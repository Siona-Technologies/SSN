"""
Integration facade — canonical Phase 2 wiring over shared runtime instances.

Observes the authoritative Orchestrator path in legacy/shadow modes.
Optionally runs CognitiveLoop in cognitive_experimental (proposals only).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ssn.cognition.loop import CognitiveLoop, CognitiveRuntime
from ssn.cognition.neuromorphic.providers import (
    DeterministicNeuromorphicProvider,
    data_to_neuromorphic_event,
)
from ssn.integration.chat_bridge import ChatBridge
from ssn.integration.event_bridge import EventBridge
from ssn.integration.memory_bridge import MemoryBridge
from ssn.integration.model_bridge import ModelBridge
from ssn.integration.observability import IntegrationMetrics
from ssn.integration.perception_bridge import PerceptionBridge
from ssn.integration.redaction import bounded_summary, redact
from ssn.integration.runtime_modes import RuntimeMode, get_runtime_mode, resolve_runtime_mode
from ssn.integration.tool_bridge import ToolBridge
from ssn.integration.trace_context import TraceContext
from ssn.integration.world_bridge import WorldBridge


@dataclass
class IntegrationFacade:
    """
    Shared integration surface attached once by SSNRuntimeBuilder.
    """

    cognitive_runtime: CognitiveRuntime
    orchestrator: Any = None
    mode: RuntimeMode = field(default_factory=get_runtime_mode)
    metrics: IntegrationMetrics = field(default_factory=IntegrationMetrics)
    events: EventBridge = field(init=False)
    chat: ChatBridge = field(init=False)
    model: ModelBridge = field(init=False)
    tools: ToolBridge = field(init=False)
    perception: PerceptionBridge = field(init=False)
    memory: MemoryBridge = field(init=False)
    world: WorldBridge = field(init=False)
    neuromorphic: Any = field(default=None)

    def __post_init__(self) -> None:
        self.events = EventBridge(self.cognitive_runtime.bus, metrics=self.metrics)
        self.chat = ChatBridge(self.events)
        self.model = ModelBridge(self.events, metrics=self.metrics)
        self.tools = ToolBridge(self.events, metrics=self.metrics)
        self.perception = PerceptionBridge(self.events, metrics=self.metrics)
        self.memory = MemoryBridge(self.events, metrics=self.metrics)
        self.world = WorldBridge(self.events, metrics=self.metrics)
        self.neuromorphic = self.neuromorphic or getattr(
            self.cognitive_runtime, "neuromorphic", None
        ) or DeterministicNeuromorphicProvider()

    @classmethod
    def create(
        cls,
        *,
        cognitive_runtime: CognitiveRuntime,
        orchestrator: Any = None,
        mode: Optional[str] = None,
    ) -> "IntegrationFacade":
        return cls(
            cognitive_runtime=cognitive_runtime,
            orchestrator=orchestrator,
            mode=resolve_runtime_mode(mode),
        )

    def refresh_mode(self) -> RuntimeMode:
        self.mode = get_runtime_mode()
        return self.mode

    def diagnostic_snapshot(self) -> Dict[str, Any]:
        """Local diagnostic API — not a public admin endpoint."""
        bus = self.cognitive_runtime.bus
        self.metrics.queue_depth = bus.queue_depth
        self.metrics.workspace_count = len(self.cognitive_runtime.workspaces)
        self.metrics.workspace_evictions = int(
            getattr(self.cognitive_runtime.workspaces, "evictions", 0) or 0
        )
        snap = self.metrics.snapshot()
        snap["runtime_mode"] = self.mode.value
        snap["cognitive_runtime_id"] = id(self.cognitive_runtime)
        snap["orchestrator_id"] = id(self.orchestrator) if self.orchestrator is not None else None
        snap["memory_hub_id"] = id(getattr(self.cognitive_runtime.memory, "hub", None))
        snap["world_model_id"] = id(getattr(self.cognitive_runtime.world, "world_model", None))
        snap["model_gateway_id"] = id(self.cognitive_runtime.model_gateway)
        snap["bus_metrics"] = bus.metrics.snapshot()
        # Scrub any accidental secrets
        return redact(snap)

    def observe_authoritative_chat(
        self,
        *,
        user_input: str,
        role: str,
        context: Optional[Dict[str, Any]],
        result: Dict[str, Any],
        trace: TraceContext,
        started_at: float,
        identity_verified: bool = False,
        router_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Shadow/legacy observation after the authoritative path completes.
        Never changes the response. Never calls a model again.
        """
        self.metrics.inc_mode(trace.runtime_mode)
        latency_ms = max(0.0, (time.time() - started_at) * 1000.0)
        self.metrics.request_latency_ms_last = latency_ms

        if self.mode == RuntimeMode.LEGACY:
            # Minimal observation optional — still emit input/response for continuity tests
            # when explicitly requested via shadow... for legacy we keep events light.
            return {
                "runtime_mode": RuntimeMode.LEGACY.value,
                "authoritative": True,
                "cognitive_side_effects": False,
            }

        # Shadow (and experimental observation of the authoritative result)
        self.chat.on_input_text(user_input, trace=trace)
        self.chat.on_identity_resolved(role=role, verified=identity_verified, trace=trace)
        self.chat.on_policy_evaluated(outcome="passed_to_runtime", action="chat", trace=trace)

        rr = router_result or {}
        mode = str(rr.get("mode") or rr.get("brain_mode") or "unknown")
        self.model.on_routing_selected(mode=mode, role=role, note=str(rr.get("note") or ""), trace=trace)

        # Observe model result without duplicate inference
        obs_src = dict(rr) if rr else {"reply": result.get("answer"), "engine": ""}
        if "reply" not in obs_src and "answer" in result:
            obs_src["reply"] = result.get("answer")
        self.model.on_model_observed_from_result(result=obs_src, trace=trace, shadow=True)

        # Neuromorphic shadow on bounded features only
        self._neuromorphic_shadow(user_input=user_input, trace=trace)

        workspace = self.cognitive_runtime.workspaces.get(trace.tenant_id, trace.session_id)
        # Ingest attention candidate from input event metadata only
        from ssn.cognition.events import CognitiveEvent, EventPriority

        ev = CognitiveEvent.text_input(
            user_input[:200],
            role=role,
            session_id=trace.session_id,
            tenant_id=trace.tenant_id,
            priority=EventPriority.NORMAL,
            trace_id=trace.trace_id,
        )
        workspace.ingest_event(ev, salience=0.4, novelty=0.3, anomaly=0.0)
        workspace.update_context(
            {
                "role": role,
                "tenant_id": workspace.tenant_id,
                "session_id": workspace.session_id,
                "last_user_text": (user_input or "")[:500],
            }
        )
        decision = workspace.select_attention()
        if decision.selected is not None:
            self.metrics.attention_selections += 1

        used_tools = result.get("used_tools") or []
        self.chat.on_response_completed(
            answer_preview=str(result.get("answer") or ""),
            engine=str(obs_src.get("engine") or ""),
            degraded=bool(result.get("degraded")),
            used_tools=len(used_tools) if isinstance(used_tools, list) else 0,
            trace=trace,
            latency_ms=latency_ms,
        )

        return {
            "runtime_mode": self.mode.value,
            "authoritative": True,
            "cognitive_side_effects": False,
            "duplicate_model_call": False,
            "attention": decision.to_dict() if decision else None,
            "trace_id": trace.trace_id,
        }

    def _neuromorphic_shadow(self, *, user_input: str, trace: TraceContext) -> None:
        if self.neuromorphic is None:
            return
        features = {
            "text_length": len(user_input or ""),
            "modality": "text_meta",
            "hash8": bounded_summary(user_input).get("hash8"),
            "temporal": time.time(),
        }
        # Explicitly exclude secrets — only metadata features.
        event = data_to_neuromorphic_event(features, metadata={"trace_id": trace.trace_id})
        out = self.neuromorphic.process_event(event)
        self.metrics.neuromorphic_events += 1
        self.metrics.simulated_spike_count += int(out.spikes_detected)
        if out.reflex_proposal:
            # Non-executing: record as event only
            self.events.emit_sync(
                "tool.proposed",
                source="integration.neuromorphic",
                payload={
                    "tool": "reflex",
                    "args": redact(dict(out.reflex_proposal)),
                    "executes": False,
                    "simulated": True,
                },
                trace=trace,
            )

    def run_experimental_loop(
        self,
        *,
        text: str,
        role: str,
        session_id: str,
        tenant_id: str,
        context: Optional[Dict[str, Any]],
        trace: TraceContext,
    ) -> Dict[str, Any]:
        """
        Opt-in cognitive loop. Proposals only — no tool/embodiment execution here.
        Labelled experimental. Uses deterministic providers by default.
        """
        self.metrics.inc_mode(RuntimeMode.COGNITIVE_EXPERIMENTAL.value)
        loop = CognitiveLoop(self.cognitive_runtime)
        out = loop.process_text(
            text,
            role=role,
            context=context,
            session_id=session_id,
            tenant_id=tenant_id,
        )
        out["runtime_mode"] = RuntimeMode.COGNITIVE_EXPERIMENTAL.value
        out["experimental"] = True
        out["authoritative_front_door"] = False
        out["trace_id"] = trace.trace_id
        out["label"] = "cognitive_experimental"
        # Ensure proposals do not auto-execute
        for p in out.get("proposals") or []:
            if isinstance(p, dict):
                p.setdefault("requires_confirmation", True)
                p.setdefault("executed", False)
        return out

    def observe_sense_tick(
        self,
        *,
        tick_result: Dict[str, Any],
        trace: TraceContext,
        fallback: bool,
        update_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        uid = update_id or str(uuid.uuid4())
        self.perception.on_sensor_observation(
            summary={
                "processed": tick_result.get("processed"),
                "source": "sense_tick",
                "fallback": fallback,
            },
            trace=trace,
            confidence=float(tick_result.get("confidence") or 0.5),
        )
        self.perception.on_perception_completed(
            processed=int(tick_result.get("processed") or 0),
            world_updated=bool(tick_result.get("world_updated")),
            fallback=fallback,
            trace=trace,
        )
        first = self.world.on_updated(
            update_id=uid,
            entity_count=len((tick_result.get("world_update") or {}).get("entities") or []),
            event_count=len((tick_result.get("world_update") or {}).get("events") or []),
            trace=trace,
            source="sense_tick",
        )
        return {"update_id": uid, "first_world_update_event": first, "trace_id": trace.trace_id}

    def observe_tool_execution(
        self,
        *,
        tool_name: str,
        args: Dict[str, Any],
        execution_id: str,
        ok: bool,
        result_summary: Dict[str, Any],
        trace: TraceContext,
    ) -> None:
        self.tools.on_proposed(tool_name=tool_name, args=args, trace=trace)
        self.tools.on_started(tool_name=tool_name, execution_id=execution_id, trace=trace)
        self.tools.on_completed(
            tool_name=tool_name,
            execution_id=execution_id,
            ok=ok,
            result_summary=result_summary,
            trace=trace,
            count_execution=True,
        )

    @property
    def pending_observation_tasks(self) -> int:
        return self.events.pending_task_count

    async def drain(self, *, timeout_s: float = 5.0) -> None:
        """Await pending observation tasks from EventBridge."""
        await self.events.drain(timeout_s=timeout_s)

    async def shutdown(self, *, timeout_s: float = 5.0) -> None:
        """Drain observation tasks and close the event bridge."""
        await self.events.shutdown(timeout_s=timeout_s)

    def shutdown_sync(self, *, timeout_s: float = 5.0) -> None:
        """
        Sync teardown for callers without a running event loop.
        Inside a running loop, raises — use ``await facade.shutdown()``.
        """
        self.events.shutdown_sync(timeout_s=timeout_s)
