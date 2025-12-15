# ssn/memory/consolidation.py

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ConsolidationResult:
    status: str
    promoted_candidates: List[Dict[str, Any]]
    summary_payload: Dict[str, Any]


class MemoryConsolidator:
    """
    Phase 3.7.3 — Memory Consolidation (bounded, internal-only)

    Reads recent traces + episodic summaries and produces a consolidation_summary trace.
    Does NOT mutate semantic store automatically (promotion candidates are advisory only).
    """

    MAX_RUNTIME_SEC = 0.75
    MAX_TRACE_ITEMS = 80
    MAX_INSIGHTS_CAPTURED = 20
    MAX_TAGS_CAPTURED = 12

    def __init__(self, memory_hub: Any, safety_monitor: Any):
        self.memory_hub = memory_hub
        self.safety_monitor = safety_monitor

    def _allow(self) -> bool:
        for name in (
            "allow_internal_reflection",
            "allow_internal_analysis",
            "allow_internal_thought",
        ):
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
    def _payload_type(payload: Dict[str, Any]) -> Optional[str]:
        t = payload.get("type")
        return t if isinstance(t, str) else None

    @staticmethod
    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            return float(x)
        except (TypeError, ValueError):
            return default

    def run_once(
        self,
        *,
        trace_limit: int = 60,
        episodic_limit: int = 10,
        write_trace: bool = True,
    ) -> Dict[str, Any]:
        start_time = time.time()

        if not self._allow():
            return {"status": "aborted", "reason": "safety_denied"}

        get_traces = getattr(self.memory_hub, "get_recent_traces", None)
        get_episodic = getattr(self.memory_hub, "get_recent_episodic", None)

        traces = get_traces(limit=min(trace_limit, self.MAX_TRACE_ITEMS)) if callable(get_traces) else []
        episodic = get_episodic(limit=episodic_limit) if callable(get_episodic) else []

        payloads = [self._extract_payload(t) for t in (traces or [])]

        reflection_summaries: List[Dict[str, Any]] = []
        drift_reports: List[Dict[str, Any]] = []

        for p in payloads:
            if time.time() - start_time > self.MAX_RUNTIME_SEC:
                break
            t = self._payload_type(p)
            if t == "reflection_summary":
                reflection_summaries.append(p)
            elif t == "drift_report":
                drift_reports.append(p)

        # Aggregate reflection insights (bounded)
        insights: List[Any] = []
        for rs in reflection_summaries:
            if time.time() - start_time > self.MAX_RUNTIME_SEC:
                break
            rs_insights = rs.get("insights", [])
            if isinstance(rs_insights, list):
                for item in rs_insights:
                    if len(insights) >= self.MAX_INSIGHTS_CAPTURED:
                        break
                    insights.append(item)

        # Aggregate drift metrics (bounded)
        drift_scores = [
            self._safe_float(dr.get("drift_score"), 0.0) for dr in drift_reports
        ]
        avg_drift = (sum(drift_scores) / max(1, len(drift_scores))) if drift_scores else 0.0
        max_drift = max(drift_scores) if drift_scores else 0.0

        merged_tags: List[str] = []
        for dr in drift_reports:
            tags = dr.get("drift_tags", [])
            if isinstance(tags, list):
                for t in tags:
                    if isinstance(t, str) and t not in merged_tags:
                        merged_tags.append(t)
                    if len(merged_tags) >= self.MAX_TAGS_CAPTURED:
                        break
            if len(merged_tags) >= self.MAX_TAGS_CAPTURED:
                break

        # Build promotion candidates (advisory only; NO semantic mutation here)
        promoted_candidates: List[Dict[str, Any]] = []

        # Very conservative: only propose promotions if drift is low/moderate
        drift_ok = avg_drift <= 0.35 and max_drift <= 0.55

        if drift_ok and insights:
            # Heuristic: treat repeated "note"/strings as potential semantic facts
            # Keep minimal and bounded: propose at most 5 candidates
            text_hits: Dict[str, int] = {}
            for ins in insights:
                if isinstance(ins, str):
                    key = ins.strip()
                elif isinstance(ins, dict) and "note" in ins and isinstance(ins["note"], str):
                    key = ins["note"].strip()
                else:
                    continue

                if not key:
                    continue

                text_hits[key] = text_hits.get(key, 0) + 1

            for k, v in sorted(text_hits.items(), key=lambda kv: kv[1], reverse=True)[:5]:
                # Require minimal repetition to avoid noise
                if v >= 2:
                    promoted_candidates.append(
                        {
                            "kind": "semantic_candidate",
                            "fact": k,
                            "support_count": v,
                            "confidence": min(0.85, 0.45 + 0.15 * v),
                        }
                    )

        consolidation_payload: Dict[str, Any] = {
            "type": "consolidation_summary",
            "timestamp": time.time(),
            "inputs": {
                "trace_items_scanned": len(payloads),
                "reflection_summaries": len(reflection_summaries),
                "drift_reports": len(drift_reports),
                "episodic_items_scanned": len(episodic) if episodic is not None else 0,
            },
            "drift": {
                "avg_drift_score": avg_drift,
                "max_drift_score": max_drift,
                "drift_tags": merged_tags,
                "drift_ok_for_promotion": drift_ok,
            },
            "reflection": {
                "insights_captured": len(insights),
            },
            "promotion_candidates": promoted_candidates,  # advisory only
            "notes": [
                "No semantic store mutation performed.",
                "Candidates require OWNER approval in later phase before promotion.",
            ],
        }

        if write_trace:
            write_fn = getattr(self.memory_hub, "write_trace", None)
            if callable(write_fn):
                write_fn(
                    source="memory_consolidator",
                    payload=consolidation_payload,
                    bounded=True,
                )

        return {
            "status": "completed",
            "avg_drift_score": avg_drift,
            "max_drift_score": max_drift,
            "drift_tags": merged_tags,
            "promotion_candidates": promoted_candidates,
        }
