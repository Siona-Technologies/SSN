# ssn/senses/encoders/imu_encoder.py

from __future__ import annotations

from typing import Any, Dict

from ssn.senses.contracts import SensorEnvelope
from ssn.senses.encoders.base import EncoderConfig, _packet


class IMUEncoder:
    config = EncoderConfig(name="imu_encoder", version="0.1")

    def encode(self, env: SensorEnvelope):
        raw = env.payload

        # Expect dict-like: {"ax":..,"ay":..,"az":..,"gx":..,"gy":..,"gz":..}
        ax = ay = az = gx = gy = gz = 0.0
        if isinstance(raw, dict):
            ax = float(raw.get("ax", 0.0) or 0.0)
            ay = float(raw.get("ay", 0.0) or 0.0)
            az = float(raw.get("az", 0.0) or 0.0)
            gx = float(raw.get("gx", 0.0) or 0.0)
            gy = float(raw.get("gy", 0.0) or 0.0)
            gz = float(raw.get("gz", 0.0) or 0.0)

        mag_a = (ax * ax + ay * ay + az * az) ** 0.5
        mag_g = (gx * gx + gy * gy + gz * gz) ** 0.5

        features: Dict[str, Any] = {
            "accel": [ax, ay, az],
            "gyro": [gx, gy, gz],
            "accel_mag": mag_a,
            "gyro_mag": mag_g,
        }

        # anomaly if values are all zero (sensor missing) or absurdly large
        if mag_a == 0.0 and mag_g == 0.0:
            anomaly = 0.9
            conf = 0.2
        elif mag_a > 1000 or mag_g > 1000:
            anomaly = 0.95
            conf = 0.25
        else:
            anomaly = 0.1
            conf = 0.7

        return _packet(env=env, features=features, anomaly_score=anomaly, confidence=conf, meta={"encoder": self.config.name})
