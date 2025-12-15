# ssn/core/consistency_monitor.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import time


@dataclass(frozen=True)
class DriftReport:
    drift_score: float                 # 0.0 .. 1.0
    drift_tags: List[str]              # explainable labels
    metrics: Dict[str, Any]            # raw metrics for traceability
    timestamp: float


class ConsistencyMonitor:
    """
    Phase 3.7 — Consistency & Drift Tracking (internal-only)

    Reads recent traces (and optionally reflection summaries) and computes:
      - mode oscillation
      - reasoning depth variance (if present)
      - law/safety friction frequency (if present)

    Produces a bounded DriftReport and writes it once to trace memory.
    """

    def __init__(self, memory_hub: Any, safety_monitor: Any):
        self.memory_hub = memory_hub
        self.safety_monitor = safety_monitor

    def _allow(self) -> bool:
        # Prefer explicit safety gates if present; default allow for internal-only computation.
        gate = getattr(self.safety_monitor, "allow_internal_reflection", None) or \
               getattr(self.safety_monitor, "allow_internal_analysis", None)
        if callable(gate):
            return bool(gate())
        return True

    @staticmethod
    def _clip01(x: float) -> float:
        if x < 0.0:
            return 0.0
        if x > 1.0:
            return 1.0
        return x

    @staticmethod
    def _extract_payload(trace_item: Any) -> Dict[str, Any]:
        # supports dict traces or objects with .payload
        if isinstance(trace_item, dict):
            return trace_item.get("payload", trace_item)
        payload = getattr(trace_item, "payload", None)
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _get_mode(payload: Dict[str, Any]) -> Optional[str]:
        # common keys across systems
        return (
            payload.get("brain_mode")
            or payload.get("mode")
            or payload.get("selected_mode")
            or payload.get("router_mode")
        )

    @staticmethod
    def _get_reasoning_depth(payload: Dict[str, Any]) -> Optional[float]:
        v = payload.get("reasoning_depth") or payload.get("depth")
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _is_friction(payload: Dict[str, Any]) -> bool:
        # law/safety friction signals (non-exhaustive, safe defaults)
        if payload.get("law_violation") is True:
            return True
        if payload.get("safety_flag") is True:
            return True
        tags = payload.get("tags")
        if isinstance(tags, list) and any(t in {"law_friction", "policy_block", "safety_abort"} for t in tags):
            return True
        return False

    def evaluate_recent(
        self,
        *,
        trace_limit: int = 30,
        write_trace: bool = True,
    ) -> Dict[str, Any]:
        """
        Returns a dict for easy integration; includes DriftReport fields + status.
        """
        if not self._allow():
            return {"status": "aborted", "reason": "safety_denied"}

        get_traces = getattr(self.memory_hub, "get_recent_traces", None)
        traces = get_traces(limit=trace_limit) if callable(get_traces) else []

        payloads = [self._extract_payload(t) for t in (traces or [])]

        # 1) Mode oscillation: count transitions / (n-1)
        modes: List[str] = []
        for p in payloads:
            m = self._get_mode(p)
            if isinstance(m, str) and m.strip():
                modes.append(m.strip())

        transitions = 0
        for i in range(1, len(modes)):
            if modes[i] != modes[i - 1]:
                transitions += 1

        osc_rate = (transitions / max(1, len(modes) - 1)) if len(modes) >= 2 else 0.0

        # 2) Reasoning depth variance proxy: normalized spread if depth exists
        depths: List[float] = []
        for p in payloads:
            d = self._get_reasoning_depth(p)
            if d is not None:
                depths.append(d)

        depth_spread = 0.0
        if len(depths) >= 2:
            dmin, dmax = min(depths), max(depths)
            # normalize by max to avoid scale dominance
            denom = max(1.0, abs(dmax))
            depth_spread = abs(dmax - dmin) / denom

        # 3) Friction rate
        friction_count = sum(1 for p in payloads if self._is_friction(p))
        friction_rate = (friction_count / max(1, len(payloads))) if payloads else 0.0

        # Drift score: weighted, bounded
        # (weights chosen to prioritize stability of mode + safety; can be tuned later)
        drift_score = self._clip01(
            0.45 * osc_rate +
            0.25 * depth_spread +
            0.30 * friction_rate
        )

        tags: List[str] = []
        if osc_rate >= 0.35:
            tags.append("mode_oscillation")
        if depth_spread >= 0.40:
            tags.append("reasoning_variance")
        if friction_rate >= 0.10:
            tags.append("law_or_safety_friction")

        report = DriftReport(
            drift_score=drift_score,
            drift_tags=tags,
            metrics={
                "trace_items": len(payloads),
                "modes_observed": len(modes),
                "mode_transitions": transitions,
                "mode_oscillation_rate": osc_rate,
                "depth_samples": len(depths),
                "depth_spread": depth_spread,
                "friction_count": friction_count,
                "friction_rate": friction_rate,
            },
            timestamp=time.time(),
        )

        if write_trace:
            write_fn = getattr(self.memory_hub, "write_trace", None)
            if callable(write_fn):
                write_fn(
                    source="consistency_monitor",
                    payload={
                        "type": "drift_report",
                        "drift_score": report.drift_score,
                        "drift_tags": report.drift_tags,
                        "metrics": report.metrics,
                        "timestamp": report.timestamp,
                    },
                    bounded=True,
                )

        return {
            "status": "completed",
            "drift_score": report.drift_score,
            "drift_tags": report.drift_tags,
            "metrics": report.metrics,
            "timestamp": report.timestamp,
        }
