"""
World-model service boundaries and event-driven adapters.

Preserves existing WorldModel JSON persistence. Adds typed update
contracts and CognitiveEvent → world update bridging.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class WorldEntityView:
    id: str
    entity_type: str
    status: str = "unknown"
    confidence: float = 0.5
    source: str = "unknown"
    freshness: float = 1.0
    attributes: Dict[str, Any] = field(default_factory=dict)
    affordances: List[str] = field(default_factory=list)
    last_seen_ts: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity": self.entity_type,
            "status": self.status,
            "confidence": self.confidence,
            "source": self.source,
            "freshness": self.freshness,
            "attributes": dict(self.attributes),
            "affordances": list(self.affordances),
            "last_seen_ts": self.last_seen_ts,
        }


@dataclass
class WorldRelationView:
    subject_id: str
    predicate: str
    object_id: str
    confidence: float = 0.5
    source: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "predicate": self.predicate,
            "object_id": self.object_id,
            "confidence": self.confidence,
            "source": self.source,
        }


@dataclass
class WorldObservation:
    observation_id: str
    description: str
    confidence: float = 0.5
    source: str = "unknown"
    freshness: float = 1.0
    ts: float = field(default_factory=time.time)
    uncertainty: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "description": self.description,
            "confidence": self.confidence,
            "source": self.source,
            "freshness": self.freshness,
            "ts": self.ts,
            "uncertainty": self.uncertainty,
            "metadata": dict(self.metadata),
        }


@dataclass
class WorldPrediction:
    prediction_id: str
    description: str
    confidence: float = 0.3
    horizon_s: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldUpdateProposal:
    """Structured world update — applied only through WorldModel APIs."""

    proposal_id: str
    entities: List[WorldEntityView] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    observations: List[WorldObservation] = field(default_factory=list)
    relations: List[WorldRelationView] = field(default_factory=list)
    predictions: List[WorldPrediction] = field(default_factory=list)
    source: str = "cognition"
    confidence: float = 0.5
    trace_id: str = ""

    def to_world_packet(self) -> Dict[str, Any]:
        """Shape compatible with WorldModel.apply_update / update."""
        return {
            "type": "world_update",
            "ts": time.time(),
            "source": self.source,
            "entities": [e.to_dict() for e in self.entities],
            "events": list(self.events),
            "trace_id": self.trace_id,
            "proposal_id": self.proposal_id,
            "confidence": self.confidence,
        }


class WorldModelPort(Protocol):
    def apply_update(self, packet: Dict[str, Any]) -> Any:
        ...

    def snapshot(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        ...


class WorldModelServiceBoundary:
    """Facade over existing WorldModel with richer typed proposals."""

    def __init__(self, world_model: Any = None) -> None:
        self._world = world_model

    @property
    def world_model(self) -> Any:
        return self._world

    def propose_from_observation(
        self,
        description: str,
        *,
        entity_id: str = "",
        entity_type: str = "observation",
        confidence: float = 0.5,
        source: str = "cognition.world",
        trace_id: str = "",
    ) -> WorldUpdateProposal:
        eid = entity_id or f"obs:{uuid.uuid4().hex[:8]}"
        entity = WorldEntityView(
            id=eid,
            entity_type=entity_type,
            status="observed",
            confidence=confidence,
            source=source,
            last_seen_ts=time.time(),
            attributes={"description": description[:500]},
        )
        obs = WorldObservation(
            observation_id=str(uuid.uuid4()),
            description=description[:500],
            confidence=confidence,
            source=source,
        )
        return WorldUpdateProposal(
            proposal_id=str(uuid.uuid4()),
            entities=[entity],
            events=[{"type": "observation", "ts": time.time(), "confidence": confidence, "details": {"text": description[:200]}}],
            observations=[obs],
            source=source,
            confidence=confidence,
            trace_id=trace_id,
        )

    def apply_proposal(self, proposal: WorldUpdateProposal) -> Dict[str, Any]:
        if self._world is None:
            return {"ok": False, "reason": "no_world_model"}
        packet = proposal.to_world_packet()
        fn = getattr(self._world, "apply_update", None) or getattr(self._world, "update", None)
        if not callable(fn):
            return {"ok": False, "reason": "no_apply_update"}
        try:
            fn(packet)
            return {"ok": True, "proposal_id": proposal.proposal_id}
        except Exception as exc:
            return {"ok": False, "reason": str(exc)}

    def snapshot(self, **kwargs: Any) -> Dict[str, Any]:
        if self._world is None:
            return {}
        fn = getattr(self._world, "snapshot", None)
        if callable(fn):
            try:
                return dict(fn(**kwargs))
            except TypeError:
                return dict(fn())
            except Exception:
                return {}
        return {}
