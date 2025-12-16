from __future__ import annotations

import os
import unittest

from ssn.runtime.runtime_builder import SSNRuntimeBuilder

IDENTITY_PATH = "ssn/data/identity_profile.json"


class TestPhase66IdentityEnrollment(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("SSN_MASTER_KEY", "NEW_MASTER_KEY_HERE")
        # Clean identity profile
        try:
            if os.path.exists(IDENTITY_PATH):
                os.remove(IDENTITY_PATH)
        except Exception:
            pass

    def test_owner_can_enroll_and_view_identity(self) -> None:
        mk = os.environ.get("SSN_MASTER_KEY", "NEW_MASTER_KEY_HERE")
        rt = SSNRuntimeBuilder.build_default(default_role="GUEST")

        # View before enrollment (should be unavailable, but call must succeed)
        r0 = rt.shell.handle_event(
            {
                "type": "run_tool",
                "role": "OWNER",
                "text": "",
                "context": {"tool_name": "identity.view", "args": {}, "master_key": mk},
                "meta": {"master_key": mk},
            }
        )
        self.assertTrue(getattr(r0, "ok", False))
        d0 = getattr(r0, "data", {}) or {}
        self.assertTrue(d0.get("allowed") is True)
        res0 = d0.get("result") or {}
        self.assertIn("available", res0)
        self.assertFalse(bool(res0.get("available", True)))

        # Enroll (force overwrite)
        r1 = rt.shell.handle_event(
            {
                "type": "run_tool",
                "role": "OWNER",
                "text": "",
                "context": {"tool_name": "identity.enroll", "args": {"force": True}, "master_key": mk},
                "meta": {"master_key": mk},
            }
        )
        self.assertTrue(getattr(r1, "ok", False))
        d1 = getattr(r1, "data", {}) or {}
        self.assertTrue(d1.get("allowed") is True)
        res1 = d1.get("result") or {}
        self.assertTrue(res1.get("ok") is True)
        prof = res1.get("profile") or {}
        self.assertEqual(prof.get("owner_name"), "Samson Sibona Njaji")
        self.assertEqual(prof.get("creator_name"), "Samson Sibona Njaji")
        self.assertTrue(isinstance(prof.get("signature"), str) and len(prof.get("signature")) > 0)

        # View after enroll (should be available and signature_valid True)
        r2 = rt.shell.handle_event(
            {
                "type": "run_tool",
                "role": "OWNER",
                "text": "",
                "context": {"tool_name": "identity.view", "args": {}, "master_key": mk},
                "meta": {"master_key": mk},
            }
        )
        self.assertTrue(getattr(r2, "ok", False))
        d2 = getattr(r2, "data", {}) or {}
        res2 = d2.get("result") or {}
        self.assertTrue(res2.get("available") is True)
        self.assertTrue(res2.get("signature_valid") is True)

    def test_guest_blocked(self) -> None:
        rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
        r = rt.shell.handle_event(
            {"type": "run_tool", "role": "GUEST", "text": "", "context": {"tool_name": "identity.view", "args": {}}, "meta": {}}
        )
        self.assertTrue(getattr(r, "ok", False))
        d = getattr(r, "data", {}) or {}
        self.assertFalse(d.get("allowed", True))
