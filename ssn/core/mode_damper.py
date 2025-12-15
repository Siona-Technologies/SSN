# ssn/core/mode_damper.py

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ModeDampingDecision:
    selected_mode: str
    original_mode: str
    drift_score: float
    drift_tags: List[str]
    damped: bool
    reason: str
    timestamp: float


class ModeDamper:
    """
    Phase 3.9 — Mode Damping (internal-only)

    Uses latest drift_report to reduce mode oscillations:
      - If drift is high or mode_oscillation is present, prefer 'hybrid' as a stable default.
      - If drift is low, respect original mode.

    Does not change autonomy; advisory pre-fusion stabilization.
    """

    def __init__(self, memory_hub: Any = None, safety_monitor: Any = None):
        self.memory_hub = memory_hub
        self.safety_monitor = safety_monitor

    def _allow(self) -> bool:
        if self.safety_monitor is None:
            return True
        for name in ("allow_internal_reflection", "allow_internal_analysis", "allow_internal_thought"):
            fn = getattr(self.safety_monitor, name, None)
            if callable(fn):
                return bool(fn())
        return True

    @staticmethod
    def _extract_payload(trace_item: Any) -> Dict[str, Any]:
        if isinstance(trace_item, dict):
            return trace_item.get("payload", trace_item)
        payload = getattr(trace_item, "payload", None)
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _ptype(p: Dict[str, Any]) -> Optional[str]:
        t = p.get("type")
        return t if isinstance(t, str) else None

    def _latest_drift(self, trace_limit: int = 120) -> Dict[str, Any]:
        get_traces = getattr(self.memory_hub, "get_recent_traces", None) if self.memory_hub else None
        traces = get_traces(limit=trace_limit) if callable(get_traces) else []
        payloads = [self._extract_payload(t) for t in (traces or [])]

        # Prefer newest-first, but support either ordering
        for p in payloads:
            if self._ptype(p) == "drift_report":
                return p
        for p in reversed(payloads):
            if self._ptype(p) == "drift_report":
                return p
        return {}

    def damp_mode(self, original_mode: str, *, trace_limit: int = 120) -> ModeDampingDecision:
        if not self._allow():
            return ModeDampingDecision(
                selected_mode=original_mode,
                original_mode=original_mode,
                drift_score=0.0,
                drift_tags=[],
                damped=False,
                reason="safety_denied_neutral",
                timestamp=time.time(),
            )

        drift = self._latest_drift(trace_limit=trace_limit) or {}
        drift_score = float(drift.get("drift_score", 0.0) or 0.0)
        drift_tags = drift.get("drift_tags", [])
        if not isinstance(drift_tags, list):
            drift_tags = []

        # Damping rules (conservative)
        if drift_score >= 0.60 or ("mode_oscillation" in drift_tags and drift_score >= 0.40):
            # Stabilize to hybrid unless original already hybrid
            selected = "hybrid" if original_mode != "hybrid" else "hybrid"
            return ModeDampingDecision(
                selected_mode=selected,
                original_mode=original_mode,
                drift_score=drift_score,
                drift_tags=[t for t in drift_tags if isinstance(t, str)],
                damped=(selected != original_mode),
                reason="high_drift_or_oscillation",
                timestamp=time.time(),
            )

        # Low drift: no damping
        return ModeDampingDecision(
            selected_mode=original_mode,
            original_mode=original_mode,
            drift_score=drift_score,
            drift_tags=[t for t in drift_tags if isinstance(t, str)],
            damped=False,
            reason="drift_low_respect_original",
            timestamp=time.time(),
        )
