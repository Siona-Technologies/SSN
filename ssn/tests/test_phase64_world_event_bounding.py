# ssn/tests/test_phase64_world_event_bounding.py

from __future__ import annotations

import os
import unittest

from ssn.runtime.runtime_builder import SSNRuntimeBuilder


WORLD_PATH = "ssn/data/world_model.json"
TRACE_PATH = "ssn/data/trace_memory.json"


def _rm_if_exists(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


class TestPhase64WorldEventBounding(unittest.TestCase):
    def setUp(self) -> None:
        # Ensure a master key is available (tests in earlier phases expect this pattern)
        os.environ.setdefault("SSN_MASTER_KEY", "NEW_MASTER_KEY_HERE")

        # Clear persisted world + trace for deterministic test run
        _rm_if_exists(WORLD_PATH)
        _rm_if_exists(TRACE_PATH)

    def test_world_max_events_is_hard_bounded_and_guest_blocked(self) -> None:
        mk = os.environ.get("SSN_MASTER_KEY", "NEW_MASTER_KEY_HERE")

        rt = SSNRuntimeBuilder.build_default(default_role="GUEST")

        # Run 3 perception ticks (synthetic fallback is acceptable)
        for _ in range(3):
            resp = rt.shell.handle_event(
                {
                    "type": "sense_tick",
                    "role": "OWNER",
                    "text": "",
                    "context": {"events": [], "max_events": 25, "master_key": mk},
                    "meta": {"master_key": mk},
                }
            )
            self.assertTrue(getattr(resp, "ok", False), "sense_tick should succeed for OWNER")

        # Call world with max_events=2 and assert returned events are bounded
        resp2 = rt.shell.handle_event(
            {
                "type": "world",
                "role": "OWNER",
                "text": "",
                "context": {"max_entities": 5, "max_events": 2, "include_events": True, "master_key": mk},
                "meta": {"master_key": mk},
            }
        )
        self.assertTrue(getattr(resp2, "ok", False), "world should succeed for OWNER")

        data = getattr(resp2, "data", {}) or {}
        self.assertTrue(data.get("identity_verified") is True)
        self.assertTrue(data.get("allowed") is True)

        world = data.get("world", {}) or {}
        events = world.get("events", [])
        self.assertIsInstance(events, list)
        self.assertLessEqual(len(events), 2, "world.events must be hard bounded by max_events")

        # Confirm GUEST is blocked (no master key)
        resp3 = rt.shell.handle_event(
            {
                "type": "world",
                "role": "GUEST",
                "text": "",
                "context": {"max_entities": 5, "max_events": 2, "include_events": True},
                "meta": {},
            }
        )
        self.assertTrue(getattr(resp3, "ok", False), "world handler returns ok=True with blocked payload")

        data3 = getattr(resp3, "data", {}) or {}
        self.assertTrue(data3.get("identity_verified") is False)
        self.assertTrue(data3.get("allowed") is False)
        world3 = data3.get("world", {}) or {}
        self.assertTrue(world3.get("available") is False)
