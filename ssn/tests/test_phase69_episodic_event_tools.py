from __future__ import annotations

import os
import unittest

from ssn.interfaces.contracts import InterfaceRequest
from ssn.interfaces.handlers_tools import handle_run_tool
from ssn.runtime.runtime_builder import SSNRuntimeBuilder


class TestPhase69EpisodicEventTools(unittest.TestCase):
    def setUp(self):
        self.rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
        self.deps = self.rt.gateway.deps
        self.mk = os.environ.get("SSN_MASTER_KEY", "")

    def _run_tool(self, name: str, args: dict):
        req = InterfaceRequest(
            action="run_tool",
            role="OWNER",
            user_input="",
            context={"tool_name": name, "args": args},
            meta={"master_key": self.mk} if self.mk else {},
        )
        return handle_run_tool(req, self.deps)

    def test_owner_can_add_recent_search_events(self):
        # add
        r1 = self._run_tool(
            "memory.event.add",
            {"event_type": "experiment_note", "actor": "Samson", "details": {"topic": "phase69", "ok": True}},
        )
        self.assertTrue(r1.ok, getattr(r1, "data", None))

        # recent
        r2 = self._run_tool("memory.event.recent", {"limit": 10})
        self.assertTrue(r2.ok, getattr(r2, "data", None))
        data2 = r2.data.get("result") if isinstance(r2.data, dict) else None
        # handler_tools wraps result under data["result"]
        self.assertIsInstance(data2, dict)
        self.assertIn("events", data2)
        self.assertIsInstance(data2["events"], list)

        # search
        r3 = self._run_tool("memory.event.search", {"query": "phase69", "limit": 10})
        self.assertTrue(r3.ok, getattr(r3, "data", None))
        data3 = r3.data.get("result") if isinstance(r3.data, dict) else None
        self.assertIsInstance(data3, dict)
        self.assertIn("events", data3)
        self.assertIsInstance(data3["events"], list)


if __name__ == "__main__":
    unittest.main()
