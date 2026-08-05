"""
Event-bus adapters that turn CognitiveEvents into world-model proposals.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from ssn.cognition.events import CognitiveEvent
from ssn.cognition.world.contracts import WorldModelServiceBoundary, WorldUpdateProposal


class WorldEventAdapter:
    """
    Subscribe to cognitive events and optionally apply world updates.

    Default: only builds proposals. Apply only when apply=True and a
    WorldModel is wired — never bypasses existing persistence bounds.
    """

    def __init__(
        self,
        boundary: Optional[WorldModelServiceBoundary] = None,
        *,
        apply: bool = False,
        on_proposal: Optional[Callable[[WorldUpdateProposal], None]] = None,
    ) -> None:
        self.boundary = boundary or WorldModelServiceBoundary()
        self.apply = bool(apply)
        self.on_proposal = on_proposal
        self.last_proposal: Optional[WorldUpdateProposal] = None
        self.update_count = 0

    def handle(self, event: CognitiveEvent) -> Optional[WorldUpdateProposal]:
        if not event.event_type.startswith("world.") and event.event_type not in (
            "perception.delta",
            "sensor.anomaly",
            "embodiment.observation",
        ):
            # Also accept explicit world_update payload types
            if event.event_type != "world_update" and "world" not in event.event_type:
                return None

        description = ""
        payload = event.payload or {}
        if "description" in payload:
            description = str(payload["description"])
        elif "text" in payload:
            description = str(payload["text"])
        else:
            description = f"event:{event.event_type}"

        proposal = self.boundary.propose_from_observation(
            description,
            entity_id=str(payload.get("entity_id") or ""),
            entity_type=str(payload.get("entity_type") or "event"),
            confidence=float(event.confidence),
            source=event.source,
            trace_id=event.trace_id,
        )
        self.last_proposal = proposal
        if self.on_proposal:
            self.on_proposal(proposal)
        if self.apply:
            result = self.boundary.apply_proposal(proposal)
            if result.get("ok"):
                self.update_count += 1
        return proposal

    def as_handler(self) -> Callable[[CognitiveEvent], None]:
        def _handler(event: CognitiveEvent) -> None:
            self.handle(event)

        return _handler
