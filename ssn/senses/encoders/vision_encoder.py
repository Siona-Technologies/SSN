# ssn/senses/encoders/vision_encoder.py

from __future__ import annotations

import hashlib
from typing import Any, Dict

from ssn.senses.contracts import SensorEnvelope
from ssn.senses.encoders.base import EncoderConfig, _packet


class VisionEncoder:
    config = EncoderConfig(name="vision_encoder", version="0.1")

    def encode(self, env: SensorEnvelope):
        # Accept bytes or dict; deterministic fingerprint features (placeholder)
        raw = env.payload
        if isinstance(raw, (bytes, bytearray)):
            blob = bytes(raw)
        else:
            blob = str(raw).encode("utf-8", errors="ignore")

        h = hashlib.sha256(blob).hexdigest()
        # simple 8-dim numeric "embedding" from hash (placeholder)
        emb = [int(h[i:i+4], 16) / 65535.0 for i in range(0, 32, 4)]

        features: Dict[str, Any] = {
            "embedding": emb,
            "fingerprint": h[:16],
        }
        # naive anomaly heuristic: empty payload is anomalous
        anomaly = 0.9 if not raw else 0.1
        conf = 0.6 if raw else 0.2

        return _packet(env=env, features=features, anomaly_score=anomaly, confidence=conf, meta={"encoder": self.config.name})
