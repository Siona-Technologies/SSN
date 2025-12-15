# ssn/tests/test_phase54_perception_hub.py

import unittest
import time

from ssn.senses.sensory_bus import SensoryBus
from ssn.senses.contracts import SensorEnvelope
from ssn.senses.encoders.registry import EncoderRegistry
from ssn.senses.encoders.vision_encoder import VisionEncoder
from ssn.senses.encoders.imu_encoder import IMUEncoder
from ssn.senses.perception_hub import PerceptionHub, PerceptionHubConfig
from ssn.core.snn_engine import SNNEngine


class DummyMemoryHub:
    def __init__(self):
        self.traces = []

    def add_trace(self, payload=None, **kwargs):
        if payload is None:
            payload = kwargs.get("payload", {})
        self.traces.append(payload)

    def get_recent_traces(self, limit=50):
        return [{"payload": p} for p in self.traces[-limit:]]


class TestPhase54PerceptionHub(unittest.TestCase):

    def test_perception_hub_processes_events_and_writes_trace(self):
        bus = SensoryBus(max_events_per_stream=50, max_total_events=200)
        reg = EncoderRegistry()
        reg.register("vision_frame", VisionEncoder())
        reg.register("imu_sample", IMUEncoder())

        mh = DummyMemoryHub()
        snn = SNNEngine()

        hub = PerceptionHub(
            bus=bus,
            registry=reg,
            snn_engine=snn,
            memory_hub=mh,
            config=PerceptionHubConfig(max_events_per_tick=10, trace_enabled=True),
        )

        t0 = time.time()
        bus.publish(SensorEnvelope(sensor_type="vision_frame", ts=t0 + 0.01, device_id="cam", stream_id="s", payload=b"abc", privacy="sensitive"))
        bus.publish(SensorEnvelope(sensor_type="imu_sample", ts=t0 + 0.02, device_id="imu", stream_id="b", payload={"ax": 1, "ay": 2, "az": 3}, privacy="internal"))

        report = hub.process_once()

        self.assertEqual(report["status"], "ok")
        self.assertGreaterEqual(report["processed"], 2)
        self.assertGreaterEqual(report["trace_written"], 2)
        self.assertTrue(report["has_snn"])

        # Ensure traces are bounded: no raw frame bytes under a "payload" field
        last = mh.traces[-1]
        self.assertEqual(last.get("type"), "perception_tick_item")
        self.assertIn("payload_excerpt", last)
        self.assertNotIn("payload", last)

    def test_perception_hub_skips_unknown_sensor_type(self):
        bus = SensoryBus(max_events_per_stream=50, max_total_events=200)
        reg = EncoderRegistry()
        reg.register("vision_frame", VisionEncoder())

        hub = PerceptionHub(bus=bus, registry=reg, config=PerceptionHubConfig(max_events_per_tick=10, trace_enabled=False))

        t0 = time.time()
        bus.publish(SensorEnvelope(sensor_type="custom", ts=t0 + 0.01, device_id="x", stream_id="y", payload={"x": 1}))
        report = hub.process_once()

        self.assertEqual(report["processed"], 0)
        self.assertGreaterEqual(report["skipped"], 1)


if __name__ == "__main__":
    unittest.main()
