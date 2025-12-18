from __future__ import annotations

import os
import unittest

from ssn.interfaces.contracts import InterfaceRequest
from ssn.interfaces.handlers_tools import handle_run_tool
from ssn.runtime.runtime_builder import SSNRuntimeBuilder


class TestPhase70TraceTools(unittest.TestCase):
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

    def test_trace_tools_work(self):
        # Ensure some traces exist (your world.sense_tick writes trace)
        r0 = self._run_tool("world.sense_tick", {"events": [], "max_events": 25})
        self.assertTrue(r0.ok, r0.data)

        r1 = self._run_tool("memory.trace.recent", {"limit": 50})
        self.assertTrue(r1.ok, r1.data)
        self.assertIsInstance(r1.data.get("result"), dict)

        recent = r1.data["result"]
        self.assertTrue(recent.get("ok"))
        self.assertIn("traces", recent)
        self.assertIsInstance(recent["traces"], list)
        self.assertIn("trace_type_histogram", recent)

        r2 = self._run_tool("memory.trace.types", {"limit": 200})
        self.assertTrue(r2.ok, r2.data)
        types = r2.data["result"]
        self.assertTrue(types.get("ok"))
        self.assertIsInstance(types.get("trace_type_histogram"), dict)

        # Search should return a dict, may be 0..N hits depending on trace payload text
        r3 = self._run_tool("memory.trace.search", {"query": "world", "limit": 25, "scan_limit": 200})
        self.assertTrue(r3.ok, r3.data)
        srch = r3.data["result"]
        self.assertTrue(srch.get("ok"))
        self.assertIsInstance(srch.get("traces"), list)


if __name__ == "__main__":
    unittest.main()
