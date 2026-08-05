"""BrainRouter / model observation bridges (no duplicate inference)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ssn.integration.event_bridge import EventBridge
from ssn.integration.redaction import bounded_summary
from ssn.integration.trace_context import TraceContext


def classify_provider(meta: Optional[Dict[str, Any]] = None, engine: str = "") -> Dict[str, Any]:
    """Record provider class without claiming intelligence."""
    m = dict(meta or {})
    name = str(m.get("engine") or engine or m.get("provider") or "unknown")
    lower = name.lower()
    kind = "unknown"
    simulated = True
    trained = False
    if "dummy" in lower:
        kind = "dummy"
    elif "deterministic" in lower:
        kind = "deterministic"
    elif "http" in lower or "remote" in lower:
        kind = "remote"
    elif "local" in lower:
        kind = "local"
    if m.get("fallback_reason") or m.get("fallback_used"):
        simulated = True
    if m.get("simulated") is False and m.get("trained") is True:
        trained = True
        simulated = False
    return {
        "provider_name": name[:128],
        "provider_kind": kind,
        "simulated": simulated,
        "trained": trained,
        "intelligence_claim": False,
    }


class ModelBridge:
    def __init__(self, events: EventBridge, *, metrics: Any = None) -> None:
        self.events = events
        self.metrics = metrics

    def on_routing_selected(
        self,
        *,
        mode: str,
        role: str,
        note: str = "",
        trace: TraceContext,
    ) -> None:
        if self.metrics is not None:
            self.metrics.router_selections += 1
        self.events.emit_sync(
            "routing.selected",
            source="integration.router",
            payload={"mode": str(mode)[:32], "role": role, "note": str(note)[:120]},
            trace=trace,
        )

    def on_model_observed_from_result(
        self,
        *,
        result: Dict[str, Any],
        trace: TraceContext,
        shadow: bool = True,
    ) -> None:
        """
        Observe an already-completed model/router result.
        Does NOT invoke a model. Used by shadow mode.
        """
        if self.metrics is not None:
            if shadow:
                self.metrics.model_shadow_observations += 1
                self.metrics.duplicate_model_calls_prevented += 1
            else:
                self.metrics.model_requests += 1
        engine = str(result.get("engine") or "")
        reply = str(result.get("reply") or result.get("answer") or "")
        meta = result.get("meta") if isinstance(result.get("meta"), dict) else {}
        classification = classify_provider(meta, engine)
        self.events.emit_sync(
            "model.completed",
            source="integration.model",
            payload={
                "shadow_observation": bool(shadow),
                "duplicate_inference": False,
                "reply": bounded_summary(reply),
                **classification,
            },
            trace=trace,
        )

    def on_model_failed(self, *, reason: str, trace: TraceContext) -> None:
        if self.metrics is not None:
            self.metrics.provider_failures += 1
        self.events.emit_sync(
            "model.failed",
            source="integration.model",
            payload={"reason": str(reason)[:200]},
            trace=trace,
        )
