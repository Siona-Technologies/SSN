"""
Attention arbitration for the Global Cognitive Workspace.

Deterministic ranking of attention candidates based on priority,
salience, confidence, freshness, and explicit attention flags.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from ssn.cognition.events import CognitiveEvent, EventPriority


@dataclass(frozen=True)
class AttentionCandidate:
    event: CognitiveEvent
    salience: float = 0.0
    novelty: float = 0.0
    anomaly: float = 0.0
    reason_hints: Dict[str, Any] = field(default_factory=dict)

    @property
    def event_id(self) -> str:
        return self.event.event_id


@dataclass(frozen=True)
class AttentionDecision:
    selected: Optional[AttentionCandidate]
    score: float
    reason: str
    rejected: List[Dict[str, Any]] = field(default_factory=list)
    ranked: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_event_id": self.selected.event_id if self.selected else None,
            "score": self.score,
            "reason": self.reason,
            "rejected": list(self.rejected),
            "ranked": list(self.ranked),
        }


class AttentionArbiter:
    """
    Deterministic attention selector.

    Score = w_priority * priority_norm
          + w_salience * salience
          + w_confidence * confidence
          + w_freshness * freshness
          + w_flag * requires_attention
          + w_anomaly * anomaly
    """

    def __init__(
        self,
        *,
        w_priority: float = 0.35,
        w_salience: float = 0.25,
        w_confidence: float = 0.15,
        w_freshness: float = 0.10,
        w_flag: float = 0.10,
        w_anomaly: float = 0.05,
        max_age_ms: float = 60_000.0,
    ) -> None:
        self.w_priority = float(w_priority)
        self.w_salience = float(w_salience)
        self.w_confidence = float(w_confidence)
        self.w_freshness = float(w_freshness)
        self.w_flag = float(w_flag)
        self.w_anomaly = float(w_anomaly)
        self.max_age_ms = float(max_age_ms)

    def score_candidate(self, candidate: AttentionCandidate, *, now_mono: Optional[float] = None) -> float:
        ev = candidate.event
        if ev.is_expired(now_mono=now_mono):
            return -1.0

        priority_norm = float(int(ev.priority)) / float(int(EventPriority.CRITICAL))
        age_ms = ev.age_ms(now_mono=now_mono)
        freshness = max(0.0, 1.0 - (age_ms / self.max_age_ms))
        flag = 1.0 if ev.requires_attention else 0.0
        salience = max(0.0, min(1.0, float(candidate.salience)))
        anomaly = max(0.0, min(1.0, float(candidate.anomaly)))
        confidence = max(0.0, min(1.0, float(ev.confidence)))

        return (
            self.w_priority * priority_norm
            + self.w_salience * salience
            + self.w_confidence * confidence
            + self.w_freshness * freshness
            + self.w_flag * flag
            + self.w_anomaly * anomaly
        )

    def select(
        self,
        candidates: Sequence[AttentionCandidate],
        *,
        now_mono: Optional[float] = None,
    ) -> AttentionDecision:
        rejected: List[Dict[str, Any]] = []
        scored: List[tuple[float, AttentionCandidate]] = []

        for c in candidates:
            if c.event.is_expired(now_mono=now_mono):
                rejected.append({"event_id": c.event_id, "reason": "expired"})
                continue
            s = self.score_candidate(c, now_mono=now_mono)
            scored.append((s, c))

        # Deterministic tie-break: higher score, then higher priority, then earlier monotonic ts, then event_id.
        scored.sort(
            key=lambda pair: (
                -pair[0],
                -int(pair[1].event.priority),
                pair[1].event.monotonic_timestamp,
                pair[1].event.event_id,
            )
        )

        ranked = [
            {
                "event_id": c.event_id,
                "score": round(s, 6),
                "event_type": c.event.event_type,
                "priority": int(c.event.priority),
            }
            for s, c in scored
        ]

        if not scored:
            return AttentionDecision(
                selected=None,
                score=0.0,
                reason="no_viable_candidates",
                rejected=rejected,
                ranked=ranked,
            )

        best_score, best = scored[0]
        reason_parts = [
            f"priority={int(best.event.priority)}",
            f"salience={best.salience:.3f}",
            f"confidence={best.event.confidence:.3f}",
            f"attention_flag={best.event.requires_attention}",
        ]
        if best.reason_hints:
            reason_parts.append(f"hints={sorted(best.reason_hints.keys())}")

        return AttentionDecision(
            selected=best,
            score=best_score,
            reason="; ".join(reason_parts),
            rejected=rejected,
            ranked=ranked,
        )
