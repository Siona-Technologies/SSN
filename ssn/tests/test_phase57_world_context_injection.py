# ssn/tests/test_phase57_world_context_injection.py

import unittest
from unittest.mock import patch

from ssn.core.orchestrator import Orchestrator


class DummyWorldModel:
    def snapshot(self, include_events=True, max_events=50):
        # intentionally oversized to test bounding/redaction
        ents = []
        for i in range(50):
            ents.append({
                "id": f"e{i}",
                "entity": "person",
                "status": "present",
                "confidence": 0.7,
                "last_seen": 1000.0 + i,
                "attributes": {f"k{j}": j for j in range(50)},  # lots of keys
                "source": "perception",
            })

        evs = []
        for i in range(50):
            evs.append({
                "type": "motion_event",
                "ts": 2000.0 + i,
                "confidence": 0.6,
                "source": "perception",
                "payload": {"huge": "x" * 10000},  # should not appear in world context
            })

        return {
            "ts": 9999.0,
            "entity_count": len(ents),
            "entities": ents,
            "events": evs[-max_events:],
        }


class TestPhase57WorldContextInjection(unittest.TestCase):

    def test_owner_receives_world_context_in_fusion(self):
        orch = Orchestrator(world_model=DummyWorldModel())

        # ensure policy always allows for test
        orch.policy.check_permission = lambda role, action: True

        captured = {}

        def fuse_spy(user_input, role="GUEST", context=None, mode="hybrid"):
            captured["role"] = role
            captured["context"] = context or {}
            return {
                "role": role,
                "mode": mode,
                "fusion_score": 0.5,
                "cognition_llm": {},
                "perception_snn": {"signal_strength": 0.1, "anomaly_score": 0.1, "spikes_detected": 1, "meta": {}},
                "final_message": "ok",
            }

        orch.fusion.fuse = fuse_spy
        orch.router.route = lambda role, user_input, context=None: {"engine": "test", "note": "skip"}

        with patch("ssn.core.orchestrator.verify_owner", return_value={
            "master_key_score": 1.0, "biometric_score": 0.0, "behavior_score": 0.0, "overall_score": 0.7
        }), patch("ssn.core.orchestrator.is_samson_verified", return_value=True):
            orch.run(master_key="dummy", user_input="hi", context={"topic": "x"})

        self.assertEqual(captured["role"], "OWNER")
        self.assertIn("world", captured["context"])

        world = captured["context"]["world"]
        self.assertTrue(world.get("available"))
        self.assertLessEqual(len(world.get("entities", [])), 8)
        self.assertLessEqual(len(world.get("events", [])), 8)

        # ensure payload not present in event summaries
        for ev in world.get("events", []):
            self.assertNotIn("payload", ev)

        # ensure attributes are bounded
        for e in world.get("entities", []):
            attrs = e.get("attributes", {})
            self.assertTrue(isinstance(attrs, dict))
            self.assertLessEqual(len(attrs.keys()), 11)  # max_attr_keys + possible "…"

    def test_guest_does_not_receive_world_context(self):
        orch = Orchestrator(world_model=DummyWorldModel())
        orch.policy.check_permission = lambda role, action: True

        captured = {}

        def fuse_spy(user_input, role="GUEST", context=None, mode="hybrid"):
            captured["role"] = role
            captured["context"] = context or {}
            return {
                "role": role,
                "mode": mode,
                "fusion_score": 0.5,
                "cognition_llm": {},
                "perception_snn": {"signal_strength": 0.1, "anomaly_score": 0.1, "spikes_detected": 1, "meta": {}},
                "final_message": "ok",
            }

        orch.fusion.fuse = fuse_spy
        orch.router.route = lambda role, user_input, context=None: {"engine": "test", "note": "skip"}

        with patch("ssn.core.orchestrator.verify_owner", return_value={
            "master_key_score": 0.0, "biometric_score": 0.0, "behavior_score": 0.0, "overall_score": 0.0
        }), patch("ssn.core.orchestrator.is_samson_verified", return_value=False):
            orch.run(master_key=None, user_input="hi", context={"topic": "x"})

        self.assertEqual(captured["role"], "GUEST")
        self.assertNotIn("world", captured["context"])


if __name__ == "__main__":
    unittest.main()
