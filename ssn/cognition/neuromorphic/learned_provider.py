"""Learned temporal-salience neuromorphic provider (software SNN).

Loads the EXP-4-003 canonical candidate and runs pure-Python LIF inference.
Explicit activation only — never the default NeuromorphicSNNFacade provider.

Weights are executable only after byte-level SHA-256 verification of an artifact
file. Arbitrary in-memory weight mappings are not accepted.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

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
LEARNED_FEATURE_KEYS = frozenset({LEARNED_FEATURE_KEY})
MAX_EVENT_ID_CHARS = 128
MAX_LEARNED_BATCH_EVENTS = 256
MAX_FALLBACK_REASON_CHARS = 64


class LearnedNeuromorphicInputError(ValueError):
    """Malformed event that claims the learned temporal-salience modality."""


def _validate_event_id(event_id: object) -> str:
    if not isinstance(event_id, str) or isinstance(event_id, bool):
        raise LearnedNeuromorphicInputError("event_id_invalid")
    if not event_id or len(event_id) > MAX_EVENT_ID_CHARS:
        raise LearnedNeuromorphicInputError("event_id_invalid")
    return event_id


def _validate_learned_event(event: object) -> Tuple[NeuromorphicEvent, Tuple[Tuple[float, ...], ...]]:
    if not isinstance(event, NeuromorphicEvent):
        raise LearnedNeuromorphicInputError("event_not_neuromorphic_event")
    _validate_event_id(event.event_id)
    if not isinstance(event.modality, str) or isinstance(event.modality, bool):
        raise LearnedNeuromorphicInputError("modality_invalid")
    if event.modality != LEARNED_MODALITY:
        raise LearnedNeuromorphicInputError("modality_not_learned")
    features = event.features
    if not isinstance(features, dict) or isinstance(features, bool):
        raise LearnedNeuromorphicInputError("features_not_dict")
    if set(features.keys()) != LEARNED_FEATURE_KEYS:
        raise LearnedNeuromorphicInputError("features_key_set_invalid")
    try:
        sequence = parse_temporal_sequence(features[LEARNED_FEATURE_KEY])
    except LearnedNeuromorphicInferenceError as exc:
        raise LearnedNeuromorphicInputError(str(exc)) from exc
    return event, sequence


class LearnedTemporalSalienceProvider:
    """Explicit learned SNN provider for phase4a-temporal-salience-v1."""

    name = PROVIDER_TARGET

    def __init__(
        self,
        *,
        artifact_path: Path | str | None = None,
        fallback: Optional[Any] = None,
        expected_sha256: str = APPROVED_ARTIFACT_SHA256,
    ) -> None:
        # Weights come only from verified artifact file bytes — no in-memory inject.
        self._artifact = load_learned_artifact(
            artifact_path,
            expected_sha256=expected_sha256,
        )
        self._fallback = fallback if fallback is not None else DeterministicNeuromorphicProvider()
        self._event_count = 0
        self._learned_count = 0
        self._fallback_count = 0
        self._rejected_input_count = 0
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
                "energy_note": "energy field is compatibility zero; not a measured energy claim",
                "max_batch_events": MAX_LEARNED_BATCH_EVENTS,
            },
        )

    def health(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "provider": self.name,
            "events": self._event_count,
            "learned_events": self._learned_count,
            "fallback_events": self._fallback_count,
            "rejected_inputs": self._rejected_input_count,
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
            "energy_metrics": False,
            "energy_note": "energy field is compatibility zero; not a measured energy claim",
        }

    def reset(self) -> None:
        self._state = NeuromorphicState(backend=self.name)
        self._event_count = 0
        self._learned_count = 0
        self._fallback_count = 0
        self._rejected_input_count = 0
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
            "energy_metrics": False,
        }
        meta.update(extra)
        return meta

    def _fallback_output(self, event: NeuromorphicEvent, reason: str) -> NeuromorphicOutput:
        bounded_reason = reason[:MAX_FALLBACK_REASON_CHARS]
        self._event_count += 1
        self._fallback_count += 1
        out = self._fallback.process_event(event)
        meta = dict(out.meta)
        meta.update(
            {
                "learned_provider_fallback": True,
                "fallback_reason": bounded_reason,
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

    def _learned_output(
        self,
        event: NeuromorphicEvent,
        sequence: Sequence[Sequence[float]],
    ) -> NeuromorphicOutput:
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
        self._event_count += 1
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
                energy_note="compatibility_zero_not_measured",
            ),
        )

    def process_event(self, event: object) -> NeuromorphicOutput:
        if not isinstance(event, NeuromorphicEvent):
            self._rejected_input_count += 1
            raise LearnedNeuromorphicInputError("event_not_neuromorphic_event")
        if not isinstance(event.modality, str) or isinstance(event.modality, bool):
            self._rejected_input_count += 1
            raise LearnedNeuromorphicInputError("modality_invalid")
        if event.modality != LEARNED_MODALITY:
            return self._fallback_output(event, "unsupported_modality")
        try:
            validated, sequence = _validate_learned_event(event)
        except LearnedNeuromorphicInputError:
            self._rejected_input_count += 1
            raise
        return self._learned_output(validated, sequence)

    def process_batch(self, events: object) -> List[NeuromorphicOutput]:
        if not isinstance(events, (list, tuple)):
            self._rejected_input_count += 1
            raise LearnedNeuromorphicInputError("batch_container_invalid")
        if len(events) > MAX_LEARNED_BATCH_EVENTS:
            self._rejected_input_count += 1
            raise LearnedNeuromorphicInputError("batch_too_large")

        # Atomic prevalidation for claimed learned events before any mutation.
        prepared: List[Tuple[str, Any]] = []
        for event in events:
            if not isinstance(event, NeuromorphicEvent):
                self._rejected_input_count += 1
                raise LearnedNeuromorphicInputError("event_not_neuromorphic_event")
            if not isinstance(event.modality, str) or isinstance(event.modality, bool):
                self._rejected_input_count += 1
                raise LearnedNeuromorphicInputError("modality_invalid")
            if event.modality == LEARNED_MODALITY:
                try:
                    validated, sequence = _validate_learned_event(event)
                except LearnedNeuromorphicInputError:
                    self._rejected_input_count += 1
                    raise
                prepared.append(("learned", (validated, sequence)))
            else:
                prepared.append(("fallback", event))

        outputs: List[NeuromorphicOutput] = []
        for kind, payload in prepared:
            if kind == "learned":
                validated, sequence = payload
                outputs.append(self._learned_output(validated, sequence))
            else:
                outputs.append(self._fallback_output(payload, "unsupported_modality"))
        return outputs


def build_learned_temporal_salience_provider(
    *,
    artifact_path: Path | str | None = None,
    fallback: Optional[Any] = None,
) -> LearnedTemporalSalienceProvider:
    """Explicit factory — does not alter NeuromorphicSNNFacade defaults."""
    return LearnedTemporalSalienceProvider(artifact_path=artifact_path, fallback=fallback)
