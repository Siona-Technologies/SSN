"""Governed Phase 5 streaming-neuromorphic planning regressions."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs" / "PHASE_5_ENGINEERING_SPEC.md"
PLANNING = ROOT / "docs" / "PHASE_5_PLANNING_ACCEPTANCE.md"
EVIDENCE = ROOT / "docs" / "evidence" / "PHASE_5_PLANNING_ACCEPTANCE.json"
ADR5 = ROOT / "docs" / "adr" / "0005-stateful-streaming-neuromorphic-strategy.md"
STATUS = ROOT / "docs" / "PHASE_STATUS.md"
ROADMAP = ROOT / "docs" / "SIONA_PHASE_ROADMAP.md"
PHASE4_ACCEPTANCE = ROOT / "docs" / "evidence" / "PHASE_4_ACCEPTANCE.json"
ARTIFACT = ROOT / "artifacts" / "neuromorphic" / "phase4b-lif-final-membrane-v1.json"
REGISTRY = ROOT / "config" / "model_registry.json"
REQUIREMENTS = ROOT / "requirements.txt"


class TestPhase5StreamingNeuromorphicPlanning(unittest.TestCase):
    def test_current_planning_status_and_objective(self):
        spec = SPEC.read_text(encoding="utf-8")
        planning = PLANNING.read_text(encoding="utf-8")
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        status = STATUS.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")

        self.assertEqual(evidence["decision"], "PHASE_5_PLANNING_ACCEPTED")
        self.assertEqual(evidence["objective"], "STATEFUL_STREAMING_NEUROMORPHIC_RUNTIME")
        self.assertEqual(evidence["phase_5_implementation_status"], "NOT_STARTED")
        self.assertEqual(evidence["adr_0005_status"], "PROPOSED")
        self.assertIn("Stateful Streaming Neuromorphic Runtime", spec)
        self.assertIn("**Status:** Accepted planning gate", planning)
        self.assertIn("Phase 5 | **Planning accepted", status)
        self.assertIn("ADR 0005 **Proposed**", status)
        self.assertIn("## Phase 5 — Stateful streaming neuromorphic runtime", roadmap)

    def test_adr0005_is_proposed(self):
        adr = ADR5.read_text(encoding="utf-8")
        block = adr.replace("\r\n", "\n").split("## Status", 1)[1].split("## Context", 1)[0]
        self.assertRegex(block, r"(?m)^\s*Proposed\s*$")
        self.assertNotIn("Accepted", block)

    def test_phase4_artifact_is_frozen_reference(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        phase4 = json.loads(PHASE4_ACCEPTANCE.read_text(encoding="utf-8"))
        digest = hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()
        expected = "dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc"
        self.assertEqual(digest, expected)
        self.assertEqual(evidence["accepted_phase4_reference"]["artifact_sha256"], expected)
        self.assertEqual(phase4["provider"]["artifact_sha256"], expected)
        self.assertFalse(evidence["accepted_phase4_reference"]["stateful"])
        self.assertFalse(evidence["accepted_phase4_reference"]["runtime_training_dependencies"])

    def test_initial_streaming_parity_targets_are_frozen(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        parity = evidence["frozen_initial_parity_targets"]
        self.assertEqual(parity["frozen_test_samples"], 128)
        self.assertEqual(parity["predicted_class_agreement_required"], 128)
        self.assertEqual(parity["spike_count_agreement_required"], 128)
        self.assertEqual(parity["max_abs_logit_difference"], 1e-12)
        self.assertEqual(parity["max_abs_probability_difference"], 1e-12)

    def test_async_bus_is_planning_prerequisite_not_immediate_wiring(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        bus = evidence["existing_async_bus"]
        self.assertTrue(bus["available"])
        self.assertTrue(bus["bounded_queue"])
        self.assertTrue(bus["priority_backpressure"])
        self.assertTrue(bus["event_ttl"])
        self.assertTrue(bus["handler_timeout"])
        self.assertTrue(bus["graceful_shutdown"])
        self.assertFalse(bus["phase5_bus_wiring_authorized_immediately"])

    def test_no_retraining_qwen_hardware_or_authority_is_authorized(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        denied = set(evidence["not_authorized"])
        for required in (
            "SNN_RETRAINING",
            "PHASE4_ARTIFACT_OR_WEIGHT_MUTATION",
            "QWEN_TRAINING_OR_CAPABILITY_CHANGE",
            "GLOBAL_STREAMING_PROVIDER_DEFAULT_SWITCH",
            "CUDA_OR_GPU_CLAIM",
            "LOIHI_FPGA_OR_NEUROMORPHIC_SILICON_CLAIM",
            "MEASURED_ENERGY_CLAIM",
            "REAL_EVENT_CAMERA_HARDWARE",
            "TOOL_OR_PHYSICAL_AUTHORITY",
            "ROBOTICS_IOT_OR_ACTUATION",
            "PRODUCTION_CERTIFICATION",
        ):
            self.assertIn(required, denied)

        requirements = REQUIREMENTS.read_text(encoding="utf-8").lower()
        for package in ("torch", "snntorch", "norse"):
            self.assertNotIn(package, requirements)

        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        qwen = next(m for m in registry["models"] if m["provider_id"] == "siona-local-open-weight-v1")
        self.assertTrue(qwen["capabilities"]["chat"])
        self.assertFalse(qwen["capabilities"]["tools"])
        self.assertFalse(qwen["capabilities"]["structured_json"])
        self.assertFalse(qwen["capabilities"]["streaming"])
        self.assertFalse(qwen["capabilities"]["multimodal"])
        self.assertFalse(qwen["siona_native"])

    def test_historical_phase4_closeout_is_not_rewritten(self):
        phase4 = json.loads(PHASE4_ACCEPTANCE.read_text(encoding="utf-8"))
        self.assertEqual(phase4["decision"], "PHASE_4_ACCEPTED")
        self.assertFalse(phase4["next_phase_started"])
        self.assertTrue(phase4["next_planning_gate_required"])


if __name__ == "__main__":
    unittest.main()
