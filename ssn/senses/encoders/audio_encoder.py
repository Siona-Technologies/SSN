# ssn/senses/encoders/audio_encoder.py

from __future__ import annotations

import hashlib
from typing import Any, Dict

from ssn.senses.contracts import SensorEnvelope
from ssn.senses.encoders.base import EncoderConfig, _packet


class AudioEncoder:
    config = EncoderConfig(name="audio_encoder", version="0.1")

    def encode(self, env: SensorEnvelope):
        raw = env.payload
        if isinstance(raw, (bytes, bytearray)):
            blob = bytes(raw)
        else:
            blob = str(raw).encode("utf-8", errors="ignore")

        h = hashlib.sha256(blob).hexdigest()
        # simple audio signature (placeholder)
        sig = [int(h[i:i+2], 16) / 255.0 for i in range(0, 16, 2)]

        features: Dict[str, Any] = {
            "audio_sig": sig,
            "fingerprint": h[:16],
        }
        anomaly = 0.85 if not raw else 0.15
        conf = 0.55 if raw else 0.15

        return _packet(env=env, features=features, anomaly_score=anomaly, confidence=conf, meta={"encoder": self.config.name})
