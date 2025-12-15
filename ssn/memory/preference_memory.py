# ssn/memory/preference_memory.py

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class PreferenceCandidate:
    key: str
    value: Any
    support_count: int
    confidence: float


class PreferenceStabilizer:
    """
    Phase 3.7.4 — Long-term Preference Stabilization (advisory only)

    Reads recent traces (reflection_summary + consolidation_summary) and extracts preference hints.
    Produces:
      - stable preference candidates (in return payload)
      - a bounded trace write: type=preference_update (advisory, no enforcement)

    Does NOT mutate PersonalProfile automatically in Phase 3.7.
    """

    MAX_RUNTIME_SEC = 0.75
    MAX_TRACE_ITEMS = 100
    MAX_CANDIDATES = 10

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
    def _payload_type(payload: Dict[str, Any]) -> Optional[str]:
        t = payload.get("type")
        return t if isinstance(t, str) else None

    @staticmethod
    def _normalize_key(k: str) -> str:
        return k.strip().lower().replace(" ", "_")

    @staticmethod
    def _clip01(x: float) -> float:
        return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)

    def _extract_preference_pairs(self, payload: Dict[str, Any]) -> List[Tuple[str, Any]]:
        """
        Conservative extraction rules:
        - If insight dict contains {"preference": {"key":..., "value":...}} capture it.
        - If insight dict contains {"pref_key":..., "pref_value":...} capture it.
        - If string contains "prefer X" or "preference: key=value" capture simple patterns.
        """
        pairs: List[Tuple[str, Any]] = []

        # From reflection_summary insights
        if payload.get("type") == "reflection_summary":
            insights = payload.get("insights", [])
            if isinstance(insights, list):
                for ins in insights:
                    if isinstance(ins, dict):
                        pref = ins.get("preference")
                        if isinstance(pref, dict) and isinstance(pref.get("key"), str):
                            pairs.append((pref["key"], pref.get("value")))
                            continue
                        if isinstance(ins.get("pref_key"), str):
                            pairs.append((ins["pref_key"], ins.get("pref_value")))
                            continue
                        # common "note" shortcut (advisory): treat repeated notes as tone/style preferences
                        note = ins.get("note")
                        if isinstance(note, str) and "prefer" in note.lower():
                            pairs.extend(self._parse_text(note))
                    elif isinstance(ins, str):
                        pairs.extend(self._parse_text(ins))

        # From consolidation_summary promotion candidates
        if payload.get("type") == "consolidation_summary":
            cands = payload.get("promotion_candidates", [])
            if isinstance(cands, list):
                for c in cands:
                    if not isinstance(c, dict):
                        continue
                    fact = c.get("fact")
                    if isinstance(fact, str):
                        pairs.extend(self._parse_text(fact))

        return pairs

    def _parse_text(self, text: str) -> List[Tuple[str, Any]]:
        t = text.strip()
        low = t.lower()
        pairs: List[Tuple[str, Any]] = []

        # Very simple patterns (conservative by design)
        # "preference: key=value"
        if "preference:" in low and "=" in t:
            try:
                after = t.split("preference:", 1)[1].strip()
                key, val = after.split("=", 1)
                pairs.append((key.strip(), val.strip()))
                return pairs
            except Exception:
                return pairs

        # "prefer concise outputs" -> map to writing_style=concise
        if "prefer" in low:
            # rudimentary mapping for common SSN preferences
            if "concise" in low:
                pairs.append(("writing_style", "concise"))
            if "detailed" in low:
                pairs.append(("writing_style", "detailed"))
            if "formal" in low:
                pairs.append(("tone", "formal"))
            if "friendly" in low:
                pairs.append(("tone", "friendly"))
            if "dark" in low and "theme" in low:
                pairs.append(("theme", "dark"))
            if "light" in low and "theme" in low:
                pairs.append(("theme", "light"))

        return pairs

    def run_once(
        self,
        *,
        trace_limit: int = 80,
        write_trace: bool = True,
    ) -> Dict[str, Any]:
        start = time.time()

        if not self._allow():
            return {"status": "aborted", "reason": "safety_denied"}

        get_traces = getattr(self.memory_hub, "get_recent_traces", None)
        traces = get_traces(limit=min(trace_limit, self.MAX_TRACE_ITEMS)) if callable(get_traces) else []
        payloads = [self._extract_payload(t) for t in (traces or [])]

        # Collect preference votes
        votes: Dict[Tuple[str, Any], int] = {}
        for p in payloads:
            if time.time() - start > self.MAX_RUNTIME_SEC:
                break
            ptype = self._payload_type(p)
            if ptype not in {"reflection_summary", "consolidation_summary"}:
                continue

            for k, v in self._extract_preference_pairs(p):
                if not isinstance(k, str) or not k.strip():
                    continue
                nk = self._normalize_key(k)
                key = (nk, v)
                votes[key] = votes.get(key, 0) + 1

        # Build candidates: repeated signals only
        candidates: List[PreferenceCandidate] = []
        for (k, v), count in sorted(votes.items(), key=lambda kv: kv[1], reverse=True):
            if time.time() - start > self.MAX_RUNTIME_SEC:
                break
            if count < 2:  # conservative threshold
                continue
            confidence = self._clip01(0.40 + 0.15 * count)  # grows with repetition
            candidates.append(PreferenceCandidate(k, v, count, confidence))
            if len(candidates) >= self.MAX_CANDIDATES:
                break

        payload = {
            "type": "preference_update",
            "timestamp": time.time(),
            "stable_candidates": [
                {
                    "key": c.key,
                    "value": c.value,
                    "support_count": c.support_count,
                    "confidence": c.confidence,
                }
                for c in candidates
            ],
            "notes": [
                "Advisory only. No profile mutation performed in Phase 3.7.",
                "Candidates can be applied later with explicit OWNER approval.",
            ],
        }

        if write_trace:
            write_fn = getattr(self.memory_hub, "write_trace", None)
            if callable(write_fn):
                write_fn(source="preference_stabilizer", payload=payload, bounded=True)

        return {
            "status": "completed",
            "stable_candidates": payload["stable_candidates"],
            "vote_count": len(votes),
        }
