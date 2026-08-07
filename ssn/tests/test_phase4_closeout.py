"""Phase 4 acceptance and Phase 5 boundary regression tests."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACCEPTANCE = ROOT / "docs" / "PHASE_4_ACCEPTANCE.md"
EVIDENCE = ROOT / "docs" / "evidence" / "PHASE_4_ACCEPTANCE.json"
STATUS = ROOT / "docs" / "PHASE_STATUS.md"
ROADMAP = ROOT / "docs" / "SIONA_PHASE_ROADMAP.md"
ADR4 = ROOT / "docs" / "adr" / "0004-learned-neuromorphic-backend-strategy.md"
ARTIFACT = ROOT / "artifacts" / "neuromorphic" / "phase4b-lif-final-membrane-v1.json"
REGISTRY = ROOT / "config" / "model_registry.json"
REQUIREMENTS = ROOT / "requirements.txt"

ARTIFACT_SHA = "dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc"


class TestPhase4Closeout(unittest.TestCase):
    def test_acceptance_record_and_current_status(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(data["decision"], "PHASE_4_ACCEPTED")
        self.assertEqual(data["adr_0004_status"], "ACCEPTED_PHASE_4")
        self.assertEqual(data["phase_4_status"], "COMPLETE")
        self.assertEqual(data["phase_5_status"], "NOT_STARTED")
        self.assertEqual(data["artifact_sha256"], ARTIFACT_SHA)

        status = STATUS.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        acceptance = ACCEPTANCE.read_text(encoding="utf-8")
        self.assertIn("Phase 4 | **Completed and accepted", status)
        self.assertIn("ADR 0004 **Accepted (Phase 4)**", status)
        self.assertIn("Phase 5 | **Not started", status)
        self.assertIn("## Phase 5 — Planning boundary", roadmap)
        self.assertIn("Phase 5 remains NOT STARTED", roadmap)
        self.assertIn("Phase 4: **Complete**", acceptance)
        self.assertIn("Phase 5: **Not Started**", acceptance)

    def test_adr4_is_accepted_and_limits_are_retained(self):
        adr = ADR4.read_text(encoding="utf-8")
        block = adr.replace("\r\n", "\n").split("## Status", 1)[1].split("## Context", 1)[0]
        self.assertIn("Accepted (Phase 4)", block)
        self.assertIn("CPU-only software SNN", adr)
        self.assertIn("no tool or physical-actuator authority", adr)
        self.assertIn("Qwen fine-tuning", adr)
        self.assertIn("Phase 5 implementation", adr)

    def test_required_experiment_decisions_are_recorded(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(data["required_evidence"]["EXP-4-003"], "FIRST_CPU_SNN_TRAINING_VERIFIED")
        self.assertEqual(data["required_evidence"]["EXP-4-004"], "LEARNED_SNN_PROVIDER_PARITY_VERIFIED")
        self.assertEqual(
            data["required_evidence"]["EXP-4-005"],
            "PHASE4_LEARNED_SNN_BREADTH_SAFETY_VERIFIED",
        )

    def test_canonical_artifact_integrity(self):
        self.assertEqual(hashlib.sha256(ARTIFACT.read_bytes()).hexdigest(), ARTIFACT_SHA)
        artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(artifact["provider_target"], "siona-neuro-learned-lif-v1")
        self.assertFalse(artifact["tool_authority"])
        self.assertFalse(artifact["physical_actuation_authority"])

    def test_runtime_dependency_and_qwen_boundaries(self):
        req = REQUIREMENTS.read_text(encoding="utf-8").lower()
        for package in ("torch", "snntorch", "norse"):
            self.assertNotIn(package, req)

        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        entry = next(
            m
            for m in registry["models"]
            if m["provider_id"] == "siona-local-open-weight-v1"
            and m["model_id"] == "Qwen3-1.7B-Q4_K_M"
        )
        self.assertTrue(entry["capabilities"]["chat"])
        self.assertFalse(entry["capabilities"]["tools"])
        self.assertFalse(entry["capabilities"]["structured_json"])
        self.assertFalse(entry["capabilities"]["streaming"])
        self.assertFalse(entry["capabilities"]["multimodal"])
        self.assertFalse(entry["siona_native"])

    def test_phase5_not_silently_authorized(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(data["next_gate"], "SEPARATE_PHASE_5_PLANNING_DECISION")
        self.assertFalse(data["accepted_boundaries"]["qwen_fine_tuning_authorized"])
        self.assertFalse(data["accepted_boundaries"]["global_default_promotion_authorized"])
        self.assertFalse(data["accepted_boundaries"]["physical_actuation_authority"])


if __name__ == "__main__":
    unittest.main()
