"""World-model observation bridges — prevent duplicate mutation tracking."""

from __future__ import annotations

from typing import Any, Dict

from ssn.integration.event_bridge import EventBridge
from ssn.integration.redaction import redact
from ssn.integration.trace_context import TraceContext


class WorldBridge:
    def __init__(self, events: EventBridge, *, metrics: Any = None) -> None:
        self.events = events
        self.metrics = metrics
        self._applied: set[str] = set()

    def on_updated(
        self,
        *,
        update_id: str,
        entity_count: int,
        event_count: int,
        trace: TraceContext,
        source: str = "world",
    ) -> bool:
        """
        Emit world.updated once per update_id.
        Returns True if this is the first observation (safe to count mutation).
        """
        if update_id in self._applied:
            return False
        self._applied.add(update_id)
        if self.metrics is not None:
            self.metrics.world_updates += 1
        self.events.emit_sync(
            "world.updated",
            source="integration.world",
            payload={
                "update_id": update_id,
                "entity_count": int(entity_count),
                "event_count": int(event_count),
                "origin": str(source)[:64],
            },
            trace=trace,
        )
        return True
