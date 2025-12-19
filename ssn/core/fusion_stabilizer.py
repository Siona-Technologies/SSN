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
    damping_factor: float                 # 0.0 .. 1.0
    recommended_mode_bias: Optional[str]
    llm_weight_multiplier: float
    snn_weight_multiplier: float
    style_hints: Dict[str, Any]


class FusionStabilizer:
    """
    Phase 3.8 — Hybrid Fusion Stabilization (internal-only)

    Reads Phase 3.7 drift signals from trace memory and applies
    bounded, advisory stabilization to fusion outputs.
    """

    MAX_RUNTIME_SEC = 0.35

    def __init__(self, memory_hub: Any = None, safety_monitor: Any = None):
        self.memory_hub = memory_hub
        self.safety_monitor = safety_monitor

    # --------------------------------------------------
    # Safety gate
    # --------------------------------------------------
    def _allow(self) -> bool:
        if self.safety_monitor is None:
            return True
        for name in (
            "allow_internal_reflection",
            "allow_internal_analysis",
            "allow_internal_thought",
        ):
            fn = getattr(self.safety_monitor, name, None)
            if callable(fn):
                return bool(fn())
        return True

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------
    @staticmethod
    def _clip01(x: float) -> float:
        return max(0.0, min(1.0, x))

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

    def _latest_by_type(
        self, payloads: List[Dict[str, Any]], t: str
    ) -> Optional[Dict[str, Any]]:
        # support newest-first or oldest-first ordering
        for p in payloads:
            if self._ptype(p) == t:
                return p
        for p in reversed(payloads):
            if self._ptype(p) == t:
                return p
        return None

    # --------------------------------------------------
    # Compute adjustment
    # --------------------------------------------------
    def compute(self, *, trace_limit: int = 120) -> FusionStabilityAdjustment:
        start = time.time()

        if not self._allow():
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

        get_traces = (
            getattr(self.memory_hub, "get_recent_traces", None)
            if self.memory_hub
            else None
        )
        traces = get_traces(limit=trace_limit) if callable(get_traces) else []

        for t in traces or []:
            if time.time() - start > self.MAX_RUNTIME_SEC:
                break
            payloads.append(self._extract_payload(t))

        drift = self._latest_by_type(payloads, "drift_report") or {}
        prefs = self._latest_by_type(payloads, "preference_update") or {}

        # ---- drift presence check (CRITICAL) ----
        has_drift = isinstance(drift, dict) and "drift_score" in drift

        drift_score = float(drift.get("drift_score", 0.0) or 0.0)
        drift_tags = drift.get("drift_tags", [])
        if not isinstance(drift_tags, list):
            drift_tags = []

        # ---- style hints from preferences ----
        style_hints: Dict[str, Any] = {}
        stable_candidates = prefs.get("stable_candidates", [])
        if isinstance(stable_candidates, list):
            best = None
            best_conf = -1.0
            for c in stable_candidates:
                if not isinstance(c, dict):
                    continue
                conf = float(c.get("confidence", 0.0) or 0.0)
                if conf > best_conf:
                    best = c
                    best_conf = conf
            if isinstance(best, dict) and isinstance(best.get("key"), str):
                style_hints[best["key"]] = best.get("value")

        # ---- damping logic ----
        damping = self._clip01(0.85 * drift_score) if has_drift else 0.0
        if has_drift and "mode_oscillation" in drift_tags:
            damping = self._clip01(damping + 0.10)

        llm_mul = 1.0
        snn_mul = 1.0
        mode_bias = None

        if drift_score >= 0.55:
            mode_bias = "hybrid"
            llm_mul = 0.97
            snn_mul = 1.03

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

    # --------------------------------------------------
    # Apply to fusion output
    # --------------------------------------------------
    def apply_to_fusion_result(self, fusion_result: Dict[str, Any]) -> Dict[str, Any]:
        adj = self.compute()

        out = dict(fusion_result or {})
        base_score = out.get("fusion_score")

        if isinstance(base_score, (int, float)) and adj.damping_factor > 0.0:
            neutral = 0.5
            out["fusion_score"] = (
                (1.0 - adj.damping_factor) * float(base_score)
                + adj.damping_factor * neutral
            )

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

        out.setdefault("style_hints", {})
        if isinstance(out["style_hints"], dict):
            out["style_hints"].update(adj.style_hints)

        return out
