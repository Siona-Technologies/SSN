"""EXP-4-003 first CPU SNN training evidence tests (model-free; no training stack)."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from ssn.cognition.neuromorphic.phase4a_dataset import split_fingerprint

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs" / "evidence" / "EXP-4-003_FIRST_CPU_SNN_TRAINING.json"
ARTIFACT = ROOT / "artifacts" / "neuromorphic" / "phase4b-lif-final-membrane-v1.json"
NARRATIVE = ROOT / "docs" / "SIONA_PHASE_4B_FIRST_CPU_SNN_TRAINING.md"
REQUIREMENTS = ROOT / "requirements.txt"
REGISTRY = ROOT / "config" / "model_registry.json"
ADR4 = ROOT / "docs" / "adr" / "0004-learned-neuromorphic-backend-strategy.md"
STATUS = ROOT / "docs" / "PHASE_STATUS.md"
TASK = ROOT / "config" / "phase4a_temporal_salience_task.json"


class TestPhase4BExp4003Evidence(unittest.TestCase):
    def test_evidence_schema_and_decision(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(data["experiment_id"], "EXP-4-003")
        self.assertEqual(data["decision"], "FIRST_CPU_SNN_TRAINING_VERIFIED")
        self.assertTrue(data["accepted"])
        self.assertEqual(data["training_run_count"], 1)
        self.assertEqual(data["qwen_run_count"], 0)
        self.assertEqual(data["tool_execution_count"], 0)
        self.assertFalse(data["tool_authority"])
        self.assertFalse(data["physical_actuation_authority"])
        self.assertFalse(data["cuda_used"])
        self.assertTrue(data["cpu_only"])
        self.assertFalse(data["project_requirements_changed"])
        self.assertFalse(data["absolute_operator_paths_committed"])
        self.assertEqual(data["adr_0004_status"], "PROPOSED")
        self.assertEqual(
            data["phase_4_status"],
            "IN_PROGRESS_LEARNED_PROVIDER_INTEGRATION_PENDING",
        )
        self.assertEqual(
            data["next_blocker"],
            "LEARNED SNN PROVIDER INTEGRATION + FALLBACK/PARITY VERIFICATION",
        )
        blob = EVIDENCE.read_text(encoding="utf-8")
        self.assertNotIn("C:/Users", blob)
        self.assertNotIn("C:\\Users", blob)
        self.assertNotIn("njaji", blob.lower())

    def test_acceptance_recomputed_from_stored_metrics(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        metrics = data["metrics"]
        checks = metrics["acceptance_checks"]
        self.assertGreaterEqual(metrics["test_balanced_accuracy"], 0.90)
        self.assertGreaterEqual(metrics["per_class_recall"]["0"], 0.85)
        self.assertGreaterEqual(metrics["per_class_recall"]["1"], 0.85)
        self.assertGreaterEqual(metrics["margin_over_baseline"], 0.20)
        self.assertGreaterEqual(metrics["time_reversal_positive_score_drop"], 0.10)
        self.assertTrue(checks["balanced_accuracy"])
        self.assertTrue(checks["class0_recall"])
        self.assertTrue(checks["class1_recall"])
        self.assertTrue(checks["baseline_margin"])
        self.assertTrue(checks["time_reversal"])
        self.assertTrue(all(checks.values()))
        # Recompute margin from lower-level metric.
        self.assertAlmostEqual(
            metrics["margin_over_baseline"],
            metrics["test_balanced_accuracy"] - 0.50,
            places=12,
        )

    def test_candidate_artifact_hash_matches_evidence(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        blob = ARTIFACT.read_bytes()
        digest = hashlib.sha256(blob).hexdigest()
        self.assertEqual(digest, data["artifacts"]["candidate_artifact_sha256"])
        self.assertEqual(
            digest,
            "dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc",
        )
        artifact = json.loads(blob.decode("utf-8"))
        self.assertEqual(artifact["artifact_type"], "SIONA_LEARNED_NEUROMORPHIC_CANDIDATE")
        self.assertEqual(artifact["architecture_id"], "phase4b-lif-final-membrane-v1")
        self.assertEqual(artifact["training_experiment"], "EXP-4-003")
        self.assertFalse(artifact["tool_authority"])
        self.assertFalse(artifact["physical_actuation_authority"])
        text = blob.decode("utf-8")
        self.assertNotIn("C:/Users", text)
        self.assertNotIn("C:\\Users", text)

    def test_frozen_task_fingerprints(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        expected = data["dataset_fingerprints"]
        for split in ("train", "validation", "test"):
            self.assertEqual(split_fingerprint(split), expected[split])
        task = json.loads(TASK.read_text(encoding="utf-8"))
        self.assertEqual(task["task_id"], "phase4a-temporal-salience-v1")

    def test_qwen_registry_unchanged_and_conservative(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        registry_bytes = REGISTRY.read_bytes()
        self.assertEqual(
            hashlib.sha256(registry_bytes).hexdigest(),
            data["model_registry_sha256"],
        )
        registry = json.loads(registry_bytes.decode("utf-8"))
        entry = next(
            model
            for model in registry["models"]
            if model["provider_id"] == "siona-local-open-weight-v1"
            and model["model_id"] == "Qwen3-1.7B-Q4_K_M"
        )
        caps = entry["capabilities"]
        self.assertTrue(caps["chat"])
        self.assertFalse(caps["tools"])
        self.assertFalse(caps["structured_json"])
        self.assertFalse(caps["streaming"])
        self.assertFalse(caps["multimodal"])
        self.assertFalse(entry.get("siona_native", False))

    def test_adr_phase_and_requirements_boundaries(self):
        adr = ADR4.read_text(encoding="utf-8")
        status = STATUS.read_text(encoding="utf-8")
        narrative = NARRATIVE.read_text(encoding="utf-8")
        status_block = adr.replace("\r\n", "\n").split("## Status", 1)[1].split(
            "## Context", 1
        )[0]
        self.assertRegex(status_block, r"(?m)^\s*Proposed\s*$")
        self.assertIn("FIRST_CPU_SNN_TRAINING_VERIFIED", status)
        self.assertIn("learned-provider integration", status.lower())
        self.assertIn("ADR 0004 **Proposed**", status)
        self.assertIn("Phase 4 remains **not started**", status)
        self.assertIn("FIRST_CPU_SNN_TRAINING_VERIFIED", narrative)
        requirements = [
            line.strip().lower()
            for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        names = {
            line.split("==", 1)[0].split(">=", 1)[0].split("<=", 1)[0] for line in requirements
        }
        self.assertNotIn("torch", names)
        self.assertNotIn("snntorch", names)
        self.assertNotIn("norse", names)


if __name__ == "__main__":
    unittest.main()
