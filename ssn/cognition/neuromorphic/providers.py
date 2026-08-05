"""
Deterministic reference neuromorphic provider (simulated, not trained).

Provides stable salience / novelty / anomaly signals for tests and
offline operation. Clearly labeled as simulation.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence

from ssn.cognition.neuromorphic.contracts import (
    AnomalyOutput,
    NeuromorphicCapabilities,
    NeuromorphicEvent,
    NeuromorphicOutput,
    NeuromorphicState,
    SalienceOutput,
    SpikeBatch,
)


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


class DeterministicNeuromorphicProvider:
    """
    Reference neuromorphic backend — SIMULATED / NOT a trained SNN.

    Future backends (snnTorch, Norse, Lava, Loihi, FPGA) implement the
    same NeuromorphicProvider protocol without changing higher layers.
    """

    name = "siona-neuro-deterministic-v1"

    def __init__(self, *, anomaly_threshold: float = 0.65) -> None:
        self.anomaly_threshold = float(anomaly_threshold)
        self._state = NeuromorphicState(backend=self.name)
        self._seen_hashes: Dict[str, int] = {}
        self._event_count = 0

    def capabilities(self) -> NeuromorphicCapabilities:
        return NeuromorphicCapabilities(
            backends=["deterministic-reference"],
            stateful=True,
            spike_traces=True,
            energy_metrics=True,
            batch=True,
            deterministic=True,
            metadata={
                "simulated": True,
                "trained": False,
                "note": "Reference provider for tests; not biological SNN.",
            },
        )

    def health(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "provider": self.name,
            "events": self._event_count,
            "simulated": True,
        }

    def reset(self) -> None:
        self._state = NeuromorphicState(backend=self.name)
        self._seen_hashes.clear()
        self._event_count = 0

    def get_state(self) -> NeuromorphicState:
        return NeuromorphicState(
            step=self._state.step,
            energy=self._state.energy,
            last_salience=self._state.last_salience,
            last_anomaly=self._state.last_anomaly,
            last_novelty=self._state.last_novelty,
            backend=self.name,
            extras=dict(self._state.extras),
        )

    def _feature_strength(self, event: NeuromorphicEvent) -> float:
        feats = event.features or {}
        if "signal_strength" in feats:
            return _clip01(float(feats["signal_strength"]))
        if "embedding" in feats and isinstance(feats["embedding"], (list, tuple)):
            emb = [float(x) for x in feats["embedding"][:64]]
            if not emb:
                return 0.1
            mean = sum(abs(x) for x in emb) / len(emb)
            return _clip01(mean)
        if "text" in feats:
            return _clip01(len(str(feats["text"])) / 50.0)
        # Stable hash-based residual signal (not random)
        blob = json.dumps(
            {"modality": event.modality, "features": feats},
            sort_keys=True,
            default=str,
        )
        h = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        return _clip01(int(h[:8], 16) / 0xFFFFFFFF)

    def _hash_event(self, event: NeuromorphicEvent) -> str:
        blob = json.dumps(
            {
                "modality": event.modality,
                "features": event.features,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    def process_event(self, event: NeuromorphicEvent) -> NeuromorphicOutput:
        self._event_count += 1
        self._state.step += 1

        strength = self._feature_strength(event)
        eh = self._hash_event(event)
        seen = self._seen_hashes.get(eh, 0)
        self._seen_hashes[eh] = seen + 1
        novelty = 1.0 if seen == 0 else _clip01(1.0 / (seen + 1))

        # Anomaly rises when strength is extreme or novelty is high with low confidence.
        anomaly = _clip01((1.0 - strength) * 0.4 + novelty * 0.35 + (1.0 - event.confidence) * 0.25)
        is_anomaly = anomaly >= self.anomaly_threshold

        salience = _clip01(0.45 * strength + 0.35 * novelty + 0.20 * anomaly)
        spikes = int(strength * 10) + int(novelty * 3)
        energy = _clip01(0.01 * spikes + 0.02 * salience)

        # Deterministic synthetic spike trace
        spike_ids = list(range(spikes))
        spike_times = [float(i) * 0.5 for i in spike_ids]
        batch = SpikeBatch(
            neuron_ids=spike_ids,
            times_ms=spike_times,
            counts={"total": spikes},
        )

        attention = salience >= 0.55 or is_anomaly or bool(event.metadata.get("force_attention"))
        reflex: Optional[Dict[str, Any]] = None
        if is_anomaly and salience >= 0.7:
            reflex = {
                "kind": "reflex",
                "action": "attend",
                "confidence": salience,
                "reason": "high_salience_anomaly",
                "simulated": True,
            }

        self._state.energy += energy
        self._state.last_salience = salience
        self._state.last_anomaly = anomaly
        self._state.last_novelty = novelty

        return NeuromorphicOutput(
            signal_strength=round(strength, 3),
            anomaly_score=round(anomaly, 3),
            spikes_detected=spikes,
            salience=SalienceOutput(
                score=round(salience, 3),
                reason="deterministic_mix",
                components={
                    "strength": round(strength, 3),
                    "novelty": round(novelty, 3),
                    "anomaly": round(anomaly, 3),
                },
            ),
            novelty=round(novelty, 3),
            anomaly=AnomalyOutput(
                score=round(anomaly, 3),
                reason="threshold_compare" if is_anomaly else "within_bounds",
                is_anomaly=is_anomaly,
            ),
            attention_trigger=attention,
            reflex_proposal=reflex,
            spike_batch=batch,
            energy=round(energy, 4),
            backend=self.name,
            simulated=True,
            meta={
                "event_id": event.event_id,
                "modality": event.modality,
                "step": self._state.step,
                "used_metadata": bool(event.metadata),
            },
        )

    def process_batch(self, events: Sequence[NeuromorphicEvent]) -> List[NeuromorphicOutput]:
        return [self.process_event(e) for e in events]


def data_to_neuromorphic_event(data: Any, metadata: Optional[Dict] = None) -> NeuromorphicEvent:
    """Convert legacy SNNEngine.process(data, metadata) inputs to NeuromorphicEvent."""
    import time
    import uuid

    features: Dict[str, Any]
    modality = "generic"
    if isinstance(data, (int, float)):
        features = {"signal_strength": min(1.0, abs(float(data)) / 100.0)}
        modality = "numeric"
    elif isinstance(data, bytes):
        features = {"signal_strength": min(1.0, len(data) / 32.0)}
        modality = "bytes"
    elif isinstance(data, str):
        features = {"text": data, "signal_strength": min(1.0, len(data) / 50.0)}
        modality = "text"
    elif isinstance(data, dict):
        features = dict(data)
        modality = str(data.get("modality") or "dict")
    elif isinstance(data, list):
        features = {"embedding": data[:64], "signal_strength": 0.5}
        modality = "list"
    else:
        features = {"signal_strength": 0.1}

    return NeuromorphicEvent(
        event_id=str(uuid.uuid4()),
        modality=modality,
        features=features,
        timestamp=time.time(),
        confidence=1.0,
        metadata=dict(metadata or {}),
    )
