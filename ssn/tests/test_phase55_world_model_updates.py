# ssn/tests/test_phase55_world_model_updates.py

import unittest

from ssn.senses.contracts import WorldStateDelta
from ssn.world.world_model import WorldModel, WorldModelConfig


class FakeClock:
    def __init__(self, t0: float = 1000.0):
        self.t = float(t0)

    def now(self) -> float:
        return float(self.t)

    def advance(self, dt: float) -> None:
        self.t += float(dt)


class TestPhase55WorldModelUpdates(unittest.TestCase):

    def test_entity_detected_and_snapshot(self):
        clk = FakeClock(1000.0)
        wm = WorldModel(config=WorldModelConfig(max_entities=10, max_events=50, entity_ttl_sec=60.0), now_fn=clk.now)

        d = WorldStateDelta(
            ts=clk.now(),
            source="perception",
            changes=[{"type": "entity_detected", "entity": "person", "id": "p1", "attributes": {"zone": "front"}}],
            confidence=0.8,
        )
        rep = wm.apply_delta(d)
        self.assertEqual(rep["added"], 1)
        self.assertEqual(rep["entities"], 1)

        snap = wm.snapshot()
        self.assertEqual(snap["entity_count"], 1)
        self.assertEqual(snap["entities"][0]["id"], "p1")
        self.assertEqual(snap["entities"][0]["entity"], "person")
        self.assertEqual(snap["entities"][0]["attributes"]["zone"], "front")

    def test_decay_removes_old_entities(self):
        clk = FakeClock(1000.0)
        wm = WorldModel(config=WorldModelConfig(max_entities=10, max_events=50, entity_ttl_sec=10.0), now_fn=clk.now)

        wm.apply_delta(WorldStateDelta(
            ts=clk.now(),
            source="perception",
            changes=[{"type": "entity_detected", "entity": "person", "id": "p1"}],
            confidence=0.6,
        ))
        self.assertEqual(wm.snapshot()["entity_count"], 1)

        clk.advance(11.0)
        decayed = wm.decay()
        self.assertEqual(decayed, 1)
        self.assertEqual(wm.snapshot()["entity_count"], 0)

    def test_entity_cap_evicts_oldest(self):
        clk = FakeClock(1000.0)
        wm = WorldModel(config=WorldModelConfig(max_entities=2, max_events=50, entity_ttl_sec=1000.0), now_fn=clk.now)

        wm.apply_delta(WorldStateDelta(ts=clk.now(), source="perception",
                                       changes=[{"type": "entity_detected", "entity": "obj", "id": "e1"}],
                                       confidence=0.5))
        clk.advance(1.0)
        wm.apply_delta(WorldStateDelta(ts=clk.now(), source="perception",
                                       changes=[{"type": "entity_detected", "entity": "obj", "id": "e2"}],
                                       confidence=0.5))
        clk.advance(1.0)
        rep = wm.apply_delta(WorldStateDelta(ts=clk.now(), source="perception",
                                             changes=[{"type": "entity_detected", "entity": "obj", "id": "e3"}],
                                             confidence=0.5))

        self.assertGreaterEqual(rep["evicted"], 1)
        snap = wm.snapshot()
        ids = [e["id"] for e in snap["entities"]]
        self.assertNotIn("e1", ids)
        self.assertIn("e2", ids)
        self.assertIn("e3", ids)

    def test_events_are_bounded(self):
        clk = FakeClock(1000.0)
        wm = WorldModel(config=WorldModelConfig(max_entities=10, max_events=3, entity_ttl_sec=1000.0), now_fn=clk.now)

        for i in range(6):
            clk.advance(1.0)
            wm.apply_delta(WorldStateDelta(
                ts=clk.now(),
                source="perception",
                changes=[{"type": "motion_event", "area": f"a{i}", "level": 0.1 * i}],
                confidence=0.6,
            ))

        snap = wm.snapshot(include_events=True, max_events=10)
        self.assertIn("events", snap)
        self.assertEqual(len(snap["events"]), 3)  # bounded to max_events=3


if __name__ == "__main__":
    unittest.main()
