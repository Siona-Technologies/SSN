"""Phase 5A streaming neuromorphic contract loader and model-free lifecycle scaffold.

This module freezes EXP-5-001 readiness semantics only. It does not load the
Phase 4 artifact, run LIF inference, or activate a streaming learned provider.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from ssn.cognition.neuromorphic.contracts import NeuromorphicEvent

ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = ROOT / "config" / "phase5a_streaming_neuromorphic_contract.json"
RESERVED_PROVIDER_ID = "siona-neuro-streaming-lif-v1"
STREAMING_MODALITY = "temporal_salience_stream_v1"
STEP_FEATURE_KEYS = frozenset({"channels", "sequence_index", "stream_id"})
RESET_FEATURE_KEYS = frozenset({"lifecycle_op", "stream_id"})
STREAM_RESET_OP = "stream_reset"
LIFECYCLE_STATES = ("NONEXISTENT", "ACTIVE", "COMPLETED")


class StreamingContractError(ValueError):
    """Malformed streaming contract document."""


class StreamingLifecycleError(ValueError):
    """Rejected streaming lifecycle or envelope input."""


def load_streaming_contract(path: Path | str | None = None) -> Dict[str, Any]:
    target = Path(path) if path is not None else CONTRACT_PATH
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StreamingContractError("contract_unreadable") from exc
    if not isinstance(payload, dict) or isinstance(payload, bool):
        raise StreamingContractError("contract_not_object")
    _require_frozen_fields(payload)
    return payload


def _require_frozen_fields(payload: Mapping[str, Any]) -> None:
    if payload.get("experiment_id") != "EXP-5-001":
        raise StreamingContractError("experiment_id_invalid")
    provider = payload.get("provider")
    if not isinstance(provider, dict) or provider.get("reserved_id") != RESERVED_PROVIDER_ID:
        raise StreamingContractError("provider_id_invalid")
    if provider.get("global_default") is not False:
        raise StreamingContractError("provider_must_not_be_global_default")
    if provider.get("implementation_accepted") is not False:
        raise StreamingContractError("implementation_must_not_be_accepted")
    dims = payload.get("temporal_dimensions")
    if not isinstance(dims, dict):
        raise StreamingContractError("temporal_dimensions_missing")
    if dims.get("timesteps") != 20 or dims.get("channels_per_step") != 8:
        raise StreamingContractError("temporal_dimensions_invalid")
    if dims.get("sequence_index_min") != 0 or dims.get("sequence_index_max") != 19:
        raise StreamingContractError("sequence_range_invalid")
    bounds = payload.get("bounds")
    if not isinstance(bounds, dict):
        raise StreamingContractError("bounds_missing")
    if bounds.get("max_active_learned_streams") != 256:
        raise StreamingContractError("active_stream_bound_invalid")
    if bounds.get("max_stream_id_chars") != 128:
        raise StreamingContractError("stream_id_bound_invalid")
    if bounds.get("max_stored_temporal_raw_payload_history") != 0:
        raise StreamingContractError("raw_history_retention_invalid")
    ttl = payload.get("idle_ttl")
    if not isinstance(ttl, dict):
        raise StreamingContractError("idle_ttl_missing")
    if not isinstance(ttl.get("value"), int) or isinstance(ttl.get("value"), bool):
        raise StreamingContractError("idle_ttl_invalid")
    if int(ttl["value"]) <= 0 or ttl.get("unit") != "milliseconds":
        raise StreamingContractError("idle_ttl_invalid")
    capacity = payload.get("capacity_policy")
    if not isinstance(capacity, dict) or capacity.get("on_limit_reached") != "FAIL_CLOSED":
        raise StreamingContractError("capacity_policy_invalid")
    if capacity.get("silent_eviction_of_active_streams_forbidden") is not True:
        raise StreamingContractError("capacity_policy_invalid")
    if capacity.get("lru_eviction_of_active_streams_forbidden") is not True:
        raise StreamingContractError("capacity_policy_invalid")


def _bounded_id(value: object, *, field: str, max_chars: int) -> str:
    if not isinstance(value, str) or isinstance(value, bool):
        raise StreamingLifecycleError(f"{field}_invalid")
    if not value or len(value) > max_chars:
        raise StreamingLifecycleError(f"{field}_invalid")
    return value


def validate_streaming_step_event(
    event: object,
    *,
    contract: Optional[Mapping[str, Any]] = None,
) -> Tuple[str, int, Tuple[float, ...], str]:
    spec = contract if contract is not None else load_streaming_contract()
    step = spec["streaming_step_event"]
    max_event = int(step["event_id"]["max_chars"])
    max_stream = int(step["stream_id"]["max_chars"])
    if not isinstance(event, NeuromorphicEvent):
        raise StreamingLifecycleError("event_not_neuromorphic_event")
    event_id = _bounded_id(event.event_id, field="event_id", max_chars=max_event)
    if not isinstance(event.modality, str) or isinstance(event.modality, bool):
        raise StreamingLifecycleError("modality_invalid")
    if event.modality != STREAMING_MODALITY:
        raise StreamingLifecycleError("modality_not_streaming")
    features = event.features
    if not isinstance(features, dict) or isinstance(features, bool):
        raise StreamingLifecycleError("features_not_dict")
    if set(features.keys()) != STEP_FEATURE_KEYS:
        raise StreamingLifecycleError("features_key_set_invalid")
    stream_id = _bounded_id(features["stream_id"], field="stream_id", max_chars=max_stream)
    index = features["sequence_index"]
    if isinstance(index, bool) or not isinstance(index, int):
        raise StreamingLifecycleError("sequence_index_invalid")
    if index < 0 or index > 19:
        raise StreamingLifecycleError("sequence_index_out_of_range")
    channels = _parse_binary_channels(features["channels"])
    return stream_id, index, channels, event_id


def validate_stream_reset_event(
    event: object,
    *,
    contract: Optional[Mapping[str, Any]] = None,
) -> str:
    spec = contract if contract is not None else load_streaming_contract()
    max_event = int(spec["streaming_step_event"]["event_id"]["max_chars"])
    max_stream = int(spec["streaming_step_event"]["stream_id"]["max_chars"])
    if not isinstance(event, NeuromorphicEvent):
        raise StreamingLifecycleError("event_not_neuromorphic_event")
    _bounded_id(event.event_id, field="event_id", max_chars=max_event)
    if event.modality != STREAMING_MODALITY:
        raise StreamingLifecycleError("modality_not_streaming")
    features = event.features
    if not isinstance(features, dict) or isinstance(features, bool):
        raise StreamingLifecycleError("features_not_dict")
    if set(features.keys()) != RESET_FEATURE_KEYS:
        raise StreamingLifecycleError("features_key_set_invalid")
    if features.get("lifecycle_op") != STREAM_RESET_OP:
        raise StreamingLifecycleError("lifecycle_op_invalid")
    return _bounded_id(features["stream_id"], field="stream_id", max_chars=max_stream)


def _parse_binary_channels(value: object) -> Tuple[float, ...]:
    if not isinstance(value, (list, tuple)):
        raise StreamingLifecycleError("channels_not_list")
    if len(value) != 8:
        raise StreamingLifecycleError("channels_length_invalid")
    parsed: List[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise StreamingLifecycleError("channels_non_binary_numeric")
        number = float(item)
        if not math.isfinite(number) or number not in (0.0, 1.0):
            raise StreamingLifecycleError("channels_non_binary_numeric")
        parsed.append(number)
    return tuple(parsed)


@dataclass(frozen=True)
class StreamLifecycleSnapshot:
    stream_id: str
    state: str
    next_expected_sequence_index: int
    last_success_mono: float
    raw_payload_history: Tuple[Any, ...] = ()


class StreamingLifecycleTracker:
    """Model-free lifecycle/state-machine scaffold. No LIF, weights, or outputs."""

    def __init__(
        self,
        *,
        contract: Optional[Mapping[str, Any]] = None,
        now: Optional[Callable[[], float]] = None,
    ) -> None:
        self._contract = dict(contract) if contract is not None else load_streaming_contract()
        self._now = now or time.monotonic
        self._streams: Dict[str, StreamLifecycleSnapshot] = {}
        self.success_count = 0
        self.failure_count = 0

    @property
    def resident_count(self) -> int:
        return len(self._streams)

    def snapshot(self) -> Dict[str, StreamLifecycleSnapshot]:
        return dict(self._streams)

    def expire_idle(self) -> List[str]:
        ttl_s = float(self._contract["idle_ttl"]["value"]) / 1000.0
        now = float(self._now())
        expired = [
            stream_id
            for stream_id, record in self._streams.items()
            if (now - record.last_success_mono) > ttl_s
        ]
        for stream_id in expired:
            del self._streams[stream_id]
        return expired

    def ingest_step(self, event: NeuromorphicEvent) -> StreamLifecycleSnapshot:
        self.expire_idle()
        before = self.snapshot()
        success_before = self.success_count
        try:
            stream_id, index, _channels, _event_id = validate_streaming_step_event(
                event,
                contract=self._contract,
            )
            record = self._streams.get(stream_id)
            if record is None:
                if index != 0:
                    raise StreamingLifecycleError("NONEXISTENT_PLUS_STEP_NOT_ZERO")
                max_streams = int(self._contract["bounds"]["max_active_learned_streams"])
                if len(self._streams) >= max_streams:
                    raise StreamingLifecycleError("CAPACITY_EXHAUSTION_WITHOUT_EXPIRY_SLOT")
                updated = StreamLifecycleSnapshot(
                    stream_id=stream_id,
                    state="ACTIVE",
                    next_expected_sequence_index=1,
                    last_success_mono=float(self._now()),
                )
            else:
                if record.state == "COMPLETED":
                    raise StreamingLifecycleError("COMPLETED_PLUS_ANY_STEP_WITHOUT_NEW_LIFECYCLE")
                expected = record.next_expected_sequence_index
                if index == expected:
                    next_index = index + 1
                    state = "COMPLETED" if index == 19 else "ACTIVE"
                    updated = StreamLifecycleSnapshot(
                        stream_id=stream_id,
                        state=state,
                        next_expected_sequence_index=next_index,
                        last_success_mono=float(self._now()),
                    )
                elif index < expected:
                    if index == expected - 1:
                        raise StreamingLifecycleError("ACTIVE_DUPLICATE_SEQUENCE_INDEX")
                    raise StreamingLifecycleError("ACTIVE_BACKWARDS_OR_OUT_OF_ORDER_INDEX")
                else:
                    raise StreamingLifecycleError("ACTIVE_SKIPPED_SEQUENCE_INDEX")
            self._streams[stream_id] = updated
            self.success_count += 1
            return updated
        except StreamingLifecycleError:
            self.failure_count += 1
            self._streams = before
            self.success_count = success_before
            raise

    def reset_stream(self, event: NeuromorphicEvent) -> None:
        self.expire_idle()
        before = self.snapshot()
        success_before = self.success_count
        try:
            stream_id = validate_stream_reset_event(event, contract=self._contract)
            if stream_id not in self._streams:
                raise StreamingLifecycleError("stream_reset_nonexistent")
            del self._streams[stream_id]
            self.success_count += 1
        except StreamingLifecycleError:
            self.failure_count += 1
            self._streams = before
            self.success_count = success_before
            raise

    def reset_provider(self) -> None:
        self._streams.clear()

    def state_of(self, stream_id: str) -> str:
        record = self._streams.get(stream_id)
        return record.state if record is not None else "NONEXISTENT"
