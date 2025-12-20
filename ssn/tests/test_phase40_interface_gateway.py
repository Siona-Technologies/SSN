# ssn/tests/test_phase40_interface_gateway.py

import unittest

from ssn.interfaces.contracts import InterfaceRequest
from ssn.interfaces.gateway import InterfaceGateway


class DummyRouter:
    def route(self, role, user_input, context=None):
        return {"routed": True, "role": role, "user_input": user_input, "context": context or {}}


class DummyPolicyAllow:
    def is_allowed(self, role, action, context=None, meta=None):
        return True


class DummyPolicyDeny:
    def is_allowed(self, role, action, context=None, meta=None):
        return False


class DummySafetyAllow:
    def allow_internal_reflection(self):
        return True


class DummySafetyDeny:
    def allow_internal_reflection(self):
        return False


class DummyMemoryHub:
    def __init__(self):
        self.traces = [{"payload": {"type": "reflection_summary"}}, {"payload": {"type": "drift_report"}}]
        self.episodic = [{"event": "a"}]

    def get_recent_traces(self, limit=30):
        return self.traces[:limit]

    def get_recent_episodic(self, limit=10):
        return self.episodic[:limit]


class TestPhase40InterfaceGateway(unittest.TestCase):

    def test_blocks_unknown_action(self):
        gw = InterfaceGateway(brain_router=DummyRouter(), policy_engine=DummyPolicyAllow(), safety_monitor=DummySafetyAllow())
        resp = gw.handle(InterfaceRequest(action="external_action", role="OWNER", user_input="x"))
        self.assertFalse(resp.ok)
        self.assertEqual(resp.error.code, "ACTION_NOT_ALLOWED")

    def test_blocks_by_policy(self):
        # NOTE: current InterfaceGateway does not apply policy gating to "think"
        # so we test policy blocking on a policy-gated action.
        gw = InterfaceGateway(
            brain_router=DummyRouter(),
            policy_engine=DummyPolicyDeny(),
            safety_monitor=DummySafetyAllow(),
            memory_hub=DummyMemoryHub(),
        )
        resp = gw.handle(InterfaceRequest(action="summarize_memory", role="OWNER", meta={"trace_limit": 10, "episodic_limit": 5}))
        self.assertFalse(resp.ok)
        self.assertEqual(resp.error.code, "BLOCKED_BY_POLICY")

    def test_blocks_by_safety(self):
        gw = InterfaceGateway(brain_router=DummyRouter(), policy_engine=DummyPolicyAllow(), safety_monitor=DummySafetyDeny())
        resp = gw.handle(InterfaceRequest(action="think", role="OWNER", user_input="x"))
        self.assertFalse(resp.ok)
        self.assertEqual(resp.error.code, "BLOCKED_BY_SAFETY")

    def test_think_routes_via_brain_router(self):
        gw = InterfaceGateway(brain_router=DummyRouter(), policy_engine=DummyPolicyAllow(), safety_monitor=DummySafetyAllow())
        req = InterfaceRequest(action="think", role="OWNER", user_input="hello", context={"k": 1})
        resp = gw.handle(req)
        self.assertTrue(resp.ok)
        self.assertTrue(resp.data.get("routed"))

    def test_summarize_memory(self):
        gw = InterfaceGateway(
            brain_router=DummyRouter(),
            policy_engine=DummyPolicyAllow(),
            safety_monitor=DummySafetyAllow(),
            memory_hub=DummyMemoryHub(),
        )
        req = InterfaceRequest(action="summarize_memory", role="OWNER", meta={"trace_limit": 10, "episodic_limit": 5})
        resp = gw.handle(req)
        self.assertTrue(resp.ok)
        self.assertIn("trace_type_histogram", resp.data)
        self.assertEqual(resp.data["episodic_count"], 1)


if __name__ == "__main__":
    unittest.main()
