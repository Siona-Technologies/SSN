from __future__ import annotations

import os
import unittest

from ssn.interfaces.contracts import InterfaceRequest
from ssn.interfaces.gateway import InterfaceGateway


IDENTITY_PATH = "ssn/data/identity_profile.json"


class _EchoOrchestrator:
    # compatible with handlers._call_compat (expects handle_request/run/process/handle/think)
    def handle_request(self, *, user_input=None, context=None, role=None, master_key=None, **kwargs):
        return {"seen_context": context or {}, "role": role, "text": user_input}


class TestPhase67IdentityContextInjection(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("SSN_MASTER_KEY", "NEW_MASTER_KEY_HERE")

    def test_identity_injected_for_verified_owner(self) -> None:
        mk = os.environ.get("SSN_MASTER_KEY", "NEW_MASTER_KEY_HERE")

        gw = InterfaceGateway(orchestrator=_EchoOrchestrator())
        req = InterfaceRequest(
            action="think",
            role="OWNER",
            user_input="hello",
            context={},
            meta={"master_key": mk},
        )
        resp = gw.handle(req)
        self.assertTrue(resp.ok)
        data = resp.data or {}
        ctx = (data.get("seen_context") or {})
        self.assertIn("identity", ctx)
        self.assertIn("identity_summary", ctx)

        ident = ctx.get("identity") or {}
        self.assertTrue(ident.get("available") in (True, False))
        # If profile exists (it does in your run), it should be available and correct:
        if ident.get("available") is True:
            self.assertEqual(ident.get("owner_name"), "Samson Sibona Njaji")
            self.assertEqual(ident.get("creator_name"), "Samson Sibona Njaji")

    def test_identity_not_injected_without_master_key(self) -> None:
        gw = InterfaceGateway(orchestrator=_EchoOrchestrator())
        req = InterfaceRequest(action="think", role="OWNER", user_input="hello", context={}, meta={})
        resp = gw.handle(req)
        self.assertTrue(resp.ok)
        ctx = (resp.data or {}).get("seen_context") or {}
        self.assertNotIn("identity", ctx)
        self.assertNotIn("identity_summary", ctx)
