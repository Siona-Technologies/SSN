# ssn/senses/encoders/event_encoder.py

from __future__ import annotations

from typing import Any, Dict, List

from ssn.senses.contracts import SensorEnvelope
from ssn.senses.encoders.base import EncoderConfig, _packet


class EventCameraEncoder:
    config = EncoderConfig(name="event_camera_encoder", version="0.1")

    def encode(self, env: SensorEnvelope):
        raw = env.payload

        # Expect list of events: [{"x":..,"y":..,"t":..,"p":..}, ...]
        events: List[dict] = []
        if isinstance(raw, list):
            for e in raw:
                if isinstance(e, dict):
                    events.append(e)

        cnt = len(events)
        pol_sum = 0
        for e in events[:5000]:
            p = e.get("p", 0)
            try:
                pol_sum += 1 if int(p) > 0 else -1
            except Exception:
                continue

        features: Dict[str, Any] = {
            "event_count": cnt,
            "polarity_balance": pol_sum,
        }

        anomaly = 0.85 if cnt == 0 else (0.6 if cnt < 50 else 0.12)
        conf = 0.2 if cnt == 0 else (0.35 if cnt < 50 else 0.75)

        return _packet(env=env, features=features, anomaly_score=anomaly, confidence=conf, meta={"encoder": self.config.name})
