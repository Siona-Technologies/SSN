# ssn/tests/test_phase58_world_summary_normalizer.py

import unittest

from ssn.world.world_summary import WorldSummaryNormalizer, WorldSummaryConfig
from ssn.core.fusion_engine import FusionEngine


class TestPhase58WorldSummaryNormalizer(unittest.TestCase):

    def test_world_summary_is_bounded_and_contains_signal(self):
        norm = WorldSummaryNormalizer(WorldSummaryConfig(max_entities=2, max_events=2, max_attr_keys=2, max_chars=180))

        world = {
            "available": True,
            "ts": 999.0,
            "entity_count": 10,
            "entities": [
                {"id": "e1", "entity": "person", "status": "present", "confidence": 0.77, "last_seen": 1.1,
                 "attributes": {"zone": "front", "color": "red", "extra": "x"}, "source": "perception"},
                {"id": "e2", "entity": "object", "status": "present", "confidence": 0.55, "last_seen": 1.0,
                 "attributes": {"zone": "back"}, "source": "perception"},
                {"id": "e3", "entity": "object", "status": "present", "confidence": 0.12, "last_seen": 0.9,
                 "attributes": {"zone": "ignored"}, "source": "perception"},
            ],
            "events": [
                {"type": "motion_event", "ts": 10.0, "confidence": 0.6, "source": "perception", "payload": {"huge": "X" * 9999}},
                {"type": "alert", "ts": 11.0, "confidence": 0.9, "source": "perception"},
                {"type": "sound_event", "ts": 12.0, "confidence": 0.2, "source": "perception"},
            ],
        }

        s = norm.summarize(world)
        self.assertTrue(isinstance(s, str))
        self.assertLessEqual(len(s), 180)
        self.assertIn("World:", s)
        self.assertIn("Top entities:", s)
        self.assertIn("Recent events:", s)
        self.assertIn("e1", s)
        self.assertIn("motion_event", s)

    def test_fusion_engine_injects_world_summary_for_owner(self):
        fe = FusionEngine()

        captured = {}

        def llm_spy(text, context=None, role="GUEST"):
            captured["role"] = role
            captured["context"] = context or {}
            return {"reply": "ok", "role": role, "used_context": bool(context), "engine": "spy"}

        fe.llm.process = llm_spy

        world = {
            "available": True,
            "entity_count": 1,
            "entities": [{"id": "e1", "entity": "person", "status": "present", "confidence": 0.7, "last_seen": 1.0, "attributes": {"zone": "front"}, "source": "perception"}],
            "events": [{"type": "motion_event", "ts": 10.0, "confidence": 0.6, "source": "perception"}],
        }

        out = fe.fuse("hello", role="OWNER", context={"world": world}, mode="hybrid")

        self.assertEqual(captured["role"], "OWNER")
        self.assertIn("world_summary", captured["context"])
        self.assertTrue(isinstance(captured["context"]["world_summary"], str))
        self.assertIn("world_summary", out)
        self.assertTrue(isinstance(out["world_summary"], str))

    def test_guest_does_not_get_world_summary_injected(self):
        fe = FusionEngine()

        captured = {}

        def llm_spy(text, context=None, role="GUEST"):
            captured["role"] = role
            captured["context"] = context or {}
            return {"reply": "ok", "role": role, "used_context": bool(context), "engine": "spy"}

        fe.llm.process = llm_spy

        world = {"available": True, "entity_count": 0, "entities": [], "events": []}
        out = fe.fuse("hello", role="GUEST", context={"world": world}, mode="hybrid")

        self.assertEqual(captured["role"], "GUEST")
        self.assertNotIn("world_summary", captured["context"])
        self.assertNotIn("world_summary", out)


if __name__ == "__main__":
    unittest.main()
