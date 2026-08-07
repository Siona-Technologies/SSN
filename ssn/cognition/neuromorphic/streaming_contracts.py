"""Strict Phase 5 streaming-neuromorphic contracts.

EXP-5-001 freezes the event envelope, lifecycle state and resource bounds only.
It does not run learned inference or alter the accepted Phase 4 artifact.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional, Sequence, Tuple

from ssn.cognition.neuromorphic.contracts import NeuromorphicOutput

STREAMING_PROVIDER_ID = "siona-neuro-streaming-lif-v1"
STREAMING_MODALITY = "temporal_salience_step_v1"
STEPS_PER_STREAM = 20
FEATURES_PER_STEP = 8
HIDDEN_MEMBRANE_UNITS = 16
MAX_STREAM_ID_CHARS = 128
MAX_EVENT_ID_CHARS = 128
MAX_ACTIVE_STREAMS = 64
STREAM_IDLE_TTL_SECONDS = 60.0


class StreamingNeuromorphicContractError(ValueError):
    """Fail-closed Phase 5 streaming contract violation."""


def _bounded_nonempty_string(value: object, *, label: str, max_chars: int) -> str:
    if type(value) is not str:
        raise StreamingNeuromorphicContractError(f"{label}_not_str")
    if not value:
        raise StreamingNeuromorphicContractError(f"{label}_empty")
    if len(value) > max_chars:
        raise StreamingNeuromorphicContractError(f"{label}_too_long")
    return value


def validate_stream_id(value: object) -> str:
    return _bounded_nonempty_string(value, label="stream_id", max_chars=MAX_STREAM_ID_CHARS)


def validate_event_id(value: object) -> str:
    return _bounded_nonempty_string(value, label="event_id", max_chars=MAX_EVENT_ID_CHARS)


def validate_step_index(value: object) -> int:
    if type(value) is not int:
        raise StreamingNeuromorphicContractError("step_index_not_int")
    if value < 0 or value >= STEPS_PER_STREAM:
        raise StreamingNeuromorphicContractError("step_index_out_of_range")
    return value


def parse_step_values(values: object) -> Tuple[float, ...]:
    if not isinstance(values, (list, tuple)):
        raise StreamingNeuromorphicContractError("values_not_list_or_tuple")
    if len(values) != FEATURES_PER_STEP:
        raise StreamingNeuromorphicContractError("values_wrong_length")
    parsed = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise StreamingNeuromorphicContractError("values_non_binary_numeric")
        number = float(value)
        if not math.isfinite(number) or number not in (0.0, 1.0):
            raise StreamingNeuromorphicContractError("values_non_binary_numeric")
        parsed.append(number)
    return tuple(parsed)


def validate_membrane(values: Sequence[float]) -> Tuple[float, ...]:
    if not isinstance(values, (list, tuple)) or len(values) != HIDDEN_MEMBRANE_UNITS:
        raise StreamingNeuromorphicContractError("membrane_wrong_shape")
    parsed = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise StreamingNeuromorphicContractError("membrane_non_finite_or_non_numeric")
        number = float(value)
        if not math.isfinite(number):
            raise StreamingNeuromorphicContractError("membrane_non_finite_or_non_numeric")
        parsed.append(number)
    return tuple(parsed)


@dataclass(frozen=True)
class StreamingTemporalStep:
    event_id: str
    stream_id: str
    step_index: int
    values: Tuple[float, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", validate_event_id(self.event_id))
        object.__setattr__(self, "stream_id", validate_stream_id(self.stream_id))
        object.__setattr__(self, "step_index", validate_step_index(self.step_index))
        object.__setattr__(self, "values", parse_step_values(self.values))


@dataclass(frozen=True)
class StreamingStreamSnapshot:
    stream_id: str
    generation: int
    next_step_index: int
    membrane: Tuple[float, ...]
    cumulative_spike_count: int
    created_at_monotonic: float
    last_activity_monotonic: float
    revision: int

    def __post_init__(self) -> None:
        validate_stream_id(self.stream_id)
        if type(self.generation) is not int or self.generation <= 0:
            raise StreamingNeuromorphicContractError("generation_invalid")
        if type(self.next_step_index) is not int or not 0 <= self.next_step_index <= STEPS_PER_STREAM:
            raise StreamingNeuromorphicContractError("next_step_index_invalid")
        object.__setattr__(self, "membrane", validate_membrane(self.membrane))
        if type(self.cumulative_spike_count) is not int or self.cumulative_spike_count < 0:
            raise StreamingNeuromorphicContractError("cumulative_spike_count_invalid")
        for label, value in (
            ("created_at_monotonic", self.created_at_monotonic),
            ("last_activity_monotonic", self.last_activity_monotonic),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise StreamingNeuromorphicContractError(f"{label}_invalid")
        if float(self.last_activity_monotonic) < float(self.created_at_monotonic):
            raise StreamingNeuromorphicContractError("last_activity_before_creation")
        if type(self.revision) is not int or self.revision < 0:
            raise StreamingNeuromorphicContractError("revision_invalid")


@dataclass(frozen=True)
class PreparedStreamingStep:
    step: StreamingTemporalStep
    state: StreamingStreamSnapshot


@dataclass(frozen=True)
class StreamingStepResult:
    stream_id: str
    accepted_step_index: int
    completed: bool
    cumulative_spike_count: int
    final_output: Optional[NeuromorphicOutput] = None

    def __post_init__(self) -> None:
        validate_stream_id(self.stream_id)
        validate_step_index(self.accepted_step_index)
        if type(self.completed) is not bool:
            raise StreamingNeuromorphicContractError("completed_not_bool")
        if type(self.cumulative_spike_count) is not int or self.cumulative_spike_count < 0:
            raise StreamingNeuromorphicContractError("result_spike_count_invalid")
        if self.completed and self.final_output is None:
            raise StreamingNeuromorphicContractError("completed_requires_final_output")
        if not self.completed and self.final_output is not None:
            raise StreamingNeuromorphicContractError("incomplete_must_not_expose_final_output")
