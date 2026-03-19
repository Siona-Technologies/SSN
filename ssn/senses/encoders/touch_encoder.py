from __future__ import annotations

from typing import Any, Dict

from ssn.senses.contracts import SensorEnvelope
from ssn.senses.encoders.base import EncoderConfig, _packet


class TouchEncoder:
    """
    Somatosensory / touch encoder.

    Expected payload shapes (examples, not strict):
      - dict with aggregate values:
          {
            "pressure": float  (0..1 or arbitrary units),
            "temperature": float (deg C),
            "pain_level": float (0..10),
          }
      - list of samples / pads can be reduced upstream into aggregates.
    """

    config = EncoderConfig(name="touch_encoder", version="0.1")

    def encode(self, env: SensorEnvelope):
        raw = env.payload

        pressure = 0.0
        temperature = 0.0
        pain = 0.0

        if isinstance(raw, dict):
            try:
                pressure = float(raw.get("pressure", 0.0) or 0.0)
            except Exception:
                pressure = 0.0
            try:
                temperature = float(raw.get("temperature", 0.0) or 0.0)
            except Exception:
                temperature = 0.0
            try:
                pain = float(raw.get("pain_level", 0.0) or 0.0)
            except Exception:
                pain = 0.0

        features: Dict[str, Any] = {
            "pressure": pressure,
            "temperature": temperature,
            "pain_level": pain,
        }

        # Simple anomaly heuristic:
        # - strong pain or extreme temperature → high anomaly
        high_pain = pain >= 7.0
        extreme_temp = temperature <= 0.0 or temperature >= 45.0

        if high_pain or extreme_temp:
            anomaly = 0.95
            confidence = 0.8
        elif pressure > 0.0 or temperature != 0.0 or pain > 0.0:
            anomaly = 0.25
            confidence = 0.6
        else:
            anomaly = 0.1
            confidence = 0.3

        return _packet(
            env=env,
            features=features,
            anomaly_score=anomaly,
            confidence=confidence,
            meta={"encoder": self.config.name},
        )

