# ssn/senses/contracts.py

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


SensorType = Literal[
    "vision_frame",
    "audio_chunk",
    "imu_sample",
    "lidar_scan",
    "event_camera",
    "cctv_frame",
    "custom",
]

PrivacyLevel = Literal["public", "internal", "personal", "sensitive"]

QualityFlag = Literal["ok", "degraded", "missing", "unknown"]


def _now() -> float:
    return float(time.time())


def _is_finite_number(x: Any) -> bool:
    if not isinstance(x, (int, float)):
        return False
    if x != x:  # NaN
        return False
    if x in (float("inf"), float("-inf")):
        return False
    return True


@dataclass(frozen=True)
class SensorEnvelope:
    """
    Normalized sensory input packet (raw or lightly structured).

    - payload is modality-specific (bytes, dict, list, etc.)
    - kept bounded via upstream buffering policies (Phase 5.1)
    """
    sensor_type: SensorType
    ts: float = field(default_factory=_now)
    device_id: str = "unknown"
    stream_id: str = "default"
    payload: Any = None

    # metadata
    privacy: PrivacyLevel = "internal"
    quality: QualityFlag = "ok"
    meta: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not isinstance(self.sensor_type, str) or not self.sensor_type:
            raise ValueError("sensor_type must be a non-empty string.")
        if not _is_finite_number(self.ts) or self.ts <= 0:
            raise ValueError("ts must be a positive finite timestamp.")
        if not isinstance(self.device_id, str) or not self.device_id:
            raise ValueError("device_id must be a non-empty string.")
        if not isinstance(self.stream_id, str) or not self.stream_id:
            raise ValueError("stream_id must be a non-empty string.")
        if not isinstance(self.privacy, str) or not self.privacy:
            raise ValueError("privacy must be a non-empty string.")
        if not isinstance(self.quality, str) or not self.quality:
            raise ValueError("quality must be a non-empty string.")
        if not isinstance(self.meta, dict):
            raise ValueError("meta must be a dict.")


@dataclass(frozen=True)
class PerceptionPacket:
    """
    Output of modality encoders (ready for SNN/Fusion).

    - features may be spikes, embeddings, descriptors, etc.
    - anomaly_score is bounded (0..1)
    """
    ts: float = field(default_factory=_now)
    source_sensor: SensorType = "custom"
    device_id: str = "unknown"
    stream_id: str = "default"

    features: Dict[str, Any] = field(default_factory=dict)  # {"embedding":[...], "spikes":[...]}
    anomaly_score: float = 0.0
    confidence: float = 0.5

    privacy: PrivacyLevel = "internal"
    meta: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not _is_finite_number(self.ts) or self.ts <= 0:
            raise ValueError("ts must be a positive finite timestamp.")
        if not isinstance(self.source_sensor, str) or not self.source_sensor:
            raise ValueError("source_sensor must be a non-empty string.")
        if not isinstance(self.device_id, str) or not self.device_id:
            raise ValueError("device_id must be a non-empty string.")
        if not isinstance(self.stream_id, str) or not self.stream_id:
            raise ValueError("stream_id must be a non-empty string.")
        if not isinstance(self.features, dict):
            raise ValueError("features must be a dict.")
        if not isinstance(self.meta, dict):
            raise ValueError("meta must be a dict.")

        if not _is_finite_number(self.anomaly_score):
            raise ValueError("anomaly_score must be finite.")
        if self.anomaly_score < 0.0 or self.anomaly_score > 1.0:
            raise ValueError("anomaly_score must be in [0, 1].")

        if not _is_finite_number(self.confidence):
            raise ValueError("confidence must be finite.")
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("confidence must be in [0, 1].")

        if not isinstance(self.privacy, str) or not self.privacy:
            raise ValueError("privacy must be a non-empty string.")


@dataclass(frozen=True)
class WorldStateDelta:
    """
    A small update describing how SSN's belief state should change.

    Example:
      - entity_detected: {"entity":"person", "id":"unknown", "location":...}
      - motion_event: {"area":"front_door", "level":0.8}

    This is a delta, not the full world state.
    """
    ts: float = field(default_factory=_now)
    source: str = "perception"
    changes: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.5
    meta: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not _is_finite_number(self.ts) or self.ts <= 0:
            raise ValueError("ts must be a positive finite timestamp.")
        if not isinstance(self.source, str) or not self.source:
            raise ValueError("source must be a non-empty string.")
        if not isinstance(self.changes, list):
            raise ValueError("changes must be a list.")
        for c in self.changes:
            if not isinstance(c, dict):
                raise ValueError("each change must be a dict.")
        if not _is_finite_number(self.confidence):
            raise ValueError("confidence must be finite.")
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("confidence must be in [0, 1].")
        if not isinstance(self.meta, dict):
            raise ValueError("meta must be a dict.")
