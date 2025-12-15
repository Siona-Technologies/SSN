# ssn/tests/test_phase59_world_interface_action.py

import unittest
from unittest.mock import patch

from ssn.interfaces.handlers_world import handle_world


class DummyWorldModel:
    def snapshot(self, include_events=True, max_events=50):
        ents = [
            {"id": "e1", "entity": "person", "status": "present", "confidence": 0.7, "last_seen": 1.0, "attributes": {"zone": "front"}, "source": "perception"}
        ]
        evs = [
            {"type": "motion_event", "ts": 10.0, "confidence": 0.6, "source": "perception", "payload": {"huge": "X" * 9999}}
        ]
        return {"ts": 999.0, "entity_count": len(ents), "entities": ents, "events": evs[-max_events:]}


class TestPhase59WorldInterfaceAction(unittest.TestCase):

    def test_world_blocks_without_owner_verification(self):
        req = {"role": "OWNER", "context": {"master_key": None}}
        deps = {"world_model": DummyWorldModel()}

        with patch("ssn.interfaces.handlers_world.verify_owner", return_value={
            "master_key_score": 0.0, "biometric_score": 0.0, "behavior_score": 0.0, "overall_score": 0.0
        }), patch("ssn.interfaces.handlers_world.is_samson_verified", return_value=False):
            out = handle_world(req, deps)

        self.assertTrue(out["ok"])
        self.assertEqual(out["action"], "world")
        self.assertFalse(out["data"]["identity_verified"])
        self.assertFalse(out["data"]["allowed"])
        self.assertEqual(out["data"]["final_result"], "BLOCKED_BY_POLICY")

    def test_world_returns_context_and_summary_for_owner(self):
        req = {"role": "OWNER", "context": {"master_key": "x", "max_entities": 8, "max_events": 8, "include_events": True}}
        deps = {"world_model": DummyWorldModel()}

        with patch("ssn.interfaces.handlers_world.verify_owner", return_value={
            "master_key_score": 1.0, "biometric_score": 0.0, "behavior_score": 0.0, "overall_score": 0.7
        }), patch("ssn.interfaces.handlers_world.is_samson_verified", return_value=True):
            out = handle_world(req, deps)

        self.assertTrue(out["ok"])
        self.assertTrue(out["data"]["identity_verified"])
        self.assertTrue(out["data"]["allowed"])
        self.assertIn("world", out["data"])
        self.assertIn("world_summary", out["data"])
        self.assertTrue(isinstance(out["data"]["world_summary"], str))

        # ensure event payload is not included in summary-context events
        world = out["data"]["world"]
        for ev in world.get("events", []):
            self.assertNotIn("payload", ev)


if __name__ == "__main__":
    unittest.main()
