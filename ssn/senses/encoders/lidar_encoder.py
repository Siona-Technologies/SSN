# ssn/senses/encoders/lidar_encoder.py

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ssn.senses.contracts import SensorEnvelope
from ssn.senses.encoders.base import EncoderConfig, _packet


class LiDAREncoder:
    config = EncoderConfig(name="lidar_encoder", version="0.1")

    def encode(self, env: SensorEnvelope):
        raw = env.payload

        # Expect list of points or dict with "points"
        pts: List[Tuple[float, float, float]] = []
        if isinstance(raw, dict) and isinstance(raw.get("points"), list):
            for p in raw["points"]:
                if isinstance(p, (list, tuple)) and len(p) >= 3:
                    pts.append((float(p[0]), float(p[1]), float(p[2])))
        elif isinstance(raw, list):
            for p in raw:
                if isinstance(p, (list, tuple)) and len(p) >= 3:
                    pts.append((float(p[0]), float(p[1]), float(p[2])))

        n = len(pts)
        if n == 0:
            features = {"point_count": 0, "bbox": None}
            return _packet(env=env, features=features, anomaly_score=0.9, confidence=0.2, meta={"encoder": self.config.name})

        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        zs = [p[2] for p in pts]
        bbox = {
            "min": [min(xs), min(ys), min(zs)],
            "max": [max(xs), max(ys), max(zs)],
        }

        features: Dict[str, Any] = {"point_count": n, "bbox": bbox}

        # anomaly: extremely sparse scans
        anomaly = 0.7 if n < 20 else 0.15
        conf = 0.55 if n >= 20 else 0.25

        return _packet(env=env, features=features, anomaly_score=anomaly, confidence=conf, meta={"encoder": self.config.name})
