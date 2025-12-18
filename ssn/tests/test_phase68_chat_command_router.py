from __future__ import annotations

import os
import unittest

from ssn.runtime.runtime_builder import SSNRuntimeBuilder


class TestPhase68ChatCommandRouter(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["SSN_MASTER_KEY"] = os.environ.get("SSN_MASTER_KEY", "NEW_MASTER_KEY_HERE")

    def test_owner_chat_runs_tools(self) -> None:
        rt = SSNRuntimeBuilder.build_default(default_role="GUEST")

        # 1) Run a sense tick via chat command
        resp1 = rt.shell.handle_event(
            {"type": "chat", "role": "OWNER", "text": "sense tick", "context": {}, "meta": {"master_key": os.environ["SSN_MASTER_KEY"]}}
        )
        self.assertTrue(resp1.ok)
        self.assertTrue((resp1.data or {}).get("tool_command", False))

        # 2) Read world via chat command
        resp2 = rt.shell.handle_event(
            {"type": "chat", "role": "OWNER", "text": "show world", "context": {"max_entities": 5, "max_events": 2}, "meta": {"master_key": os.environ["SSN_MASTER_KEY"]}}
        )
        self.assertTrue(resp2.ok)
        data2 = resp2.data or {}
        self.assertTrue(data2.get("tool_command", False))

        # Ensure world.read was executed
        tools = [r.get("tool") for r in (data2.get("results") or []) if isinstance(r, dict)]
        self.assertIn("world.read", tools)

    def test_guest_chat_does_not_run_tools(self) -> None:
        rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
        resp = rt.shell.handle_event({"type": "chat", "role": "GUEST", "text": "show world", "context": {}, "meta": {}})
        self.assertTrue(resp.ok)
        self.assertFalse((resp.data or {}).get("tool_command", False))
