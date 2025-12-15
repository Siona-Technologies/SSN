# ssn/senses/encoders/registry.py

from __future__ import annotations

from typing import Dict, Optional

from ssn.senses.contracts import SensorEnvelope, PerceptionPacket
from ssn.senses.encoders.base import Encoder


class EncoderRegistry:
    """
    Maps sensor_type -> encoder.
    """

    def __init__(self):
        self._encoders: Dict[str, Encoder] = {}

    def register(self, sensor_type: str, encoder: Encoder) -> None:
        if not isinstance(sensor_type, str) or not sensor_type:
            raise ValueError("sensor_type must be a non-empty string.")
        if sensor_type in self._encoders:
            raise ValueError(f"Encoder already registered for sensor_type: {sensor_type}")
        self._encoders[sensor_type] = encoder

    def get(self, sensor_type: str) -> Optional[Encoder]:
        return self._encoders.get(sensor_type)

    def encode(self, env: SensorEnvelope) -> PerceptionPacket:
        enc = self.get(env.sensor_type)
        if enc is None:
            raise KeyError(f"No encoder registered for sensor_type: {env.sensor_type}")
        return enc.encode(env)

    def list(self) -> Dict[str, str]:
        return {k: getattr(v, "config", None).name if getattr(v, "config", None) else v.__class__.__name__ for k, v in self._encoders.items()}
