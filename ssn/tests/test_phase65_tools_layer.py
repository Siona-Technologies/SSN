# ssn/tests/test_phase65_tools_layer.py

from __future__ import annotations

import os
import unittest

from ssn.runtime.runtime_builder import SSNRuntimeBuilder


class TestPhase65ToolsLayer(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("SSN_MASTER_KEY", "NEW_MASTER_KEY_HERE")

    def test_guest_blocked_owner_allowed(self) -> None:
        mk = os.environ.get("SSN_MASTER_KEY", "NEW_MASTER_KEY_HERE")
        rt = SSNRuntimeBuilder.build_default(default_role="GUEST")

        # Guest blocked (no key)
        r1 = rt.shell.handle_event(
            {"type": "run_tool", "role": "GUEST", "text": "", "context": {"tool_name": "tools.list", "args": {}}, "meta": {}}
        )
        self.assertTrue(getattr(r1, "ok", False))
        d1 = getattr(r1, "data", {}) or {}
        self.assertFalse(d1.get("allowed", True))

        # Owner allowed
        r2 = rt.shell.handle_event(
            {
                "type": "run_tool",
                "role": "OWNER",
                "text": "",
                "context": {"tool_name": "tools.list", "args": {}, "master_key": mk},
                "meta": {"master_key": mk},
            }
        )
        self.assertTrue(getattr(r2, "ok", False))
        d2 = getattr(r2, "data", {}) or {}
        self.assertTrue(d2.get("allowed") is True)
        res = d2.get("result", {}) or {}
        self.assertIn("tools", res)

    def test_owner_can_sense_tick_and_read_world(self) -> None:
        mk = os.environ.get("SSN_MASTER_KEY", "NEW_MASTER_KEY_HERE")
        rt = SSNRuntimeBuilder.build_default(default_role="GUEST")

        # tick
        r1 = rt.shell.handle_event(
            {
                "type": "run_tool",
                "role": "OWNER",
                "text": "",
                "context": {"tool_name": "world.sense_tick", "args": {"events": [], "max_events": 25}, "master_key": mk},
                "meta": {"master_key": mk},
            }
        )
        self.assertTrue(getattr(r1, "ok", False))

        # read
        r2 = rt.shell.handle_event(
            {
                "type": "run_tool",
                "role": "OWNER",
                "text": "",
                "context": {"tool_name": "world.read", "args": {"max_entities": 5, "max_events": 2, "include_events": True}, "master_key": mk},
                "meta": {"master_key": mk},
            }
        )
        self.assertTrue(getattr(r2, "ok", False))
        d2 = getattr(r2, "data", {}) or {}
        world = (d2.get("result") or {}).get("world", {}) or {}
        evs = world.get("events", [])
        self.assertIsInstance(evs, list)
        self.assertLessEqual(len(evs), 2)
