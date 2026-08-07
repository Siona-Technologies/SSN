"""Learned temporal-salience neuromorphic provider (software SNN).

Loads the EXP-4-003 canonical candidate and runs pure-Python LIF inference.
Explicit activation only — never the default NeuromorphicSNNFacade provider.
"""

from __future__ import annotations

from pathlib import Path
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
from ssn.cognition.neuromorphic.learned_artifact import (
    APPROVED_ARTIFACT_SHA256,
    ARCHITECTURE_ID,
    PROVIDER_TARGET,
    TASK_ID,
    TRAINING_EXPERIMENT,
    LearnedNeuromorphicArtifactError,
    load_learned_artifact,
)
from ssn.cognition.neuromorphic.learned_inference import (
    LearnedNeuromorphicInferenceError,
    forward_lif_final_membrane,
    parse_temporal_sequence,
)
from ssn.cognition.neuromorphic.providers import DeterministicNeuromorphicProvider

LEARNED_MODALITY = "temporal_salience_v1"
LEARNED_FEATURE_KEY = "temporal_sequence"


class LearnedNeuromorphicInputError(ValueError):
    """Malformed event that claims the learned temporal-salience modality."""


class LearnedTemporalSalienceProvider:
    """Explicit learned SNN provider for phase4a-temporal-salience-v1."""

    name = PROVIDER_TARGET

    def __init__(
        self,
        *,
        artifact_path: Path | str | None = None,
        artifact: Dict[str, Any] | None = None,
        fallback: Optional[Any] = None,
        expected_sha256: str = APPROVED_ARTIFACT_SHA256,
    ) -> None:
        if artifact is not None and artifact_path is not None:
            raise LearnedNeuromorphicArtifactError("artifact_source_ambiguous")
        if artifact is None:
            self._artifact = load_learned_artifact(
                artifact_path,
                expected_sha256=expected_sha256,
            )
        else:
            # Already-validated mapping from load_learned_artifact / tests.
            if artifact.get("sha256") != expected_sha256:
                raise LearnedNeuromorphicArtifactError("artifact_sha256_mismatch")
            self._artifact = artifact
        self._fallback = fallback if fallback is not None else DeterministicNeuromorphicProvider()
        self._event_count = 0
        self._learned_count = 0
        self._fallback_count = 0
        self._state = NeuromorphicState(backend=self.name)

        weights = self._artifact["weights"]
        self._fc1_weight = weights["fc1.weight"]
        self._fc1_bias = weights["fc1.bias"]
        self._fc2_weight = weights["fc2.weight"]
        self._fc2_bias = weights["fc2.bias"]
        lif = self._artifact["lif"]
        self._beta = float(lif["beta"])
        self._threshold = float(lif["threshold"])

    @property
    def artifact_sha256(self) -> str:
        return str(self._artifact["sha256"])

    def capabilities(self) -> NeuromorphicCapabilities:
        return NeuromorphicCapabilities(
            backends=["learned-lif-software"],
            stateful=False,
            spike_traces=True,
            energy_metrics=False,
            batch=True,
            deterministic=True,
            metadata={
                "simulated": True,
                "trained": True,
                "learned": True,
                "software_snn": True,
                "hardware_neuromorphic": False,
                "artifact_verified": True,
                "task_id": TASK_ID,
                "architecture_id": ARCHITECTURE_ID,
                "training_experiment": TRAINING_EXPERIMENT,
                "artifact_sha256": self.artifact_sha256,
                "tool_authority": False,
                "physical_actuation_authority": False,
            },
        )

    def health(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "provider": self.name,
            "events": self._event_count,
            "learned_events": self._learned_count,
            "fallback_events": self._fallback_count,
            "simulated": True,
            "trained": True,
            "learned": True,
            "software_snn": True,
            "hardware_neuromorphic": False,
            "artifact_verified": True,
            "task_id": TASK_ID,
            "architecture_id": ARCHITECTURE_ID,
            "training_experiment": TRAINING_EXPERIMENT,
            "artifact_sha256": self.artifact_sha256,
            "tool_authority": False,
            "physical_actuation_authority": False,
        }

    def reset(self) -> None:
        self._state = NeuromorphicState(backend=self.name)
        self._event_count = 0
        self._learned_count = 0
        self._fallback_count = 0
        if hasattr(self._fallback, "reset"):
            self._fallback.reset()

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

    def _common_meta(self, **extra: Any) -> Dict[str, Any]:
        meta = {
            "trained": True,
            "learned": True,
            "software_snn": True,
            "hardware_neuromorphic": False,
            "artifact_verified": True,
            "task_id": TASK_ID,
            "architecture_id": ARCHITECTURE_ID,
            "training_experiment": TRAINING_EXPERIMENT,
            "artifact_sha256": self.artifact_sha256,
            "tool_authority": False,
            "physical_actuation_authority": False,
        }
        meta.update(extra)
        return meta

    def _fallback_output(self, event: NeuromorphicEvent, reason: str) -> NeuromorphicOutput:
        self._fallback_count += 1
        out = self._fallback.process_event(event)
        meta = dict(out.meta)
        meta.update(
            {
                "learned_provider_fallback": True,
                "fallback_reason": reason,
                "learned_provider": self.name,
                "tool_authority": False,
                "physical_actuation_authority": False,
            }
        )
        return NeuromorphicOutput(
            signal_strength=out.signal_strength,
            anomaly_score=out.anomaly_score,
            spikes_detected=out.spikes_detected,
            salience=out.salience,
            novelty=out.novelty,
            anomaly=out.anomaly,
            attention_trigger=out.attention_trigger,
            reflex_proposal=None,
            spike_batch=out.spike_batch,
            energy=out.energy,
            backend=out.backend,
            simulated=True,
            meta=meta,
        )

    def _learned_output(self, event: NeuromorphicEvent, sequence: Sequence[Sequence[float]]) -> NeuromorphicOutput:
        result = forward_lif_final_membrane(
            sequence,
            fc1_weight=self._fc1_weight,
            fc1_bias=self._fc1_bias,
            fc2_weight=self._fc2_weight,
            fc2_bias=self._fc2_bias,
            beta=self._beta,
            threshold=self._threshold,
        )
        positive = float(result["positive_score"])  # type: ignore[arg-type]
        probs = result["probabilities"]  # type: ignore[assignment]
        predicted = int(result["predicted_class"])  # type: ignore[arg-type]
        spikes = int(result["hidden_spike_count"])  # type: ignore[arg-type]
        self._learned_count += 1
        self._state.step += 1
        self._state.last_salience = positive
        self._state.last_anomaly = 0.0
        self._state.last_novelty = 0.0
        return NeuromorphicOutput(
            signal_strength=positive,
            anomaly_score=0.0,
            spikes_detected=spikes,
            salience=SalienceOutput(
                score=positive,
                reason="learned_temporal_salience",
                components={
                    "class_0_probability": float(probs[0]),
                    "class_1_probability": float(probs[1]),
                },
            ),
            novelty=0.0,
            anomaly=AnomalyOutput(
                score=0.0,
                reason="task_does_not_implement_anomaly_detection",
                is_anomaly=False,
            ),
            attention_trigger=(predicted == 1),
            reflex_proposal=None,
            spike_batch=SpikeBatch(counts={"hidden_lif": spikes}),
            energy=0.0,
            backend=self.name,
            simulated=True,
            meta=self._common_meta(
                event_id=event.event_id,
                modality=event.modality,
                predicted_class=predicted,
                logits={
                    "class_0": float(result["logits"][0]),  # type: ignore[index]
                    "class_1": float(result["logits"][1]),  # type: ignore[index]
                },
                learned_provider_fallback=False,
            ),
        )

    def process_event(self, event: NeuromorphicEvent) -> NeuromorphicOutput:
        self._event_count += 1
        if event.modality != LEARNED_MODALITY:
            return self._fallback_output(event, "unsupported_modality")
        features = event.features or {}
        if LEARNED_FEATURE_KEY not in features:
            raise LearnedNeuromorphicInputError("missing_temporal_sequence")
        try:
            sequence = parse_temporal_sequence(features[LEARNED_FEATURE_KEY])
        except LearnedNeuromorphicInferenceError as exc:
            raise LearnedNeuromorphicInputError(str(exc)) from exc
        return self._learned_output(event, sequence)

    def process_batch(self, events: Sequence[NeuromorphicEvent]) -> List[NeuromorphicOutput]:
        return [self.process_event(event) for event in events]


def build_learned_temporal_salience_provider(
    *,
    artifact_path: Path | str | None = None,
    fallback: Optional[Any] = None,
) -> LearnedTemporalSalienceProvider:
    """Explicit factory — does not alter NeuromorphicSNNFacade defaults."""
    return LearnedTemporalSalienceProvider(artifact_path=artifact_path, fallback=fallback)
