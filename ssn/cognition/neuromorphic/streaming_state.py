"""Bounded lifecycle/state table for Phase 5 streaming neuromorphic inference.

No learned inference occurs here. The prepare/commit split lets a future provider
compute one LIF step without mutating state until the computation succeeds.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Callable, Dict, List, Tuple

from ssn.cognition.neuromorphic.streaming_contracts import (
    HIDDEN_MEMBRANE_UNITS,
    MAX_ACTIVE_STREAMS,
    STEPS_PER_STREAM,
    STREAM_IDLE_TTL_SECONDS,
    PreparedStreamingStep,
    StreamingNeuromorphicContractError,
    StreamingStreamSnapshot,
    StreamingTemporalStep,
    validate_membrane,
    validate_stream_id,
)


class StreamingNeuromorphicStateError(StreamingNeuromorphicContractError):
    """Fail-closed stream lifecycle/state error."""


@dataclass
class _MutableState:
    stream_id: str
    next_step_index: int
    membrane: Tuple[float, ...]
    cumulative_spike_count: int
    created_at_monotonic: float
    last_activity_monotonic: float
    revision: int


class StreamingStateTable:
    """Bounded explicit-start stream state with deterministic TTL cleanup."""

    def __init__(
        self,
        *,
        max_active_streams: int = MAX_ACTIVE_STREAMS,
        idle_ttl_seconds: float = STREAM_IDLE_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if type(max_active_streams) is not int or max_active_streams <= 0 or max_active_streams > MAX_ACTIVE_STREAMS:
            raise StreamingNeuromorphicStateError("max_active_streams_invalid")
        if isinstance(idle_ttl_seconds, bool) or not isinstance(idle_ttl_seconds, (int, float)):
            raise StreamingNeuromorphicStateError("idle_ttl_seconds_invalid")
        if not math.isfinite(float(idle_ttl_seconds)) or not 0 < float(idle_ttl_seconds) <= STREAM_IDLE_TTL_SECONDS:
            raise StreamingNeuromorphicStateError("idle_ttl_seconds_invalid")
        if not callable(clock):
            raise StreamingNeuromorphicStateError("clock_not_callable")
        self._max_active_streams = max_active_streams
        self._idle_ttl_seconds = float(idle_ttl_seconds)
        self._clock = clock
        self._states: Dict[str, _MutableState] = {}

    @property
    def max_active_streams(self) -> int:
        return self._max_active_streams

    @property
    def idle_ttl_seconds(self) -> float:
        return self._idle_ttl_seconds

    def _now(self) -> float:
        value = self._clock()
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise StreamingNeuromorphicStateError("clock_value_invalid")
        return float(value)

    @staticmethod
    def _snapshot(state: _MutableState) -> StreamingStreamSnapshot:
        return StreamingStreamSnapshot(
            stream_id=state.stream_id,
            next_step_index=state.next_step_index,
            membrane=state.membrane,
            cumulative_spike_count=state.cumulative_spike_count,
            created_at_monotonic=state.created_at_monotonic,
            last_activity_monotonic=state.last_activity_monotonic,
            revision=state.revision,
        )

    def cleanup_expired(self) -> Tuple[str, ...]:
        now = self._now()
        expired = sorted(
            stream_id
            for stream_id, state in self._states.items()
            if now - state.last_activity_monotonic >= self._idle_ttl_seconds
        )
        for stream_id in expired:
            del self._states[stream_id]
        return tuple(expired)

    def active_stream_ids(self) -> Tuple[str, ...]:
        self.cleanup_expired()
        return tuple(sorted(self._states))

    def active_stream_count(self) -> int:
        return len(self.active_stream_ids())

    def start_stream(self, stream_id: str) -> StreamingStreamSnapshot:
        stream_id = validate_stream_id(stream_id)
        self.cleanup_expired()
        if stream_id in self._states:
            raise StreamingNeuromorphicStateError("stream_already_active")
        if len(self._states) >= self._max_active_streams:
            raise StreamingNeuromorphicStateError("active_stream_capacity_reached")
        now = self._now()
        state = _MutableState(
            stream_id=stream_id,
            next_step_index=0,
            membrane=(0.0,) * HIDDEN_MEMBRANE_UNITS,
            cumulative_spike_count=0,
            created_at_monotonic=now,
            last_activity_monotonic=now,
            revision=0,
        )
        self._states[stream_id] = state
        return self._snapshot(state)

    def get_stream(self, stream_id: str) -> StreamingStreamSnapshot:
        stream_id = validate_stream_id(stream_id)
        self.cleanup_expired()
        state = self._states.get(stream_id)
        if state is None:
            raise StreamingNeuromorphicStateError("stream_not_active")
        return self._snapshot(state)

    def prepare_step(self, step: StreamingTemporalStep) -> PreparedStreamingStep:
        if not isinstance(step, StreamingTemporalStep):
            raise StreamingNeuromorphicStateError("step_wrong_type")
        self.cleanup_expired()
        state = self._states.get(step.stream_id)
        if state is None:
            raise StreamingNeuromorphicStateError("stream_not_active")
        if step.step_index != state.next_step_index:
            raise StreamingNeuromorphicStateError("step_index_not_expected")
        return PreparedStreamingStep(step=step, state=self._snapshot(state))

    def commit_step(
        self,
        prepared: PreparedStreamingStep,
        *,
        membrane: Tuple[float, ...] | List[float],
        spike_increment: int,
    ) -> StreamingStreamSnapshot:
        if not isinstance(prepared, PreparedStreamingStep):
            raise StreamingNeuromorphicStateError("prepared_step_wrong_type")
        parsed_membrane = validate_membrane(membrane)
        if type(spike_increment) is not int or spike_increment < 0:
            raise StreamingNeuromorphicStateError("spike_increment_invalid")

        state = self._states.get(prepared.step.stream_id)
        if state is None:
            raise StreamingNeuromorphicStateError("stream_not_active")
        if state.revision != prepared.state.revision or state.next_step_index != prepared.step.step_index:
            raise StreamingNeuromorphicStateError("prepared_state_stale")

        now = self._now()
        next_index = prepared.step.step_index + 1
        completed = next_index == STEPS_PER_STREAM
        committed = _MutableState(
            stream_id=state.stream_id,
            next_step_index=next_index,
            membrane=parsed_membrane,
            cumulative_spike_count=state.cumulative_spike_count + spike_increment,
            created_at_monotonic=state.created_at_monotonic,
            last_activity_monotonic=now,
            revision=state.revision + 1,
        )
        snapshot = self._snapshot(committed)
        if completed:
            del self._states[state.stream_id]
        else:
            self._states[state.stream_id] = committed
        return snapshot

    def reset_stream(self, stream_id: str) -> bool:
        stream_id = validate_stream_id(stream_id)
        return self._states.pop(stream_id, None) is not None

    def reset(self) -> None:
        self._states.clear()
