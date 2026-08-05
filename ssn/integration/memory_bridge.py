"""Memory observation bridges — never auto-commit."""

from __future__ import annotations

from typing import Any, Dict

from ssn.integration.event_bridge import EventBridge
from ssn.integration.redaction import redact
from ssn.integration.trace_context import TraceContext


class MemoryBridge:
    def __init__(self, events: EventBridge, *, metrics: Any = None) -> None:
        self.events = events
        self.metrics = metrics

    def on_proposed(
        self,
        *,
        proposal_id: str,
        kind: str,
        ref: str,
        trace: TraceContext,
    ) -> None:
        if self.metrics is not None:
            self.metrics.memory_proposals += 1
        self.events.emit_sync(
            "memory.proposed",
            source="integration.memory",
            payload={
                "proposal_id": proposal_id,
                "kind": str(kind)[:64],
                "ref": str(ref)[:128],
                "auto_commit": False,
            },
            trace=trace,
        )

    def on_committed(self, *, proposal_id: str, ref: str, trace: TraceContext) -> None:
        self.events.emit_sync(
            "memory.committed",
            source="integration.memory",
            payload={"proposal_id": proposal_id, "ref": str(ref)[:128]},
            trace=trace,
        )

    def on_rejected(self, *, proposal_id: str, reason: str, trace: TraceContext) -> None:
        self.events.emit_sync(
            "memory.rejected",
            source="integration.memory",
            payload={"proposal_id": proposal_id, "reason": str(reason)[:120]},
            trace=trace,
        )
