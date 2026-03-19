from __future__ import annotations

from typing import Any, Dict

from ssn.senses.contracts import SensorEnvelope
from ssn.senses.encoders.base import EncoderConfig, _packet


class GustatoryEncoder:
    """
    Gustation / taste encoder.

    Expected payload (example dict):
      {
        "sweet": float,
        "sour": float,
        "salty": float,
        "bitter": float,
        "umami": float,
      }
    All values are treated as bounded scores (e.g., 0..1).
    """

    config = EncoderConfig(name="gustatory_encoder", version="0.1")

    def encode(self, env: SensorEnvelope):
        raw = env.payload

        sweet = sour = salty = bitter = umami = 0.0
        if isinstance(raw, dict):
            def f(key: str) -> float:
                try:
                    return float(raw.get(key, 0.0) or 0.0)
                except Exception:
                    return 0.0

            sweet = f("sweet")
            sour = f("sour")
            salty = f("salty")
            bitter = f("bitter")
            umami = f("umami")

        features: Dict[str, Any] = {
            "sweet": sweet,
            "sour": sour,
            "salty": salty,
            "bitter": bitter,
            "umami": umami,
        }

        # Simple anomaly heuristic:
        # - very strong bitter or sour might indicate spoilage.
        if bitter >= 0.8 or sour >= 0.8:
            anomaly = 0.9
            confidence = 0.8
        elif any(v > 0.0 for v in (sweet, sour, salty, bitter, umami)):
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

