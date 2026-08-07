"""EXP-3B-013 — State C evidence schema and documentation consistency (offline)."""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

os.environ.setdefault("SSN_OFFLINE", "1")

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs" / "evidence" / "EXP-3B-013_STATE_C.json"
DOC = ROOT / "docs" / "SIONA_STATE_C_REGISTRY_BOUND_RUNTIME_VERIFICATION.md"
STATUS = ROOT / "docs" / "PHASE_STATUS.md"
ADR = ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md"
REGISTRY = ROOT / "config" / "model_registry.json"


class TestExp3B013StateCEvidence(unittest.TestCase):
    def test_evidence_schema_and_decision(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(data["experiment_id"], "EXP-3B-013")
        self.assertEqual(data["decision"], "STATE_C_VERIFIED")
        self.assertTrue(data["decision_computed"])
        self.assertFalse(data["operator_override_allowed"])
        states = data["activation_states"]
        self.assertTrue(states["A_registry_record_available"])
        self.assertTrue(states["B_registry_entry_bound"])
        self.assertTrue(states["C_real_runtime_running_during_experiment"])
        self.assertTrue(states["D_real_inference_completed"])
        self.assertTrue(states["E_runtime_shut_down"])
        self.assertEqual(data["adr_0003_status"], "PROPOSED")
        self.assertEqual(data["phase_3b_status"], "IN_PROGRESS")
        self.assertEqual(data["phase_4_status"], "NOT_STARTED")
        self.assertEqual(
            data["remaining_blocker"],
            "ADR 0003 ACCEPTANCE + PHASE 3B COMPLETION DECISION",
        )
        bind = data["pre_inference_binding"]
        self.assertTrue(bind["model_registry_entry_bound"])
        self.assertEqual(bind["provider_id"], "siona-local-open-weight-v1")
        self.assertEqual(bind["model_id"], "Qwen3-1.7B-Q4_K_M")
        self.assertEqual(bind["artifact_verification_status"], "verified")
        self.assertEqual(bind["capability_verification_status"], "verified")
        for key in ("tools", "structured_json", "streaming", "multimodal", "siona_native"):
            self.assertFalse(bind[key])
        self.assertTrue(bind["chat"])
        self.assertEqual(bind["context_window"], 4096)
        summary = data["inference_summary"]
        self.assertGreaterEqual(summary["real_model_responses"], 1)
        self.assertEqual(summary["deterministic_fallback_during_live_probes"], 0)
        self.assertEqual(summary["tool_execution_count"], 0)
        self.assertFalse(data["registry_mutation"]["config_model_registry_json_mutated"])
        self.assertEqual(data["post_shutdown"]["port_8080_status"], "CLOSED")
        self.assertEqual(data["post_shutdown"]["llama_cpp_status"], "STOPPED")
        self.assertTrue(data["post_shutdown"]["deterministic_fallback_works"])
        self.assertFalse(data["post_shutdown"]["automatic_restart_observed"])
        # No absolute Windows user paths in committed evidence.
        blob = EVIDENCE.read_text(encoding="utf-8").lower()
        self.assertNotIn("c:\\users\\", blob)
        self.assertNotIn("/users/", blob)

    def test_documentation_consistency(self):
        doc = DOC.read_text(encoding="utf-8")
        status = STATUS.read_text(encoding="utf-8")
        adr = ADR.read_text(encoding="utf-8")
        self.assertIn("STATE C CONTROLLED REGISTRY-BOUND REAL-RUNTIME VERIFICATION PASSED", doc)
        self.assertIn("STATE C DOES NOT MEAN AUTOMATIC OR PERMANENT MODEL STARTUP", doc)
        self.assertIn("STATE_C_VERIFIED", doc)
        self.assertIn("EXP-3B-013", status)
        self.assertIn("State C controlled registry-bound real-runtime verification passed", status)
        self.assertIn("ADR 0003 acceptance and Phase 3B completion decision still pending", status)
        self.assertIn("Phase 4 remains **not started**", status)
        self.assertRegex(adr.replace("\r\n", "\n"), r"(?m)^## Status\n\nProposed\n")
        self.assertIn("ADR 0003 ACCEPTANCE + PHASE 3B COMPLETION DECISION", adr)
        self.assertIn("State C controlled registry-bound real-runtime verification", adr)
        # Registry file still present and conservative.
        reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
        entry = reg["models"][0]
        self.assertEqual(entry["provider_id"], "siona-local-open-weight-v1")
        self.assertEqual(entry["model_id"], "Qwen3-1.7B-Q4_K_M")
        caps = entry["capabilities"]
        self.assertTrue(caps["chat"])
        self.assertFalse(caps["tools"])
        self.assertFalse(caps["structured_json"])
        self.assertFalse(caps["streaming"])
        self.assertFalse(caps["multimodal"])
        self.assertEqual(caps["context_window"], 4096)
        self.assertFalse(entry["siona_native"])


if __name__ == "__main__":
    unittest.main()
