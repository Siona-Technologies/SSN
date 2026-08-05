"""Chat / request path observation bridges."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ssn.cognition.events import EventPriority
from ssn.integration.event_bridge import EventBridge
from ssn.integration.redaction import bounded_summary, redact
from ssn.integration.trace_context import TraceContext


class ChatBridge:
    def __init__(self, events: EventBridge) -> None:
        self.events = events

    def on_input_text(self, text: str, *, trace: TraceContext) -> None:
        self.events.emit_sync(
            "input.text",
            source="integration.chat",
            payload={"text": bounded_summary(text), "role": trace.role},
            trace=trace,
            priority=EventPriority.HIGH if trace.role == "OWNER" else EventPriority.NORMAL,
            requires_attention=True,
        )

    def on_identity_resolved(self, *, role: str, verified: bool, trace: TraceContext) -> None:
        # Category only — never include verification secrets.
        self.events.emit_sync(
            "identity.resolved",
            source="integration.chat",
            payload={"role": role, "verified": bool(verified), "category": role},
            trace=trace,
        )

    def on_policy_evaluated(self, *, outcome: str, action: str = "", trace: TraceContext = None) -> None:
        self.events.emit_sync(
            "policy.evaluated",
            source="integration.chat",
            payload={"outcome": str(outcome)[:64], "action": str(action)[:64]},
            trace=trace,
        )

    def on_response_completed(
        self,
        *,
        answer_preview: str,
        engine: str = "",
        degraded: bool = False,
        used_tools: int = 0,
        trace: TraceContext,
        latency_ms: float = 0.0,
    ) -> None:
        self.events.emit_sync(
            "response.completed",
            source="integration.chat",
            payload={
                "answer": bounded_summary(answer_preview),
                "engine": str(engine)[:64],
                "degraded": bool(degraded),
                "used_tools": int(used_tools),
                "latency_ms": float(latency_ms),
                "runtime_mode": trace.runtime_mode,
            },
            trace=trace,
        )

    def on_runtime_error(self, *, error_class: str, message: str, trace: TraceContext) -> None:
        self.events.emit_sync(
            "runtime.error",
            source="integration.chat",
            payload={"error_class": str(error_class)[:64], "message": str(message)[:200]},
            trace=trace,
            priority=EventPriority.HIGH,
        )
