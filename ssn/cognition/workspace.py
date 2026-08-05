"""
Bounded Global Cognitive Workspace.

Engineering coordination surface for independent cognitive subsystems —
not an LLM and not a consciousness claim.
"""

from __future__ import annotations

import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Sequence

from ssn.cognition.attention import (
    AttentionArbiter,
    AttentionCandidate,
    AttentionDecision,
)
from ssn.cognition.events import CognitiveEvent


@dataclass
class GoalItem:
    goal_id: str
    description: str
    priority: int = 0
    status: str = "active"
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskState:
    task_id: str
    name: str
    status: str = "idle"
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkspaceSnapshot:
    """Immutable view of workspace state for logging / loop handoff."""

    ts: float
    active_event_ids: List[str]
    attention: Optional[Dict[str, Any]]
    goals: List[Dict[str, Any]]
    task: Optional[Dict[str, Any]]
    working_context_keys: List[str]
    memory_refs: List[str]
    world_refs: List[str]
    tool_observations: List[Dict[str, Any]]
    capacity: Dict[str, int]
    selection_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts": self.ts,
            "active_event_ids": list(self.active_event_ids),
            "attention": self.attention,
            "goals": list(self.goals),
            "task": self.task,
            "working_context_keys": list(self.working_context_keys),
            "memory_refs": list(self.memory_refs),
            "world_refs": list(self.world_refs),
            "tool_observations": list(self.tool_observations),
            "capacity": dict(self.capacity),
            "selection_reason": self.selection_reason,
        }


class GlobalCognitiveWorkspace:
    """
    Bounded working-state manager.

    Responsibilities:
    - ingest cognitive events
    - reject expired events
    - maintain bounded active set / context / refs
    - arbitrate attention
    - produce snapshots
    """

    def __init__(
        self,
        *,
        max_active_events: int = 32,
        max_context_keys: int = 64,
        max_memory_refs: int = 32,
        max_world_refs: int = 32,
        max_tool_observations: int = 32,
        max_goals: int = 16,
        arbiter: Optional[AttentionArbiter] = None,
    ) -> None:
        self.max_active_events = int(max_active_events)
        self.max_context_keys = int(max_context_keys)
        self.max_memory_refs = int(max_memory_refs)
        self.max_world_refs = int(max_world_refs)
        self.max_tool_observations = int(max_tool_observations)
        self.max_goals = int(max_goals)

        self.arbiter = arbiter or AttentionArbiter()

        self._events: OrderedDict[str, CognitiveEvent] = OrderedDict()
        self._salience: Dict[str, float] = {}
        self._novelty: Dict[str, float] = {}
        self._anomaly: Dict[str, float] = {}
        self._context: OrderedDict[str, Any] = OrderedDict()
        self._memory_refs: Deque[str] = deque(maxlen=self.max_memory_refs)
        self._world_refs: Deque[str] = deque(maxlen=self.max_world_refs)
        self._tool_obs: Deque[Dict[str, Any]] = deque(maxlen=self.max_tool_observations)
        self._goals: OrderedDict[str, GoalItem] = OrderedDict()
        self._task: Optional[TaskState] = None
        self._last_decision: Optional[AttentionDecision] = None
        self._rejected_expired: int = 0
        self._ingest_count: int = 0
        self._selection_count: int = 0

    # ------------------------------------------------------------------
    # Event ingest
    # ------------------------------------------------------------------
    def ingest_event(
        self,
        event: CognitiveEvent,
        *,
        salience: float = 0.0,
        novelty: float = 0.0,
        anomaly: float = 0.0,
        now_mono: Optional[float] = None,
    ) -> bool:
        """
        Accept an event into the active set. Returns False if rejected (expired).
        """
        if event.is_expired(now_mono=now_mono):
            self._rejected_expired += 1
            return False

        self._ingest_count += 1
        self._events[event.event_id] = event
        self._events.move_to_end(event.event_id)
        self._salience[event.event_id] = max(0.0, min(1.0, float(salience)))
        self._novelty[event.event_id] = max(0.0, min(1.0, float(novelty)))
        self._anomaly[event.event_id] = max(0.0, min(1.0, float(anomaly)))

        while len(self._events) > self.max_active_events:
            old_id, _ = self._events.popitem(last=False)
            self._salience.pop(old_id, None)
            self._novelty.pop(old_id, None)
            self._anomaly.pop(old_id, None)

        return True

    def prune_expired(self, *, now_mono: Optional[float] = None) -> int:
        expired = [eid for eid, ev in self._events.items() if ev.is_expired(now_mono=now_mono)]
        for eid in expired:
            self._events.pop(eid, None)
            self._salience.pop(eid, None)
            self._novelty.pop(eid, None)
            self._anomaly.pop(eid, None)
            self._rejected_expired += 1
        return len(expired)

    # ------------------------------------------------------------------
    # Context / refs / goals / task
    # ------------------------------------------------------------------
    def set_context(self, key: str, value: Any) -> None:
        self._context[str(key)] = value
        self._context.move_to_end(str(key))
        while len(self._context) > self.max_context_keys:
            self._context.popitem(last=False)

    def update_context(self, mapping: Dict[str, Any]) -> None:
        for k, v in mapping.items():
            self.set_context(k, v)

    def add_memory_ref(self, ref: str) -> None:
        if ref and ref not in self._memory_refs:
            self._memory_refs.append(str(ref)[:256])

    def add_world_ref(self, ref: str) -> None:
        if ref and ref not in self._world_refs:
            self._world_refs.append(str(ref)[:256])

    def add_tool_observation(self, observation: Dict[str, Any]) -> None:
        if not isinstance(observation, dict):
            return
        # Bound observation size lightly
        bounded = {str(k)[:64]: observation[k] for k in list(observation.keys())[:32]}
        self._tool_obs.append(bounded)

    def upsert_goal(self, goal: GoalItem) -> None:
        self._goals[goal.goal_id] = goal
        self._goals.move_to_end(goal.goal_id)
        while len(self._goals) > self.max_goals:
            self._goals.popitem(last=False)

    def set_task(self, task: Optional[TaskState]) -> None:
        self._task = task

    # ------------------------------------------------------------------
    # Attention
    # ------------------------------------------------------------------
    def candidates(self, *, now_mono: Optional[float] = None) -> List[AttentionCandidate]:
        self.prune_expired(now_mono=now_mono)
        out: List[AttentionCandidate] = []
        for eid, ev in self._events.items():
            out.append(
                AttentionCandidate(
                    event=ev,
                    salience=self._salience.get(eid, 0.0),
                    novelty=self._novelty.get(eid, 0.0),
                    anomaly=self._anomaly.get(eid, 0.0),
                )
            )
        return out

    def select_attention(self, *, now_mono: Optional[float] = None) -> AttentionDecision:
        decision = self.arbiter.select(self.candidates(now_mono=now_mono), now_mono=now_mono)
        self._last_decision = decision
        if decision.selected is not None:
            self._selection_count += 1
        return decision

    # ------------------------------------------------------------------
    # Snapshot / metrics
    # ------------------------------------------------------------------
    def snapshot(self, *, now_mono: Optional[float] = None) -> WorkspaceSnapshot:
        decision = self._last_decision or self.select_attention(now_mono=now_mono)
        task_dict = None
        if self._task is not None:
            task_dict = {
                "task_id": self._task.task_id,
                "name": self._task.name,
                "status": self._task.status,
                "progress": self._task.progress,
                "metadata": dict(self._task.metadata),
            }
        goals = [
            {
                "goal_id": g.goal_id,
                "description": g.description,
                "priority": g.priority,
                "status": g.status,
                "confidence": g.confidence,
            }
            for g in self._goals.values()
        ]
        return WorkspaceSnapshot(
            ts=time.time(),
            active_event_ids=list(self._events.keys()),
            attention=decision.to_dict(),
            goals=goals,
            task=task_dict,
            working_context_keys=list(self._context.keys()),
            memory_refs=list(self._memory_refs),
            world_refs=list(self._world_refs),
            tool_observations=list(self._tool_obs),
            capacity={
                "max_active_events": self.max_active_events,
                "active_events": len(self._events),
                "max_context_keys": self.max_context_keys,
                "context_keys": len(self._context),
                "memory_refs": len(self._memory_refs),
                "world_refs": len(self._world_refs),
                "tool_observations": len(self._tool_obs),
                "goals": len(self._goals),
            },
            selection_reason=decision.reason,
        )

    def metrics(self) -> Dict[str, int]:
        return {
            "ingest_count": self._ingest_count,
            "selection_count": self._selection_count,
            "rejected_expired": self._rejected_expired,
            "active_events": len(self._events),
            "context_keys": len(self._context),
        }

    def clear(self) -> None:
        self._events.clear()
        self._salience.clear()
        self._novelty.clear()
        self._anomaly.clear()
        self._context.clear()
        self._memory_refs.clear()
        self._world_refs.clear()
        self._tool_obs.clear()
        self._goals.clear()
        self._task = None
        self._last_decision = None
