# ssn/tests/test_phase41_agent_shell.py

import unittest

from ssn.interfaces.contracts import InterfaceRequest
from ssn.interfaces.gateway import InterfaceGateway
from ssn.interfaces.agent_shell import AgentShell


class DummyRouter:
    def route(self, role, user_input, context=None):
        return {"routed": True, "role": role, "user_input": user_input, "context": context or {}}


class DummyPolicyAllow:
    def is_allowed(self, role, action, context=None, meta=None):
        return True


class DummySafetyAllow:
    def allow_internal_reflection(self):
        return True


class DummyMemoryHub:
    def __init__(self):
        self.traces = [{"payload": {"type": "reflection_summary"}}, {"payload": {"type": "drift_report"}}]
        self.episodic = [{"event": "a"}]

    def get_recent_traces(self, limit=30):
        return self.traces[:limit]

    def get_recent_episodic(self, limit=10):
        return self.episodic[:limit]


class TestPhase41AgentShell(unittest.TestCase):

    def test_shell_chat_maps_to_think(self):
        gw = InterfaceGateway(
            brain_router=DummyRouter(),
            policy_engine=DummyPolicyAllow(),
            safety_monitor=DummySafetyAllow(),
            memory_hub=DummyMemoryHub(),
        )
        shell = AgentShell(gateway=gw, default_role="GUEST")

        resp = shell.handle_event({"type": "chat", "role": "OWNER", "text": "hello", "context": {"x": 1}})
        self.assertTrue(resp.ok)
        self.assertTrue(resp.data.get("routed"))
        self.assertEqual(resp.data.get("role"), "OWNER")

    def test_shell_memory_maps_to_summarize_memory(self):
        gw = InterfaceGateway(
            brain_router=DummyRouter(),
            policy_engine=DummyPolicyAllow(),
            safety_monitor=DummySafetyAllow(),
            memory_hub=DummyMemoryHub(),
        )
        shell = AgentShell(gateway=gw)

        resp = shell.handle_event({"type": "memory", "role": "OWNER", "meta": {"trace_limit": 10, "episodic_limit": 5}})
        self.assertTrue(resp.ok)
        self.assertIn("trace_type_histogram", resp.data)

    def test_shell_blocks_unknown_event(self):
        gw = InterfaceGateway(
            brain_router=DummyRouter(),
            policy_engine=DummyPolicyAllow(),
            safety_monitor=DummySafetyAllow(),
        )
        shell = AgentShell(gateway=gw)

        resp = shell.handle_event({"type": "browser", "role": "OWNER"})
        self.assertFalse(resp.ok)
        self.assertEqual(resp.error.code, "UNKNOWN_EVENT_TYPE")


if __name__ == "__main__":
    unittest.main()
