"""EXP-4-001 Phase 4A readiness consistency tests (model-free, no training)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from ssn.cognition.neuromorphic.contracts import NeuromorphicProvider
from ssn.cognition.neuromorphic.phase4a_dataset import split_fingerprint
from ssn.cognition.neuromorphic.providers import DeterministicNeuromorphicProvider

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs" / "evidence" / "EXP-4-001_PHASE_4A_READINESS.json"
TASK = ROOT / "config" / "phase4a_temporal_salience_task.json"
REQUIREMENTS = ROOT / "requirements.txt"
REGISTRY = ROOT / "config" / "model_registry.json"
ADR4 = ROOT / "docs" / "adr" / "0004-learned-neuromorphic-backend-strategy.md"
STATUS = ROOT / "docs" / "PHASE_STATUS.md"


class TestPhase4AReadiness(unittest.TestCase):
    def test_evidence_keeps_training_and_installation_disabled(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(data["experiment_id"], "EXP-4-001")
        self.assertEqual(
            data["decision"],
            "PHASE_4A_READINESS_DEFINED_TRAINING_NOT_AUTHORIZED",
        )
        self.assertFalse(data["training_executed"])
        self.assertFalse(data["dependency_installation_executed"])
        self.assertFalse(data["qwen_runtime_started"])
        self.assertEqual(data["real_model_calls"], 0)
        self.assertEqual(data["tool_executions"], 0)
        # Immutable historical governance at the time EXP-4-001 ran.
        self.assertEqual(data["adr_0004_status"], "PROPOSED")

    def test_existing_contract_is_provider_replaceable(self):
        for method in (
            "capabilities",
            "health",
            "reset",
            "get_state",
            "process_event",
            "process_batch",
        ):
            self.assertTrue(hasattr(NeuromorphicProvider, method))

        provider = DeterministicNeuromorphicProvider()
        caps = provider.capabilities()
        self.assertTrue(caps.deterministic)
        self.assertTrue(caps.metadata["simulated"])
        self.assertFalse(caps.metadata["trained"])
        self.assertTrue(provider.health()["simulated"])

    def test_current_requirements_have_no_training_stack(self):
        requirements = [
            line.strip().lower()
            for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        names = {line.split("==", 1)[0].split(">=", 1)[0].split("<=", 1)[0] for line in requirements}
        self.assertNotIn("torch", names)
        self.assertNotIn("torchvision", names)
        self.assertNotIn("snntorch", names)
        self.assertNotIn("norse", names)

    def test_backend_research_is_recommendation_not_installation(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        research = data["backend_research"]
        preferred = research["preferred_candidate"]
        alternative = research["alternative"]
        self.assertEqual(preferred["package"], "snntorch")
        self.assertEqual(preferred["version"], "1.0.0")
        self.assertEqual(preferred["license"], "MIT")
        self.assertFalse(preferred["dependency_installation_authorized"])
        self.assertFalse(preferred["python_3_12_compatibility_claimed"])
        self.assertEqual(alternative["package"], "norse")
        self.assertEqual(alternative["version"], "1.1.0")
        self.assertEqual(alternative["license"], "LGPLv3")
        self.assertFalse(alternative["dependency_installation_authorized"])
        self.assertFalse(research["exact_pytorch_version_selected"])

    def test_task_fingerprints_match_committed_evidence(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        task = json.loads(TASK.read_text(encoding="utf-8"))
        expected = data["task"]["split_fingerprints"]
        for split in ("train", "validation", "test"):
            self.assertEqual(split_fingerprint(split), expected[split])
        # Task config remains the frozen pre-training record.
        self.assertFalse(task["training"]["authorized"])
        self.assertFalse(task["candidate_backend"]["dependency_installation_authorized"])

    def test_qwen_registry_capabilities_remain_phase3_conservative(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
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
        self.assertEqual(caps["context_window"], 4096)
        self.assertFalse(entry["siona_native"])

    def test_historical_readiness_and_current_accepted_status_are_distinct(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(data["adr_0004_status"], "PROPOSED")
        adr = ADR4.read_text(encoding="utf-8")
        status_block = adr.replace("\r\n", "\n").split("## Status", 1)[1].split(
            "## Context", 1
        )[0]
        self.assertIn("Accepted (Phase 4)", status_block)
        status = STATUS.read_text(encoding="utf-8")
        self.assertIn("Phase 4 | **Completed and accepted", status)
        self.assertIn("ADR 0004 **Accepted (Phase 4)**", status)


if __name__ == "__main__":
    unittest.main()
