"""Phase 4 closeout acceptance regression (offline/model-free)."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACCEPTANCE_DOC = ROOT / "docs" / "PHASE_4_ACCEPTANCE.md"
ACCEPTANCE_JSON = ROOT / "docs" / "evidence" / "PHASE_4_ACCEPTANCE.json"
ADR4 = ROOT / "docs" / "adr" / "0004-learned-neuromorphic-backend-strategy.md"
STATUS = ROOT / "docs" / "PHASE_STATUS.md"
ROADMAP = ROOT / "docs" / "SIONA_PHASE_ROADMAP.md"
SPEC = ROOT / "docs" / "PHASE_4_ENGINEERING_SPEC.md"
ARTIFACT = ROOT / "artifacts" / "neuromorphic" / "phase4b-lif-final-membrane-v1.json"
EXP3 = ROOT / "docs" / "evidence" / "EXP-4-003_FIRST_CPU_SNN_TRAINING.json"
EXP4 = ROOT / "docs" / "evidence" / "EXP-4-004_LEARNED_SNN_PROVIDER_PARITY.json"
EXP5 = ROOT / "docs" / "evidence" / "EXP-4-005_PHASE_4_BREADTH_SAFETY.json"
REGISTRY = ROOT / "config" / "model_registry.json"
REQUIREMENTS = ROOT / "requirements.txt"


class TestPhase4Closeout(unittest.TestCase):
    def test_acceptance_record_and_current_governance(self):
        record = json.loads(ACCEPTANCE_JSON.read_text(encoding="utf-8"))
        self.assertEqual(record["decision"], "PHASE_4_ACCEPTED")
        self.assertEqual(record["adr_0004_status"], "ACCEPTED_PHASE_4")
        self.assertEqual(record["phase_4_status"], "COMPLETE")
        self.assertEqual(
            record["accepted_evidence_baseline"],
            "05de2b04279a72ece4834a984461a505de1188b3",
        )
        self.assertFalse(record["next_phase_started"])
        self.assertTrue(record["next_planning_gate_required"])

        adr = ADR4.read_text(encoding="utf-8")
        block = adr.replace("\r\n", "\n").split("## Status", 1)[1].split("## Context", 1)[0]
        self.assertIn("Accepted (Phase 4)", block)
        self.assertNotRegex(block, r"(?m)^\s*Proposed\s*$")

        status = STATUS.read_text(encoding="utf-8")
        self.assertIn("Phase 4 | **Completed and accepted", status)
        self.assertIn("ADR 0004 **Accepted (Phase 4)**", status)
        self.assertIn("Next phase | **Not started", status)

        roadmap = ROADMAP.read_text(encoding="utf-8")
        self.assertIn("## Phase 4 — Learned neuromorphic backend", roadmap)
        self.assertIn("**Completed and accepted.**", roadmap)
        self.assertIn("## Next phase — not selected", roadmap)

        spec = SPEC.read_text(encoding="utf-8")
        self.assertIn("Completed and accepted", spec)
        self.assertIn("ADR 0004 Accepted (Phase 4)", spec)

    def test_acceptance_is_recomputed_from_lower_level_evidence(self):
        exp3 = json.loads(EXP3.read_text(encoding="utf-8"))
        exp4 = json.loads(EXP4.read_text(encoding="utf-8"))
        exp5 = json.loads(EXP5.read_text(encoding="utf-8"))
        record = json.loads(ACCEPTANCE_JSON.read_text(encoding="utf-8"))

        self.assertEqual(exp3["decision"], "FIRST_CPU_SNN_TRAINING_VERIFIED")
        self.assertEqual(exp3["training_run_count"], 1)
        self.assertTrue(exp3["accepted"])
        self.assertGreaterEqual(exp3["metrics"]["test_balanced_accuracy"], 0.90)
        self.assertGreaterEqual(exp3["metrics"]["per_class_recall"]["0"], 0.85)
        self.assertGreaterEqual(exp3["metrics"]["per_class_recall"]["1"], 0.85)
        self.assertGreaterEqual(exp3["metrics"]["margin_over_baseline"], 0.20)
        self.assertGreaterEqual(exp3["metrics"]["time_reversal_positive_score_drop"], 0.10)

        self.assertEqual(exp4["decision"], "LEARNED_SNN_PROVIDER_PARITY_VERIFIED")
        self.assertEqual(exp4["training_run_count"], 0)
        self.assertEqual(exp4["parity_sample_counts"]["total"], 197)
        self.assertEqual(exp4["predicted_class_agreement"]["count"], 197)
        self.assertEqual(exp4["predicted_class_agreement"]["rate"], 1.0)
        self.assertEqual(exp4["spike_count_agreement"]["count"], 197)
        self.assertEqual(exp4["spike_count_agreement"]["rate"], 1.0)
        self.assertTrue(exp4["spike_count_agreement"]["exposed"])
        self.assertLessEqual(
            exp4["max_abs_logit_difference"],
            exp4["tolerances_predeclared"]["max_abs_logit_difference"],
        )
        self.assertLessEqual(
            exp4["max_abs_probability_difference"],
            exp4["tolerances_predeclared"]["max_abs_probability_difference"],
        )

        self.assertEqual(exp5["decision"], "PHASE4_LEARNED_SNN_BREADTH_SAFETY_VERIFIED")
        self.assertEqual(exp5["training_run_count"], 0)
        self.assertEqual(exp5["frozen_test_breadth"]["sample_count"], 128)
        self.assertEqual(exp5["frozen_test_breadth"]["correct_count"], 128)
        self.assertEqual(exp5["frozen_test_breadth"]["balanced_accuracy"], 1.0)
        self.assertEqual(exp5["frozen_test_breadth"]["class_0_recall"], 1.0)
        self.assertEqual(exp5["frozen_test_breadth"]["class_1_recall"], 1.0)
        self.assertGreaterEqual(
            exp5["temporal_breadth"]["temporal_mean_score_drop"],
            exp5["temporal_breadth"]["required_min_drop"],
        )
        self.assertTrue(exp5["security_fixes"]["in_memory_artifact_injection_removed"])
        self.assertTrue(exp5["security_fixes"]["bounded_artifact_read"])
        self.assertTrue(exp5["security_fixes"]["strict_learned_event_envelope"])
        self.assertTrue(exp5["security_fixes"]["batch_atomicity_prevalidation"])
        self.assertTrue(exp5["security_fixes"]["rejected_input_no_successful_state_mutation"])
        self.assertEqual(exp5["security_fixes"]["max_artifact_bytes"], 262144)
        self.assertEqual(exp5["security_fixes"]["max_event_id_chars"], 128)
        self.assertEqual(exp5["security_fixes"]["max_learned_batch_events"], 256)
        self.assertTrue(exp5["edge_controls"]["pass"])
        self.assertTrue(exp5["malformed_inputs"]["pass"])
        self.assertTrue(exp5["corrupted_artifacts"]["pass"])
        self.assertTrue(exp5["fallback_modalities"]["pass"])

        self.assertEqual(record["evidence_chain"]["EXP-4-003"], exp3["decision"])
        self.assertEqual(record["evidence_chain"]["EXP-4-004"], exp4["decision"])
        self.assertEqual(record["evidence_chain"]["EXP-4-005"], exp5["decision"])

    def test_artifact_and_authority_boundaries(self):
        record = json.loads(ACCEPTANCE_JSON.read_text(encoding="utf-8"))
        digest = hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()
        self.assertEqual(digest, record["provider"]["artifact_sha256"])
        self.assertEqual(
            digest,
            "dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc",
        )
        self.assertTrue(record["provider"]["trained"])
        self.assertTrue(record["provider"]["learned"])
        self.assertTrue(record["provider"]["software_snn"])
        self.assertFalse(record["provider"]["hardware_neuromorphic"])
        self.assertFalse(record["provider"]["stateful_streaming"])
        self.assertFalse(record["provider"]["energy_metrics"])
        self.assertFalse(record["provider"]["global_default"])
        self.assertTrue(record["provider"]["explicit_activation_only"])

        for value in record["authority"].values():
            if isinstance(value, bool):
                self.assertFalse(value)
            else:
                self.assertEqual(value, 0)

    def test_qwen_and_runtime_dependencies_remain_unchanged(self):
        record = json.loads(ACCEPTANCE_JSON.read_text(encoding="utf-8"))
        self.assertFalse(record["qwen_boundary"]["registry_changed_by_phase_4"])
        self.assertFalse(record["qwen_boundary"]["capabilities_expanded_by_phase_4"])
        self.assertFalse(record["qwen_boundary"]["training_or_adapters"])

        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        entry = next(
            m
            for m in registry["models"]
            if m["provider_id"] == "siona-local-open-weight-v1"
            and m["model_id"] == "Qwen3-1.7B-Q4_K_M"
        )
        caps = entry["capabilities"]
        self.assertTrue(caps["chat"])
        self.assertFalse(caps["tools"])
        self.assertFalse(caps["structured_json"])
        self.assertFalse(caps["streaming"])
        self.assertFalse(caps["multimodal"])
        self.assertEqual(caps["context_window"], 4096)
        self.assertFalse(entry["siona_native"])

        requirements = REQUIREMENTS.read_text(encoding="utf-8").lower()
        for package in ("torch", "snntorch", "norse"):
            self.assertNotIn(package, requirements)
        self.assertFalse(record["runtime_dependencies"]["torch"])
        self.assertFalse(record["runtime_dependencies"]["snntorch"])
        self.assertFalse(record["runtime_dependencies"]["numpy"])
        self.assertFalse(record["runtime_dependencies"]["norse"])

    def test_historical_experiment_governance_is_not_rewritten(self):
        exp3 = json.loads(EXP3.read_text(encoding="utf-8"))
        exp4 = json.loads(EXP4.read_text(encoding="utf-8"))
        exp5 = json.loads(EXP5.read_text(encoding="utf-8"))
        self.assertEqual(exp3["adr_0004_status"], "PROPOSED")
        self.assertEqual(exp4["adr_0004_status"], "PROPOSED")
        self.assertEqual(exp5["adr_0004_status"], "PROPOSED")
        self.assertIn("IN_PROGRESS", exp3["phase_4_status"])
        self.assertIn("IN_PROGRESS", exp4["phase_4_status"])
        self.assertIn("IN_PROGRESS", exp5["phase_4_status"])

    def test_non_claims_remain_explicit(self):
        record = json.loads(ACCEPTANCE_JSON.read_text(encoding="utf-8"))
        non_claims = set(record["non_claims"])
        for required in (
            "NEUROMORPHIC_SILICON_EXECUTION",
            "CUDA_GPU_SNN_TRAINING_OR_BENCHMARK",
            "MEASURED_ENERGY_EFFICIENCY",
            "EVENT_BY_EVENT_PERSISTENT_STREAMING_SNN",
            "QWEN_FINE_TUNING_OR_ADAPTERS",
            "ROBOTICS_OR_PHYSICAL_ACTUATION",
            "PRODUCTION_SECURITY_CERTIFICATION",
        ):
            self.assertIn(required, non_claims)

        doc = ACCEPTANCE_DOC.read_text(encoding="utf-8").lower()
        self.assertIn("not a claim that the external qwen foundation weights are siona-native", doc)
        self.assertIn("no subsequent phase starts automatically", doc)


if __name__ == "__main__":
    unittest.main()
