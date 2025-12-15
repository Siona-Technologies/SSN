# ssn/tests/test_phase60_world_runtime_wiring.py

import unittest
from unittest.mock import patch

from ssn.runtime.runtime_builder import SSNRuntimeBuilder


class TestPhase60WorldRuntimeWiring(unittest.TestCase):
    def test_runtime_builder_wires_world_model_into_gateway(self):
        rt = SSNRuntimeBuilder.build_default(default_role="GUEST")

        # gateway should exist
        self.assertIsNotNone(rt.gateway)

        # deps should contain world_model if gateway supports it
        deps = getattr(rt.gateway, "deps", {})
        self.assertIsInstance(deps, dict)

        # best-effort: allow either gateway deps or orchestrator attribute
        world_model = deps.get("world_model", None)
        if world_model is None and rt.orchestrator is not None:
            world_model = getattr(rt.orchestrator, "world_model", None)

        self.assertIsNotNone(world_model, "world_model was not wired into runtime (gateway deps / orchestrator).")

    def test_world_action_returns_available_true_when_owner_verified(self):
        rt = SSNRuntimeBuilder.build_default(default_role="GUEST")

        # Patch owner verification so test doesn't depend on local secret files
        with patch("ssn.interfaces.handlers_world.verify_owner", return_value={
            "master_key_score": 1.0,
            "biometric_score": 0.0,
            "behavior_score": 0.0,
            "overall_score": 0.7,
        }), patch("ssn.interfaces.handlers_world.is_samson_verified", return_value=True):
            resp = rt.shell.handle_event(
                {
                    "type": "world",
                    "role": "OWNER",
                    "text": "",
                    "context": {
                        "master_key": "TEST_KEY",
                        "max_entities": 10,
                        "max_events": 20,
                        "include_events": True,
                    },
                    "meta": {},
                }
            )

        # InterfaceResponse shape
        self.assertTrue(resp.ok)
        self.assertEqual(resp.action, "world")
        self.assertEqual(resp.role, "OWNER")

        data = resp.data or {}
        self.assertTrue(data.get("allowed", False))
        self.assertTrue(data.get("identity_verified", False))

        world = data.get("world", {})
        self.assertIsInstance(world, dict)
        self.assertTrue(world.get("available", False), "world.available should be True when world_model is wired.")
        self.assertIn("entity_count", world)
        self.assertIn("entities", world)
        self.assertIn("events", world)

        summary = data.get("world_summary", "")
        self.assertIsInstance(summary, str)
        self.assertTrue(len(summary) > 0)


if __name__ == "__main__":
    unittest.main()
