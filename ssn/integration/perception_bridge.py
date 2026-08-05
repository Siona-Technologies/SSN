"""Perception / sense-tick observation bridges."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ssn.integration.event_bridge import EventBridge
from ssn.integration.redaction import redact
from ssn.integration.trace_context import TraceContext


class PerceptionBridge:
    def __init__(self, events: EventBridge, *, metrics: Any = None) -> None:
        self.events = events
        self.metrics = metrics
        self._world_update_ids: set[str] = set()

    def on_sensor_observation(
        self,
        *,
        summary: Dict[str, Any],
        trace: TraceContext,
        confidence: float = 0.5,
    ) -> None:
        if self.metrics is not None:
            self.metrics.perception_observations += 1
        # Never include raw images/audio/video bytes.
        safe = redact(summary)
        for banned in ("image", "audio", "video", "bytes", "frame", "raw"):
            safe.pop(banned, None)
        self.events.emit_sync(
            "sensor.observation",
            source="integration.perception",
            payload=safe,
            trace=trace,
            confidence=confidence,
        )

    def on_perception_completed(
        self,
        *,
        processed: int,
        world_updated: bool,
        fallback: bool,
        trace: TraceContext,
    ) -> None:
        self.events.emit_sync(
            "perception.completed",
            source="integration.perception",
            payload={
                "processed": int(processed),
                "world_updated": bool(world_updated),
                "fallback": bool(fallback),
            },
            trace=trace,
        )

    def on_world_observation(
        self,
        *,
        description: str,
        update_id: str,
        trace: TraceContext,
        confidence: float = 0.5,
    ) -> None:
        self.events.emit_sync(
            "world.observation",
            source="integration.perception",
            payload={
                "description": str(description)[:200],
                "update_id": update_id,
                "confidence": float(confidence),
            },
            trace=trace,
            confidence=confidence,
        )

    def mark_world_update(self, update_id: str) -> bool:
        """Return True if first time seeing this update (prevents duplicate mutation tracking)."""
        if update_id in self._world_update_ids:
            return False
        self._world_update_ids.add(update_id)
        return True
