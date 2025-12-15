# ssn/tests/test_phase50_sensory_contracts.py

import unittest
import time

from ssn.senses.contracts import SensorEnvelope, PerceptionPacket, WorldStateDelta


class TestPhase50SensoryContracts(unittest.TestCase):

    def test_sensor_envelope_valid(self):
        env = SensorEnvelope(
            sensor_type="cctv_frame",
            ts=time.time(),
            device_id="cam01",
            stream_id="front_door",
            payload=b"\x00\x01",
            privacy="sensitive",
            quality="ok",
            meta={"fps": 15},
        )
        env.validate()

    def test_sensor_envelope_invalid_ts(self):
        env = SensorEnvelope(sensor_type="imu_sample", ts=-1.0, device_id="imu", stream_id="default")
        with self.assertRaises(ValueError):
            env.validate()

    def test_perception_packet_bounds(self):
        pkt = PerceptionPacket(
            source_sensor="vision_frame",
            device_id="cam01",
            stream_id="front_door",
            features={"embedding": [0.1, 0.2, 0.3]},
            anomaly_score=0.7,
            confidence=0.9,
            privacy="internal",
        )
        pkt.validate()

        bad = PerceptionPacket(anomaly_score=1.5)
        with self.assertRaises(ValueError):
            bad.validate()

    def test_world_state_delta_valid(self):
        d = WorldStateDelta(
            source="perception",
            changes=[{"type": "entity_detected", "entity": "person", "id": "unknown"}],
            confidence=0.8,
        )
        d.validate()


if __name__ == "__main__":
    unittest.main()
