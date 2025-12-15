# ssn/tests/test_phase43_owner_handoff_and_redaction.py

import unittest

from ssn.interfaces.contracts import InterfaceRequest
from ssn.interfaces.gateway import InterfaceGateway


class DummyPolicyAllow:
    def is_allowed(self, role, action, context=None, meta=None):
        return True


class DummySafetyAllow:
    def allow_internal_reflection(self):
        return True


class DummyOrchestrator:
    """
    Matches your real signature:
      run(master_key, user_input, context=None)
    """
    def __init__(self):
        self.seen = {}

    def run(self, master_key, user_input, context=None):
        self.seen = {
            "master_key": master_key,
            "user_input": user_input,
            "context": context if isinstance(context, dict) else {},
        }
        return {"ok": True, "seen": self.seen}


class TestPhase43OwnerHandoffAndRedaction(unittest.TestCase):

    def test_master_key_passed_as_argument_and_context_sanitized(self):
        orch = DummyOrchestrator()
        gw = InterfaceGateway(
            orchestrator=orch,
            policy_engine=DummyPolicyAllow(),
            safety_monitor=DummySafetyAllow(),
        )

        req = InterfaceRequest(
            action="think",
            role="OWNER",
            user_input="hello",
            context={"topic": "memory", "master_key": "LEAK", "auth": {"master_key": "LEAK2"}},
            meta={"master_key": "REALKEY"},
        )

        resp = gw.handle(req)
        self.assertTrue(resp.ok)

        seen = resp.data["seen"]
        self.assertEqual(seen["master_key"], "REALKEY")
        self.assertEqual(seen["user_input"], "hello")

        # Redaction guarantees: no master_key forwarded in context
        self.assertNotIn("master_key", seen["context"])
        self.assertIn("auth", seen["context"])
        self.assertNotIn("master_key", seen["context"]["auth"])

    def test_no_master_key_results_in_none_passed(self):
        orch = DummyOrchestrator()
        gw = InterfaceGateway(
            orchestrator=orch,
            policy_engine=DummyPolicyAllow(),
            safety_monitor=DummySafetyAllow(),
        )

        req = InterfaceRequest(action="think", role="OWNER", user_input="hello", context={"topic": "x"}, meta={})
        resp = gw.handle(req)
        self.assertTrue(resp.ok)
        self.assertIsNone(resp.data["seen"]["master_key"])


if __name__ == "__main__":
    unittest.main()
