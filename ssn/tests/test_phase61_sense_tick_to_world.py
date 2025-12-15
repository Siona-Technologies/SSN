# ssn/tests/test_phase61_sense_tick_to_world.py

import unittest
from unittest.mock import patch

from ssn.interfaces.gateway import InterfaceGateway
from ssn.interfaces.agent_shell import AgentShell


class DummyWorldModel:
    def __init__(self):
        self._events = []
        self._entities = []

    def apply_update(self, upd):
        for e in upd.get("events", []) or []:
            self._events.append(e)
        for ent in upd.get("entities", []) or []:
            self._entities.append(ent)

    def snapshot(self, include_events=True, max_events=50):
        return {
            "ts": 1.0,
            "entity_count": len(self._entities),
            "entities": list(self._entities),
            "events": list(self._events)[-max_events:] if include_events else [],
        }


class TestPhase61SenseTickToWorld(unittest.TestCase):
    def test_sense_tick_updates_world_model(self):
        wm = DummyWorldModel()

        gw = InterfaceGateway(
            orchestrator=None,
            brain_router=None,
            policy_engine=None,
            safety_monitor=None,
            memory_hub=None,
            suggestion_engine=None,
            tool_bus=None,
            world_model=wm,
        )
        sh = AgentShell(gateway=gw, default_role="GUEST")

        with patch("ssn.interfaces.handlers_sense_tick.verify_owner", return_value={
            "master_key_score": 1.0, "biometric_score": 0.0, "behavior_score": 0.0, "overall_score": 0.7
        }), patch("ssn.interfaces.handlers_sense_tick.is_samson_verified", return_value=True), patch(
            "ssn.interfaces.handlers_world.verify_owner", return_value={
                "master_key_score": 1.0, "biometric_score": 0.0, "behavior_score": 0.0, "overall_score": 0.7
            }
        ), patch("ssn.interfaces.handlers_world.is_samson_verified", return_value=True):

            resp_tick = sh.handle_event({
                "type": "sense_tick",
                "role": "OWNER",
                "context": {"master_key": "TEST", "events": [{"type": "motion_event", "sensor_type": "vision", "confidence": 0.6}]},
                "meta": {},
            })

            self.assertTrue(resp_tick.ok)
            self.assertEqual(resp_tick.action, "sense_tick")
            self.assertTrue(resp_tick.data.get("allowed", False))

            resp_world = sh.handle_event({
                "type": "world",
                "role": "OWNER",
                "context": {"master_key": "TEST", "max_entities": 10, "max_events": 20, "include_events": True},
                "meta": {},
            })

            self.assertTrue(resp_world.ok)
            world = resp_world.data.get("world", {})
            self.assertTrue(world.get("available", True))
            self.assertGreaterEqual(len(world.get("events", [])), 1)


if __name__ == "__main__":
    unittest.main()
