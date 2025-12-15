# ssn/tests/test_phase56_perception_to_world_model.py

import unittest
import time

from ssn.senses.sensory_bus import SensoryBus
from ssn.senses.contracts import SensorEnvelope
from ssn.senses.encoders.registry import EncoderRegistry
from ssn.senses.encoders.vision_encoder import VisionEncoder
from ssn.senses.encoders.event_encoder import EventCameraEncoder
from ssn.senses.perception_hub import PerceptionHub, PerceptionHubConfig
from ssn.world.world_model import WorldModel, WorldModelConfig


class TestPhase56PerceptionToWorldModel(unittest.TestCase):

    def test_vision_updates_world_model_entity(self):
        bus = SensoryBus(max_events_per_stream=50, max_total_events=200)
        reg = EncoderRegistry()
        reg.register("vision_frame", VisionEncoder())

        wm = WorldModel(config=WorldModelConfig(max_entities=10, max_events=50, entity_ttl_sec=60.0))

        hub = PerceptionHub(
            bus=bus,
            registry=reg,
            world_model=wm,
            config=PerceptionHubConfig(max_events_per_tick=10, trace_enabled=False, world_updates_enabled=True),
        )

        t0 = time.time()
        bus.publish(SensorEnvelope(sensor_type="vision_frame", ts=t0 + 0.01, device_id="cam01", stream_id="front", payload=b"abc", privacy="sensitive"))

        rep = hub.process_once()
        self.assertGreaterEqual(rep["world_applied"], 1)

        snap = wm.snapshot(include_events=True)
        self.assertGreaterEqual(snap["entity_count"], 1)
        ids = [e["id"] for e in snap["entities"]]
        self.assertIn("entity:cam01:front", ids)

    def test_event_camera_motion_event(self):
        bus = SensoryBus(max_events_per_stream=50, max_total_events=200)
        reg = EncoderRegistry()
        reg.register("event_camera", EventCameraEncoder())

        wm = WorldModel(config=WorldModelConfig(max_entities=10, max_events=50, entity_ttl_sec=60.0))

        hub = PerceptionHub(
            bus=bus,
            registry=reg,
            world_model=wm,
            config=PerceptionHubConfig(max_events_per_tick=10, trace_enabled=False, world_updates_enabled=True),
        )

        t0 = time.time()
        # This should produce motion_event via delta builder (event_count >= 50)
        bus.publish(SensorEnvelope(
            sensor_type="event_camera",
            ts=t0 + 0.01,
            device_id="ev01",
            stream_id="areaA",
            payload=[{"x": 1, "y": 2, "t": 0.0, "p": 1}] * 120,
            privacy="internal",
        ))

        rep = hub.process_once()
        self.assertGreaterEqual(rep["world_applied"], 1)

        snap = wm.snapshot(include_events=True, max_events=50)
        ev_types = [e.get("type") for e in snap.get("events", [])]
        self.assertIn("motion_event", ev_types)


if __name__ == "__main__":
    unittest.main()
