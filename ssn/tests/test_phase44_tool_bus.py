# ssn/tests/test_phase44_tool_bus.py

import unittest

from ssn.interfaces.contracts import InterfaceRequest
from ssn.interfaces.gateway import InterfaceGateway
from ssn.interfaces.tool_bus import ToolBus
from ssn.interfaces.tools_builtin import register_builtin_tools


class DummyPolicyAllow:
    def is_allowed(self, role, action, context=None, meta=None):
        return True


class DummySafetyAllow:
    def allow_internal_reflection(self):
        return True


class DummyMemoryHub:
    def get_recent_traces(self, limit=50):
        return [{"payload": {"type": "drift_report"}}, {"payload": {"type": "reflection_summary"}}]


class TestPhase44ToolBus(unittest.TestCase):

    def test_tools_list(self):
        bus = ToolBus()
        register_builtin_tools(bus)

        gw = InterfaceGateway(
            policy_engine=DummyPolicyAllow(),
            safety_monitor=DummySafetyAllow(),
            tool_bus=bus,
        )

        req = InterfaceRequest(action="tool", role="GUEST", meta={"tool_name": "tools.list"})
        resp = gw.handle(req)
        self.assertTrue(resp.ok)
        self.assertIn("tools", resp.data)

    def test_memory_types_owner_only(self):
        bus = ToolBus()
        register_builtin_tools(bus)

        gw = InterfaceGateway(
            policy_engine=DummyPolicyAllow(),
            safety_monitor=DummySafetyAllow(),
            tool_bus=bus,
            memory_hub=DummyMemoryHub(),
        )

        # GUEST blocked
        req_guest = InterfaceRequest(action="tool", role="GUEST", meta={"tool_name": "memory.types"})
        resp_guest = gw.handle(req_guest)
        self.assertFalse(resp_guest.ok)
        self.assertEqual(resp_guest.error.code, "TOOL_OWNER_ONLY")

        # OWNER allowed
        req_owner = InterfaceRequest(action="tool", role="OWNER", meta={"tool_name": "memory.types", "trace_limit": 10})
        resp_owner = gw.handle(req_owner)
        self.assertTrue(resp_owner.ok)
        self.assertIn("trace_type_histogram", resp_owner.data)


if __name__ == "__main__":
    unittest.main()
