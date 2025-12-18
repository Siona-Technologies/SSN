# ssn/tests/test_phase68_semantic_fact_tools.py

from __future__ import annotations

import os
import unittest

from ssn.runtime.runtime_builder import SSNRuntimeBuilder


class TestPhase68SemanticFactTools(unittest.TestCase):
    def setUp(self) -> None:
        self.mk = os.environ.get("SSN_MASTER_KEY", "").strip()
        if not self.mk:
            self.skipTest("SSN_MASTER_KEY not set")

        self.rt = SSNRuntimeBuilder.build_default(default_role="GUEST")

    def test_owner_can_set_get_list_delete_fact(self):
        # set
        resp1 = self.rt.shell.handle_event(
            {
                "type": "run_tool",
                "role": "OWNER",
                "context": {"tool_name": "memory.fact.set", "args": {"key": "creator", "value": "Samson Sibona Njaji"}},
                "meta": {"master_key": self.mk},
            }
        )
        self.assertTrue(resp1.ok, resp1.error)
        self.assertTrue(resp1.data.get("identity_verified"))
        self.assertEqual(resp1.data.get("tool"), "memory.fact.set")
        self.assertTrue(resp1.data.get("result", {}).get("ok"))

        # get
        resp2 = self.rt.shell.handle_event(
            {
                "type": "run_tool",
                "role": "OWNER",
                "context": {"tool_name": "memory.fact.get", "args": {"key": "creator"}},
                "meta": {"master_key": self.mk},
            }
        )
        self.assertTrue(resp2.ok, resp2.error)
        got = resp2.data.get("result", {})
        self.assertTrue(got.get("ok"))
        self.assertTrue(got.get("found"))
        self.assertEqual(got.get("value"), "Samson Sibona Njaji")

        # list
        resp3 = self.rt.shell.handle_event(
            {
                "type": "run_tool",
                "role": "OWNER",
                "context": {"tool_name": "memory.fact.list", "args": {"limit": 50}},
                "meta": {"master_key": self.mk},
            }
        )
        self.assertTrue(resp3.ok, resp3.error)
        lst = resp3.data.get("result", {})
        self.assertTrue(lst.get("ok"))
        facts = lst.get("facts", {})
        self.assertIsInstance(facts, dict)
        self.assertIn("creator", facts)

        # delete
        resp4 = self.rt.shell.handle_event(
            {
                "type": "run_tool",
                "role": "OWNER",
                "context": {"tool_name": "memory.fact.delete", "args": {"key": "creator"}},
                "meta": {"master_key": self.mk},
            }
        )
        self.assertTrue(resp4.ok, resp4.error)
        self.assertTrue(resp4.data.get("result", {}).get("ok"))

        # confirm gone (found may be False or value None depending on store)
        resp5 = self.rt.shell.handle_event(
            {
                "type": "run_tool",
                "role": "OWNER",
                "context": {"tool_name": "memory.fact.get", "args": {"key": "creator"}},
                "meta": {"master_key": self.mk},
            }
        )
        self.assertTrue(resp5.ok, resp5.error)
        got2 = resp5.data.get("result", {})
        self.assertTrue(got2.get("ok"))
        self.assertFalse(bool(got2.get("found")))

    def test_guest_cannot_run_tools(self):
        resp = self.rt.shell.handle_event(
            {
                "type": "run_tool",
                "role": "GUEST",
                "context": {"tool_name": "memory.fact.set", "args": {"key": "x", "value": "y"}},
                "meta": {},  # no master key
            }
        )
        # Your run_tool handler returns ok=True but allowed False for unverified
        self.assertTrue(resp.ok)
        self.assertFalse(resp.data.get("identity_verified"))
        self.assertFalse(resp.data.get("allowed"))


if __name__ == "__main__":
    unittest.main()
