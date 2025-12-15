# ssn/tests/test_phase53_spike_bridge.py

import unittest
import time

from ssn.senses.contracts import PerceptionPacket
from ssn.senses.spike_bridge import SpikeBridge, SpikeBridgeConfig
from ssn.core.snn_engine import SNNEngine


class TestPhase53SpikeBridge(unittest.TestCase):

    def test_spike_bridge_generates_spikes_from_embedding(self):
        pkt = PerceptionPacket(
            ts=time.time(),
            source_sensor="vision_frame",
            device_id="cam01",
            stream_id="front",
            features={"embedding": [0.01, 0.25, 0.05, 0.9]},
            anomaly_score=0.2,
            confidence=0.8,
            privacy="internal",
        )
        bridge = SpikeBridge(SpikeBridgeConfig(threshold=0.2, max_spikes=16))
        out = bridge.to_spikes(pkt)

        self.assertIn("spikes", out)
        self.assertTrue(len(out["spikes"]) >= 1)
        # indices should be ints, values floats
        i0, v0 = out["spikes"][0]
        self.assertIsInstance(i0, int)
        self.assertIsInstance(v0, float)

    def test_spike_bridge_fallback_heartbeat(self):
        pkt = PerceptionPacket(
            ts=time.time(),
            source_sensor="imu_sample",
            device_id="imu01",
            stream_id="base",
            features={"accel": [0.0, 0.0, 0.0]},
            anomaly_score=0.9,
            confidence=0.2,
            privacy="internal",
        )
        bridge = SpikeBridge(SpikeBridgeConfig(threshold=0.5, max_spikes=8))
        out = bridge.to_spikes(pkt)
        self.assertGreaterEqual(len(out["spikes"]), 1)

    def test_feed_snn_engine(self):
        pkt = PerceptionPacket(
            ts=time.time(),
            source_sensor="event_camera",
            device_id="ev01",
            stream_id="s",
            features={"event_count": 120, "polarity_balance": -3},
            anomaly_score=0.3,
            confidence=0.7,
            privacy="internal",
        )
        bridge = SpikeBridge()
        snn = SNNEngine()

        snn_out = bridge.feed_snn(snn, pkt)
        # expect standard snn output keys from your engine
        self.assertIsInstance(snn_out, dict)
        self.assertIn("signal_strength", snn_out)
        self.assertIn("anomaly_score", snn_out)


if __name__ == "__main__":
    unittest.main()
