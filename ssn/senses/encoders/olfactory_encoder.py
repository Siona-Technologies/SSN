from __future__ import annotations

from typing import Any, Dict, List

from ssn.senses.contracts import SensorEnvelope
from ssn.senses.encoders.base import EncoderConfig, _packet


class OlfactoryEncoder:
    """
    Olfaction / smell encoder.

    Expected payload shapes (examples):
      - list[float]: raw sensor intensities for chemical channels.
      - dict{"channels": [...]}: list of intensities.
    """

    config = EncoderConfig(name="olfactory_encoder", version="0.1")

    def encode(self, env: SensorEnvelope):
        raw = env.payload
        channels: List[float] = []

        if isinstance(raw, dict) and isinstance(raw.get("channels"), list):
            for v in raw["channels"]:
                try:
                    channels.append(float(v))
                except Exception:
                    continue
        elif isinstance(raw, list):
            for v in raw:
                try:
                    channels.append(float(v))
                except Exception:
                    continue

        if not channels:
            features: Dict[str, Any] = {"channels": [], "intensity_mean": 0.0}
            return _packet(
                env=env,
                features=features,
                anomaly_score=0.8,
                confidence=0.2,
                meta={"encoder": self.config.name},
            )

        n = len(channels)
        intensity_mean = sum(channels) / float(n)
        intensity_max = max(channels)

        features = {
            "channels": channels[:64],  # hard cap
            "intensity_mean": intensity_mean,
            "intensity_max": intensity_max,
        }

        # Heuristic:
        # - extremely high max intensity → anomaly (e.g. gas leak)
        if intensity_max >= 0.9:
            anomaly = 0.95
            confidence = 0.85
        elif intensity_mean > 0.1:
            anomaly = 0.3
            confidence = 0.6
        else:
            anomaly = 0.15
            confidence = 0.4

        return _packet(
            env=env,
            features=features,
            anomaly_score=anomaly,
            confidence=confidence,
            meta={"encoder": self.config.name},
        )

