# ssn/tests/test_phase52_encoders_contracts.py

import unittest
import time

from ssn.senses.contracts import SensorEnvelope, PerceptionPacket
from ssn.senses.encoders.registry import EncoderRegistry
from ssn.senses.encoders.vision_encoder import VisionEncoder
from ssn.senses.encoders.audio_encoder import AudioEncoder
from ssn.senses.encoders.imu_encoder import IMUEncoder
from ssn.senses.encoders.lidar_encoder import LiDAREncoder
from ssn.senses.encoders.event_encoder import EventCameraEncoder


class TestPhase52EncodersContracts(unittest.TestCase):

    def test_registry_and_encode(self):
        reg = EncoderRegistry()
        reg.register("vision_frame", VisionEncoder())
        reg.register("audio_chunk", AudioEncoder())
        reg.register("imu_sample", IMUEncoder())
        reg.register("lidar_scan", LiDAREncoder())
        reg.register("event_camera", EventCameraEncoder())

        now = time.time()

        pkt1 = reg.encode(SensorEnvelope(sensor_type="vision_frame", ts=now, device_id="cam", stream_id="s", payload=b"abc"))
        self.assertIsInstance(pkt1, PerceptionPacket)
        pkt1.validate()
        self.assertIn("embedding", pkt1.features)

        pkt2 = reg.encode(SensorEnvelope(sensor_type="imu_sample", ts=now, device_id="imu", stream_id="b", payload={"ax": 1, "ay": 2, "az": 3}))
        pkt2.validate()
        self.assertIn("accel_mag", pkt2.features)

        pkt3 = reg.encode(SensorEnvelope(sensor_type="lidar_scan", ts=now, device_id="lidar", stream_id="t", payload={"points": [(0,0,0), (1,1,1)]}))
        pkt3.validate()
        self.assertIn("bbox", pkt3.features)

    def test_missing_encoder_raises(self):
        reg = EncoderRegistry()
        with self.assertRaises(KeyError):
            reg.encode(SensorEnvelope(sensor_type="vision_frame", ts=time.time(), device_id="x", stream_id="y", payload=b"z"))


if __name__ == "__main__":
    unittest.main()
