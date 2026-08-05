"""
Legacy adapter: preserve existing SNNEngine behind NeuromorphicProvider.

Does not delete or rewrite SNNEngine — wraps it for the new abstraction.
Also provides a NeuromorphicProvider that exposes the legacy dict API.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from ssn.core.snn_engine import SNNEngine
from ssn.cognition.neuromorphic.contracts import (
    AnomalyOutput,
    NeuromorphicCapabilities,
    NeuromorphicEvent,
    NeuromorphicOutput,
    NeuromorphicState,
    SalienceOutput,
)
from ssn.cognition.neuromorphic.providers import (
    DeterministicNeuromorphicProvider,
    data_to_neuromorphic_event,
)


class LegacySNNEngineAdapter:
    """
    NeuromorphicProvider wrapping the existing Phase-1 SNNEngine.

    NOTE: The underlying SNNEngine uses random values and is a simulation.
    Prefer DeterministicNeuromorphicProvider for canonical new runtime tests.
    """

    name = "siona-legacy-snn-adapter-v1"

    def __init__(self, engine: Optional[SNNEngine] = None) -> None:
        self._engine = engine or SNNEngine()
        self._state = NeuromorphicState(backend=self.name)
        self._count = 0

    def capabilities(self) -> NeuromorphicCapabilities:
        return NeuromorphicCapabilities(
            backends=["legacy-snn-engine"],
            stateful=False,
            spike_traces=False,
            energy_metrics=False,
            batch=True,
            deterministic=False,
            metadata={
                "simulated": True,
                "legacy": True,
                "wrapped": getattr(self._engine, "engine_name", "SNNEngine"),
                "warning": "Underlying SNNEngine is non-deterministic (random).",
            },
        )

    def health(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "provider": self.name,
            "legacy_engine": getattr(self._engine, "engine_name", "SNNEngine"),
            "events": self._count,
            "simulated": True,
        }

    def reset(self) -> None:
        self._state = NeuromorphicState(backend=self.name)
        self._count = 0

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

    def process_event(self, event: NeuromorphicEvent) -> NeuromorphicOutput:
        self._count += 1
        self._state.step += 1
        raw = self._engine.process(event.features, metadata=event.metadata)
        strength = float(raw.get("signal_strength") or 0.0)
        anomaly = float(raw.get("anomaly_score") or 0.0)
        spikes = int(raw.get("spikes_detected") or 0)
        salience = max(0.0, min(1.0, 0.5 * strength + 0.5 * anomaly))
        self._state.last_salience = salience
        self._state.last_anomaly = anomaly
        return NeuromorphicOutput(
            signal_strength=strength,
            anomaly_score=anomaly,
            spikes_detected=spikes,
            salience=SalienceOutput(score=salience, reason="legacy_snn"),
            novelty=0.0,
            anomaly=AnomalyOutput(score=anomaly, is_anomaly=anomaly >= 0.65),
            attention_trigger=salience >= 0.55,
            backend=self.name,
            simulated=True,
            meta={"legacy": True, "raw_meta": raw.get("meta") or {}},
        )

    def process_batch(self, events: Sequence[NeuromorphicEvent]) -> List[NeuromorphicOutput]:
        return [self.process_event(e) for e in events]


class NeuromorphicSNNFacade:
    """
    Drop-in stand-in for SNNEngine.process(data, metadata) using a
    NeuromorphicProvider (default: deterministic reference).

    Use in new runtime paths; leave BrainRouter on legacy SNNEngine unless
    explicitly injected.
    """

    def __init__(self, provider: Optional[Any] = None) -> None:
        self._provider = provider or DeterministicNeuromorphicProvider()
        self.engine_name = getattr(self._provider, "name", "neuromorphic-facade")

    def process(self, data: Any, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        event = data_to_neuromorphic_event(data, metadata)
        out = self._provider.process_event(event)
        return out.to_legacy_dict()
