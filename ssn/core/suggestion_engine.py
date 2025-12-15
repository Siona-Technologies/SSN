# ssn/core/suggestion_engine.py

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Suggestion:
    title: str
    description: str
    confidence: float
    requires_owner_ack: bool = True
    scope: str = "internal_reasoning"  # never "external_action"


class SuggestionEngine:
    """
    Phase 3.7.5 — Reflection → Suggestion Bridge (internal-only, advisory)

    Reads recent trace signals and produces a suggestion_packet.
    No autonomy escalation. No external actions. No self-modifying behavior.
    """

    MAX_RUNTIME_SEC = 0.6
    MAX_SUGGESTIONS = 5

    def __init__(self, memory_hub: Any, safety_monitor: Any):
        self.memory_hub = memory_hub
        self.safety_monitor = safety_monitor

    def _allow(self) -> bool:
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

    @staticmethod
    def _clip01(x: float) -> float:
        return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)

    def _latest_by_type(self, payloads: List[Dict[str, Any]], t: str) -> Optional[Dict[str, Any]]:
        # assumes traces are returned newest-first in MemoryHub, but safe either way:
        for p in payloads:
            if self._ptype(p) == t:
                return p
        # fallback: scan from end if list was oldest-first
        for p in reversed(payloads):
            if self._ptype(p) == t:
                return p
        return None

    def run_once(self, *, trace_limit: int = 120, write_trace: bool = True) -> Dict[str, Any]:
        start = time.time()

        if not self._allow():
            return {"status": "aborted", "reason": "safety_denied"}

        get_traces = getattr(self.memory_hub, "get_recent_traces", None)
        traces = get_traces(limit=trace_limit) if callable(get_traces) else []
        payloads = [self._extract_payload(t) for t in (traces or [])]

        drift = self._latest_by_type(payloads, "drift_report") or {}
        cons = self._latest_by_type(payloads, "consolidation_summary") or {}
        prefs = self._latest_by_type(payloads, "preference_update") or {}

        drift_score = float(drift.get("drift_score", 0.0) or 0.0)
        drift_tags = drift.get("drift_tags", []) if isinstance(drift.get("drift_tags", []), list) else []
        cons_drift_ok = (cons.get("drift", {}) or {}).get("drift_ok_for_promotion", False)
        pref_cands = prefs.get("stable_candidates", []) if isinstance(prefs.get("stable_candidates", []), list) else []

        suggestions: List[Suggestion] = []

        # Suggestion 1: drift handling
        if drift_score >= 0.55:
            suggestions.append(
                Suggestion(
                    title="Reduce cognitive drift",
                    description=(
                        "Drift score is elevated. Recommend temporarily locking brain mode selection "
                        "to the most stable mode for similar requests, and increasing reflection frequency "
                        "slightly (still bounded) to stabilize."
                    ),
                    confidence=self._clip01(0.50 + 0.50 * min(1.0, drift_score)),
                )
            )

        if "mode_oscillation" in drift_tags:
            suggestions.append(
                Suggestion(
                    title="Stabilize brain mode transitions",
                    description=(
                        "Mode oscillation detected. Recommend adding a damping rule: "
                        "avoid switching modes too frequently unless SafetyMonitor flags urgency."
                    ),
                    confidence=0.65,
                )
            )

        # Suggestion 2: preference application (advisory only)
        if pref_cands:
            # Pick top 1–2 by confidence
            sorted_cands = sorted(
                [c for c in pref_cands if isinstance(c, dict)],
                key=lambda c: float(c.get("confidence", 0.0) or 0.0),
                reverse=True,
            )[:2]

            if sorted_cands:
                suggestions.append(
                    Suggestion(
                        title="Apply stable preferences (OWNER approval required)",
                        description=(
                            "Stable preference candidates detected. Recommend OWNER review and approval "
                            "to apply to PersonalProfile or response style gates: "
                            f"{sorted_cands}"
                        ),
                        confidence=min(0.85, float(sorted_cands[0].get("confidence", 0.6) or 0.6)),
                        scope="internal_reasoning",
                    )
                )

        # Suggestion 3: consolidation gating
        if not cons_drift_ok and (cons.get("promotion_candidates") or []):
            suggestions.append(
                Suggestion(
                    title="Hold semantic promotions due to drift",
                    description=(
                        "Consolidation produced promotion candidates but drift gating is not OK. "
                        "Recommend holding promotions until drift stabilizes, then re-evaluating."
                    ),
                    confidence=0.70,
                )
            )

        # Bound suggestions
        suggestions = suggestions[: self.MAX_SUGGESTIONS]

        packet = {
            "type": "suggestion_packet",
            "timestamp": time.time(),
            "requires_owner_ack": True,
            "inputs": {
                "drift_score": drift_score,
                "drift_tags": drift_tags,
                "consolidation_seen": bool(cons),
                "preference_candidates_seen": len(pref_cands),
            },
            "suggestions": [
                {
                    "title": s.title,
                    "description": s.description,
                    "confidence": s.confidence,
                    "requires_owner_ack": s.requires_owner_ack,
                    "scope": s.scope,
                }
                for s in suggestions
            ],
            "notes": [
                "Advisory output only. No actions taken.",
                "OWNER confirmation required before applying any suggestion.",
            ],
        }

        if write_trace:
            write_fn = getattr(self.memory_hub, "write_trace", None)
            if callable(write_fn):
                write_fn(source="suggestion_engine", payload=packet, bounded=True)

        # Return minimal result for callers
        return {
            "status": "completed",
            "suggestion_count": len(suggestions),
            "requires_owner_ack": True,
        }
