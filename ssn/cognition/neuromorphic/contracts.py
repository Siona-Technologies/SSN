"""
Neuromorphic provider contracts.

Focus: salience, novelty, anomaly, temporal activity, attention triggers,
reflex proposals, sensor filtering — NOT full language reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Sequence


@dataclass(frozen=True)
class SpikeBatch:
    """Optional spike trace for backends that expose spikes."""

    neuron_ids: List[int] = field(default_factory=list)
    times_ms: List[float] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)

    @property
    def spike_count(self) -> int:
        if self.counts:
            return int(sum(self.counts.values()))
        return len(self.neuron_ids)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "neuron_ids": list(self.neuron_ids),
            "times_ms": list(self.times_ms),
            "counts": dict(self.counts),
            "spike_count": self.spike_count,
        }


@dataclass(frozen=True)
class NeuromorphicEvent:
    event_id: str
    modality: str
    features: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "modality": self.modality,
            "features": dict(self.features),
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }


@dataclass
class NeuromorphicState:
    step: int = 0
    energy: float = 0.0
    last_salience: float = 0.0
    last_anomaly: float = 0.0
    last_novelty: float = 0.0
    backend: str = ""
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "energy": self.energy,
            "last_salience": self.last_salience,
            "last_anomaly": self.last_anomaly,
            "last_novelty": self.last_novelty,
            "backend": self.backend,
            "extras": dict(self.extras),
        }


@dataclass(frozen=True)
class SalienceOutput:
    score: float
    reason: str = ""
    components: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "reason": self.reason,
            "components": dict(self.components),
        }


@dataclass(frozen=True)
class AnomalyOutput:
    score: float
    reason: str = ""
    is_anomaly: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "reason": self.reason,
            "is_anomaly": self.is_anomaly,
        }


@dataclass(frozen=True)
class NeuromorphicOutput:
    signal_strength: float
    anomaly_score: float
    spikes_detected: int
    salience: SalienceOutput
    novelty: float
    anomaly: AnomalyOutput
    attention_trigger: bool = False
    reflex_proposal: Optional[Dict[str, Any]] = None
    spike_batch: Optional[SpikeBatch] = None
    energy: float = 0.0
    backend: str = ""
    simulated: bool = True
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_legacy_dict(self) -> Dict[str, Any]:
        """Match SNNEngine.process() dict shape for BrainRouter compatibility."""
        return {
            "signal_strength": round(float(self.signal_strength), 3),
            "anomaly_score": round(float(self.anomaly_score), 3),
            "spikes_detected": int(self.spikes_detected),
            "meta": {
                "engine": self.backend,
                "simulated": self.simulated,
                "salience": self.salience.to_dict(),
                "novelty": self.novelty,
                "attention_trigger": self.attention_trigger,
                **dict(self.meta),
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_strength": self.signal_strength,
            "anomaly_score": self.anomaly_score,
            "spikes_detected": self.spikes_detected,
            "salience": self.salience.to_dict(),
            "novelty": self.novelty,
            "anomaly": self.anomaly.to_dict(),
            "attention_trigger": self.attention_trigger,
            "reflex_proposal": self.reflex_proposal,
            "spike_batch": self.spike_batch.to_dict() if self.spike_batch else None,
            "energy": self.energy,
            "backend": self.backend,
            "simulated": self.simulated,
            "meta": dict(self.meta),
        }


@dataclass(frozen=True)
class NeuromorphicCapabilities:
    backends: List[str] = field(default_factory=list)
    stateful: bool = True
    spike_traces: bool = False
    energy_metrics: bool = False
    batch: bool = True
    deterministic: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backends": list(self.backends),
            "stateful": self.stateful,
            "spike_traces": self.spike_traces,
            "energy_metrics": self.energy_metrics,
            "batch": self.batch,
            "deterministic": self.deterministic,
            "metadata": dict(self.metadata),
        }


class NeuromorphicProvider(Protocol):
    name: str

    def capabilities(self) -> NeuromorphicCapabilities:
        ...

    def health(self) -> Dict[str, Any]:
        ...

    def reset(self) -> None:
        ...

    def get_state(self) -> NeuromorphicState:
        ...

    def process_event(self, event: NeuromorphicEvent) -> NeuromorphicOutput:
        ...

    def process_batch(self, events: Sequence[NeuromorphicEvent]) -> List[NeuromorphicOutput]:
        ...
