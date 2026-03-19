from __future__ import annotations

from typing import Any, Dict

from ssn.senses.contracts import SensorEnvelope
from ssn.senses.encoders.base import EncoderConfig, _packet


class InteroceptionEncoder:
    """
    Interoception / internal body state encoder.

    Expected payload (example dict):
      {
        "heart_rate": float,   # bpm
        "resp_rate": float,    # breaths per minute
        "temp_core": float,    # deg C
        "fatigue": float,      # 0..1 subjective
        "stress": float,       # 0..1 subjective
      }
    """

    config = EncoderConfig(name="interoception_encoder", version="0.1")

    def encode(self, env: SensorEnvelope):
        raw = env.payload

        hr = rr = temp = fatigue = stress = 0.0
        if isinstance(raw, dict):
            def f(key: str) -> float:
                try:
                    return float(raw.get(key, 0.0) or 0.0)
                except Exception:
                    return 0.0

            hr = f("heart_rate")
            rr = f("resp_rate")
            temp = f("temp_core")
            fatigue = f("fatigue")
            stress = f("stress")

        features: Dict[str, Any] = {
            "heart_rate": hr,
            "resp_rate": rr,
            "temp_core": temp,
            "fatigue": fatigue,
            "stress": stress,
        }

        # Anomaly heuristic: out-of-range vitals or extreme stress/fatigue.
        vitals_bad = (
            hr <= 35.0 or hr >= 140.0 or
            rr <= 6.0 or rr >= 30.0 or
            temp <= 34.0 or temp >= 39.0
        )
        high_stress = stress >= 0.8
        high_fatigue = fatigue >= 0.8

        if vitals_bad or high_stress or high_fatigue:
            anomaly = 0.96
            confidence = 0.85
        elif any(v > 0.0 for v in (hr, rr, temp, fatigue, stress)):
            anomaly = 0.3
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

