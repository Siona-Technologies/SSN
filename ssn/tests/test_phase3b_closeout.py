"""Phase 3B acceptance / ADR 0003 closeout consistency (offline only)."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACCEPTANCE = ROOT / "docs" / "PHASE_3B_ACCEPTANCE.md"
ACCEPTANCE_EVIDENCE = ROOT / "docs" / "evidence" / "PHASE_3B_ACCEPTANCE.json"
STATE_C = ROOT / "docs" / "evidence" / "EXP-3B-013_STATE_C.json"
REGISTRY = ROOT / "config" / "model_registry.json"
ADR = ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md"
STATUS = ROOT / "docs" / "PHASE_STATUS.md"
SPEC = ROOT / "docs" / "PHASE_3_ENGINEERING_SPEC.md"
RUNBOOK = ROOT / "docs" / "PHASE_3B_INSTALLATION_RUNBOOK.md"


class TestPhase3BCloseout(unittest.TestCase):
    def test_acceptance_record_and_governance_state(self):
        self.assertTrue(ACCEPTANCE.is_file())
        self.assertTrue(ACCEPTANCE_EVIDENCE.is_file())

        acceptance = ACCEPTANCE.read_text(encoding="utf-8")
        adr = ADR.read_text(encoding="utf-8")
        status = STATUS.read_text(encoding="utf-8")
        spec = SPEC.read_text(encoding="utf-8")

        self.assertIn("**Status:** Accepted", acceptance)
        self.assertIn("**Phase 3B is COMPLETE.**", acceptance)
        self.assertIn("Phase 3 is\nCOMPLETE", acceptance)
        self.assertIn("Phase 4 remains **NOT STARTED**", acceptance)

        status_block = adr.replace("\r\n", "\n").split("## Status", 1)[1].split(
            "## Context", 1
        )[0]
        self.assertIn("Accepted (Phase 3B)", status_block)
        self.assertNotRegex(status_block, r"(?m)^\s*Proposed\s*$")
        self.assertIn("ADR 0003 is **Accepted (Phase 3B)**", status)
        self.assertIn("Phase 3B is **complete**", status)
        self.assertIn("Phase 3 is\n**complete for its defined local-model/evaluation scope**", status)
        self.assertIn("Phase 4 remains **not started**", status)
        self.assertIn("Phase 3 **completed**", spec)
        self.assertIn("Phase 4 remains **Not Started**", spec)

    def test_acceptance_evidence_matches_state_c_and_registry(self):
        closeout = json.loads(ACCEPTANCE_EVIDENCE.read_text(encoding="utf-8"))
        state_c = json.loads(STATE_C.read_text(encoding="utf-8"))
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

        self.assertEqual(closeout["decision"], "PHASE_3B_ACCEPTED")
        self.assertEqual(closeout["adr_0003_status"], "ACCEPTED")
        self.assertEqual(closeout["phase_3_status"], "COMPLETE")
        self.assertEqual(closeout["phase_3b_status"], "COMPLETE")
        self.assertEqual(closeout["phase_4_status"], "NOT_STARTED")
        self.assertEqual(closeout["required_evidence"]["EXP-3B-013"], "STATE_C_VERIFIED")
        self.assertEqual(state_c["decision"], "STATE_C_VERIFIED")
        self.assertTrue(state_c["decision_computed"])
        self.assertFalse(state_c["operator_override_allowed"])

        entry = next(
            m
            for m in registry["models"]
            if m["provider_id"] == closeout["accepted_baseline"]["provider_id"]
            and m["model_id"] == closeout["accepted_baseline"]["model_id"]
        )
        self.assertEqual(
            closeout["accepted_baseline"]["artifact_checksum"], entry["artifact_checksum"]
        )
        self.assertEqual(closeout["accepted_baseline"]["capabilities"], entry["capabilities"])
        self.assertFalse(closeout["accepted_baseline"]["siona_native"])
        self.assertFalse(entry["siona_native"])

        caps = closeout["accepted_baseline"]["capabilities"]
        self.assertTrue(caps["chat"])
        self.assertFalse(caps["tools"])
        self.assertFalse(caps["structured_json"])
        self.assertFalse(caps["streaming"])
        self.assertFalse(caps["multimodal"])
        self.assertEqual(caps["context_window"], 4096)

    def test_acceptance_does_not_promote_optional_capabilities(self):
        closeout = json.loads(ACCEPTANCE_EVIDENCE.read_text(encoding="utf-8"))
        limits = closeout["capability_limits"]
        non_claims = closeout["non_claims"]
        activity = closeout["closeout_runtime_activity"]

        self.assertEqual(limits["native_json"], "NOT_VERIFIED")
        self.assertEqual(
            limits["gate_e_retained_json_schema"],
            "6/6_EXACT_SCHEMA_RECORDED_SEPARATELY",
        )
        self.assertEqual(limits["streaming"], "UNSUPPORTED_ON_PINNED_BASELINE")
        self.assertEqual(limits["tools"], "DISABLED")
        self.assertEqual(limits["multimodal"], "UNVERIFIED_DISABLED")

        for key, value in non_claims.items():
            self.assertFalse(value, f"unexpected closeout claim: {key}")
        for key, value in activity.items():
            self.assertEqual(value, 0, f"closeout must be model-free/offline: {key}")

        steady = closeout["steady_state"]
        self.assertTrue(steady["runtime_expected_stopped"])
        self.assertTrue(steady["port_8080_expected_closed"])
        self.assertFalse(steady["automatic_startup_authorized"])
        self.assertTrue(steady["hosted_ci_model_free"])

    def test_no_current_closeout_pending_wording(self):
        adr = ADR.read_text(encoding="utf-8")
        status = STATUS.read_text(encoding="utf-8")
        spec = SPEC.read_text(encoding="utf-8")
        runbook = RUNBOOK.read_text(encoding="utf-8")
        current = "\n".join([adr, status, spec, runbook]).lower()

        for phrase in (
            "adr acceptance still pending",
            "adr 0003 acceptance and phase 3b completion decision still pending",
            "phase 3b remains in progress",
            "phase 3b is not completed",
            "state c real-runtime verification pending",
        ):
            self.assertNotIn(phrase, current)

        self.assertIn("accepted (phase 3b)", adr.lower())
        self.assertIn("phase 3b is **complete**", status.lower())
        self.assertIn("phase 4 remains **not started**", status.lower())
        self.assertIn("post-closeout authorization boundary", runbook.lower())


if __name__ == "__main__":
    unittest.main()
