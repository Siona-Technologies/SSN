# ssn/tests/test_phase42_runtime_builder.py

import unittest

from ssn.runtime.runtime_builder import SSNRuntimeBuilder


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
    def get_recent_traces(self, limit=30):
        return [{"payload": {"type": "drift_report"}}]

    def get_recent_episodic(self, limit=10):
        return [{"event": "x"}]


class TestPhase42RuntimeBuilder(unittest.TestCase):

    def test_builder_constructs_gateway_and_shell(self):
        builder = SSNRuntimeBuilder(
            brain_router=DummyRouter(),
            policy_engine=DummyPolicyAllow(),
            safety_monitor=DummySafetyAllow(),
            memory_hub=DummyMemoryHub(),
            default_role="GUEST",
        )
        rt = builder.build()
        self.assertIsNotNone(rt.gateway)
        self.assertIsNotNone(rt.shell)

        # Basic shell event smoke
        resp = rt.shell.handle_event({"type": "chat", "role": "OWNER", "text": "hello", "context": {"k": 1}})
        self.assertTrue(resp.ok)
        self.assertTrue(resp.data.get("routed"))

    def test_build_default_does_not_crash(self):
        # Best-effort: may not wire everything in your repo, but must not crash
        rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
        self.assertIsNotNone(rt.gateway)
        self.assertIsNotNone(rt.shell)


if __name__ == "__main__":
    unittest.main()
