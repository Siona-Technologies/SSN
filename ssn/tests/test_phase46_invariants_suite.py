# ssn/tests/test_phase46_invariants_suite.py

import unittest

from ssn.interfaces.contracts import InterfaceRequest
from ssn.interfaces.gateway import InterfaceGateway
from ssn.interfaces.tool_bus import ToolBus
from ssn.interfaces.tools_builtin import register_builtin_tools


class PolicyDenyAll:
    def is_allowed(self, role, action, context=None, meta=None):
        return False


class PolicyAllowAll:
    def is_allowed(self, role, action, context=None, meta=None):
        return True


class SafetyAllow:
    def allow_internal_reflection(self):
        return True


class DummyMemoryHub:
    def __init__(self):
        self.traces = []

    def add_trace(self, payload=None, **kwargs):
        if payload is None:
            payload = kwargs.get("payload", {})
        self.traces.append(payload)

    def get_recent_traces(self, limit=50):
        return [{"payload": p} for p in self.traces[-limit:]]


class DummyOrchestratorIdentityAuthority:
    """
    Models the invariant: requested role is not authoritative.
    Orchestrator decides role based on master_key presence.
    """
    def __init__(self):
        self.calls = 0
        self.last = {}

    def run(self, master_key, user_input, context=None):
        self.calls += 1
        self.last = {"master_key": master_key, "user_input": user_input, "context": context or {}}
        role = "OWNER" if (isinstance(master_key, str) and master_key.strip()) else "GUEST"
        return {"identity_verified": role == "OWNER", "role": role, "allowed": True, "final_result": "EXECUTED"}


class TestPhase46InvariantsSuite(unittest.TestCase):

    def test_policy_blocks_before_core_is_called(self):
        orch = DummyOrchestratorIdentityAuthority()
        gw = InterfaceGateway(
            orchestrator=orch,
            policy_engine=PolicyDenyAll(),
            safety_monitor=SafetyAllow(),
        )
        req = InterfaceRequest(action="think", role="OWNER", user_input="hello", context={}, meta={})
        resp = gw.handle(req)

        self.assertFalse(resp.ok)
        self.assertEqual(resp.error.code, "BLOCKED_BY_POLICY")
        self.assertEqual(orch.calls, 0, "Orchestrator must not be called when policy denies.")

    def test_requested_owner_role_is_not_authoritative(self):
        orch = DummyOrchestratorIdentityAuthority()
        gw = InterfaceGateway(
            orchestrator=orch,
            policy_engine=PolicyAllowAll(),
            safety_monitor=SafetyAllow(),
        )

        # Request OWNER but provide no master key → must still become GUEST (as decided by orchestrator)
        req = InterfaceRequest(action="think", role="OWNER", user_input="hello", context={}, meta={})
        resp = gw.handle(req)

        self.assertTrue(resp.ok)
        self.assertEqual(resp.data.get("role"), "GUEST")

    def test_master_key_never_forwarded_inside_context(self):
        orch = DummyOrchestratorIdentityAuthority()
        gw = InterfaceGateway(
            orchestrator=orch,
            policy_engine=PolicyAllowAll(),
            safety_monitor=SafetyAllow(),
        )

        # Even if context contains master_key, it must be redacted before reaching core
        req = InterfaceRequest(
            action="think",
            role="OWNER",
            user_input="x",
            context={"master_key": "LEAK", "auth": {"master_key": "LEAK2"}, "topic": "t"},
            meta={"master_key": "REALKEY"},
        )
        resp = gw.handle(req)

        self.assertTrue(resp.ok)
        self.assertEqual(orch.last["master_key"], "REALKEY")
        self.assertNotIn("master_key", orch.last["context"])
        self.assertIn("auth", orch.last["context"])
        self.assertNotIn("master_key", orch.last["context"]["auth"])

    def test_tool_owner_only_enforcement(self):
        bus = ToolBus()
        register_builtin_tools(bus)

        gw = InterfaceGateway(
            policy_engine=PolicyAllowAll(),
            safety_monitor=SafetyAllow(),
            tool_bus=bus,
            memory_hub=DummyMemoryHub(),
        )

        # memory.types is OWNER-only
        req_guest = InterfaceRequest(action="tool", role="GUEST", meta={"tool_name": "memory.types", "trace_limit": 10})
        resp_guest = gw.handle(req_guest)
        self.assertFalse(resp_guest.ok)
        self.assertEqual(resp_guest.error.code, "TOOL_OWNER_ONLY")

    def test_doc_ingest_trace_is_bounded_no_raw_doc(self):
        bus = ToolBus()
        register_builtin_tools(bus)
        mh = DummyMemoryHub()

        gw = InterfaceGateway(
            policy_engine=PolicyAllowAll(),
            safety_monitor=SafetyAllow(),
            tool_bus=bus,
            memory_hub=mh,
        )

        req = InterfaceRequest(
            action="tool",
            role="OWNER",
            meta={
                "tool_name": "doc.ingest_readonly",
                "format": "text",
                "title": "Bound Test",
                "document": "Line1\nLine2 must remain bounded\nLine3",
                "max_citations": 5,
            },
        )
        resp = gw.handle(req)
        self.assertTrue(resp.ok)
        self.assertTrue(resp.data.get("trace_written"))

        # Confirm raw document never stored in trace payload
        written = mh.traces[-1]
        self.assertEqual(written.get("type"), "doc_ingest")
        self.assertNotIn("document", written)
        self.assertIn("content_hash", written)
        self.assertIn("citations", written)


if __name__ == "__main__":
    unittest.main()
