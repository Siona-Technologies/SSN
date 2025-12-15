import unittest
from unittest.mock import patch

from ssn.runtime.runtime_builder import SSNRuntimeBuilder


class TestPhase62TraceAndWorldPersistence(unittest.TestCase):
    def test_sense_tick_persists_trace_and_updates_world(self):
        rt = SSNRuntimeBuilder.build_default(default_role="GUEST")

        with patch("ssn.interfaces.handlers_sense_tick.verify_owner", return_value={
            "master_key_score": 1.0, "biometric_score": 0.0, "behavior_score": 0.0, "overall_score": 0.7
        }), patch("ssn.interfaces.handlers_sense_tick.is_samson_verified", return_value=True):
            resp = rt.shell.handle_event({
                "type": "sense_tick",
                "role": "OWNER",
                "context": {"master_key": "TEST", "events": [{"type": "motion_event", "sensor_type": "vision", "confidence": 0.8}]},
                "meta": {},
            })

        self.assertTrue(resp.ok)
        rep = (resp.data or {}).get("report", {})
        self.assertTrue(rep.get("ok", False))
        self.assertGreaterEqual(rep.get("processed", 0), 1)

        # These are the two invariants we care about
        self.assertTrue(rep.get("world_updated", False), "Expected world_updated=True after WorldModel update API is present.")
        self.assertTrue(rep.get("trace_written", False), "Expected trace_written=True after TraceMemory adapters are present.")

        # Also ensure world now has at least 1 event
        with patch("ssn.interfaces.handlers_world.verify_owner", return_value={
            "master_key_score": 1.0, "biometric_score": 0.0, "behavior_score": 0.0, "overall_score": 0.7
        }), patch("ssn.interfaces.handlers_world.is_samson_verified", return_value=True):
            w = rt.shell.handle_event({
                "type": "world",
                "role": "OWNER",
                "context": {"master_key": "TEST", "max_entities": 10, "max_events": 20, "include_events": True},
                "meta": {},
            })

        self.assertTrue(w.ok)
        world = (w.data or {}).get("world", {})
        self.assertGreaterEqual(len(world.get("events", [])), 1)


if __name__ == "__main__":
    unittest.main()
