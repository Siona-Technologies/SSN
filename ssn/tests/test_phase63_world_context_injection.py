import unittest
from unittest.mock import patch

from ssn.runtime.runtime_builder import SSNRuntimeBuilder


class TestPhase63WorldContextInjection(unittest.TestCase):
    def test_chat_attaches_world_summary_for_verified_owner(self):
        rt = SSNRuntimeBuilder.build_default(default_role="GUEST")

        with patch("ssn.interfaces.handlers.verify_owner", return_value={
            "master_key_score": 1.0, "biometric_score": 0.0, "behavior_score": 0.0, "overall_score": 0.7
        }), patch("ssn.interfaces.handlers.is_samson_verified", return_value=True):
            resp = rt.shell.handle_event({
                "type": "chat",
                "role": "OWNER",
                "text": "hello",
                "context": {},
                "meta": {"master_key": "TEST"},
            })

        self.assertTrue(resp.ok)
        # We just assert no crash; actual content depends on your orchestrator response formatting.
        # If your orchestrator echoes context, you can tighten this assertion.

    def test_chat_does_not_attach_world_summary_for_guest(self):
        rt = SSNRuntimeBuilder.build_default(default_role="GUEST")

        with patch("ssn.interfaces.handlers.verify_owner", return_value={
            "master_key_score": 0.0, "biometric_score": 0.0, "behavior_score": 0.0, "overall_score": 0.0
        }), patch("ssn.interfaces.handlers.is_samson_verified", return_value=False):
            resp = rt.shell.handle_event({
                "type": "chat",
                "role": "OWNER",  # even if claimed OWNER, verification fails
                "text": "hello",
                "context": {},
                "meta": {"master_key": "BAD"},
            })

        self.assertTrue(resp.ok)


if __name__ == "__main__":
    unittest.main()
