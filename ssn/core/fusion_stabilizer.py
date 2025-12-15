# ssn/core/fusion_stabilizer.py

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class FusionStabilityAdjustment:
    """
    Advisory adjustments applied to fusion outputs (not external actions).
    """
    drift_score: float
    drift_tags: List[str]
    damping_factor: float                 # 0.0 .. 1.0 (higher = more damping)
    recommended_mode_bias: Optional[str]  # e.g., "hybrid" when drift is high
    llm_weight_multiplier: float          # e.g., 0.95 .. 1.05
    snn_weight_multiplier: float          # e.g., 0.95 .. 1.05
    style_hints: Dict[str, Any]           # e.g., {"writing_style":"concise"}


class FusionStabilizer:
    """
    Phase 3.8 — Hybrid Fusion Stabilization (internal-only)

    Reads latest Phase 3.7 signals from trace_memory:
      - drift_report
      - preference_update

    Produces a bounded stability adjustment and can apply it to a fusion result dict.

    This DOES NOT:
      - execute actions
      - modify laws
      - write semantic/profile directly
      - change autonomy level
    """

    MAX_RUNTIME_SEC = 0.35

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
    def _clip01(x: float) -> float:
        return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)

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

    def _latest_by_type(self, payloads: List[Dict[str, Any]], t: str) -> Optional[Dict[str, Any]]:
        # Prefer newest-first if provided that way; otherwise fallback to reverse scan.
        for p in payloads:
            if self._ptype(p) == t:
                return p
        for p in reversed(payloads):
            if self._ptype(p) == t:
                return p
        return None

    def compute(self, *, trace_limit: int = 120) -> FusionStabilityAdjustment:
        start = time.time()

        if not self._allow():
            # Denied: return neutral adjustment (no effect)
            return FusionStabilityAdjustment(
                drift_score=0.0,
                drift_tags=[],
                damping_factor=0.0,
                recommended_mode_bias=None,
                llm_weight_multiplier=1.0,
                snn_weight_multiplier=1.0,
                style_hints={},
            )

        payloads: List[Dict[str, Any]] = []
        get_traces = getattr(self.memory_hub, "get_recent_traces", None) if self.memory_hub else None
        traces = get_traces(limit=trace_limit) if callable(get_traces) else []
        for t in traces or []:
            if time.time() - start > self.MAX_RUNTIME_SEC:
                break
            payloads.append(self._extract_payload(t))

        drift = self._latest_by_type(payloads, "drift_report") or {}
        prefs = self._latest_by_type(payloads, "preference_update") or {}

        # Detect whether we actually have a drift signal (avoid baseline damping when absent)
        has_drift = bool(drift) and ("drift_score" in drift or "drift_tags" in drift)

        drift_score = float(drift.get("drift_score", 0.0) or 0.0)
        drift_tags = drift.get("drift_tags", [])
        if not isinstance(drift_tags, list):
            drift_tags = []

        style_hints: Dict[str, Any] = {}
        stable_candidates = prefs.get("stable_candidates", [])
        if isinstance(stable_candidates, list):
            # pick top candidate by confidence
            best = None
            best_c = -1.0
            for c in stable_candidates:
                if not isinstance(c, dict):
                    continue
                conf = float(c.get("confidence", 0.0) or 0.0)
                if conf > best_c:
                    best = c
                    best_c = conf
            if isinstance(best, dict) and isinstance(best.get("key"), str):
                style_hints[best["key"]] = best.get("value")

        # Damping logic:
        # - If no drift signal exists -> damping MUST be neutral (0.0)
        # - If drift exists -> more drift => more damping (reduce volatility)
        damping = self._clip01(0.85 * drift_score) if has_drift else 0.0

        # Mode oscillation bump only applies when drift exists
        if has_drift and "mode_oscillation" in drift_tags:
            damping = self._clip01(damping + 0.10)

        # Weight multipliers:
        # - high drift => bias slightly towards SNN stability signals + hybrid bias
        # - low drift => neutral
        llm_mul = 1.0
        snn_mul = 1.0
        mode_bias = None

        if drift_score >= 0.55:
            mode_bias = "hybrid"
            llm_mul = 0.97
            snn_mul = 1.03

        # Preference hint: concise => reduce LLM dominance slightly in deep mode (advisory)
        if style_hints.get("writing_style") == "concise":
            llm_mul *= 0.985
            snn_mul *= 1.015

        return FusionStabilityAdjustment(
            drift_score=drift_score,
            drift_tags=[t for t in drift_tags if isinstance(t, str)],
            damping_factor=damping,
            recommended_mode_bias=mode_bias,
            llm_weight_multiplier=float(llm_mul),
            snn_weight_multiplier=float(snn_mul),
            style_hints=style_hints,
        )

    def apply_to_fusion_result(self, fusion_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Applies advisory stabilization to the *output packet* without requiring internal fusion refactors.

        - Adds `stability` block
        - Optionally damps `fusion_score` towards 0.5 when drift exists and is elevated
        - Adds style hints (advisory) for downstream language formatting

        This is safe even if your fusion engine doesn't expose internal weights yet.
        """
        adj = self.compute()

        out = dict(fusion_result or {})
        base_score = out.get("fusion_score", None)

        # Dampen fusion_score if present and numeric
        if isinstance(base_score, (int, float)) and adj.damping_factor > 0.0:
            # pull score toward neutral 0.5 when damping high
            neutral = 0.5
            damped = (1.0 - adj.damping_factor) * float(base_score) + adj.damping_factor * neutral
            out["fusion_score"] = float(damped)

        out["stability"] = {
            "timestamp": time.time(),
            "drift_score": adj.drift_score,
            "drift_tags": adj.drift_tags,
            "damping_factor": adj.damping_factor,
            "recommended_mode_bias": adj.recommended_mode_bias,
            "llm_weight_multiplier": adj.llm_weight_multiplier,
            "snn_weight_multiplier": adj.snn_weight_multiplier,
            "style_hints": adj.style_hints,
            "notes": [
                "Advisory stabilization applied.",
                "No external actions performed.",
                "No law or policy mutation.",
            ],
        }

        # If engine supports passing style hints, attach non-invasive hint
        out.setdefault("style_hints", {})
        if isinstance(out["style_hints"], dict):
            out["style_hints"].update(adj.style_hints)

        return out
