# ssn/senses/encoders/base.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol

from ssn.senses.contracts import SensorEnvelope, PerceptionPacket


@dataclass(frozen=True)
class EncoderConfig:
    name: str
    version: str = "0.1"
    privacy_default: str = "internal"


class Encoder(Protocol):
    config: EncoderConfig

    def encode(self, env: SensorEnvelope) -> PerceptionPacket:
        ...


def _packet(
    *,
    env: SensorEnvelope,
    features: Dict[str, Any],
    anomaly_score: float = 0.0,
    confidence: float = 0.5,
    meta: Optional[Dict[str, Any]] = None,
) -> PerceptionPacket:
    pkt = PerceptionPacket(
        ts=env.ts,
        source_sensor=env.sensor_type,
        device_id=env.device_id,
        stream_id=env.stream_id,
        features=features or {},
        anomaly_score=float(anomaly_score),
        confidence=float(confidence),
        privacy=env.privacy,
        meta=meta or {},
    )
    pkt.validate()
    return pkt
