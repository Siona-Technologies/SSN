"""Phase 4 planning-history and accepted-governance consistency (offline only)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs" / "PHASE_4_ENGINEERING_SPEC.md"
PLANNING = ROOT / "docs" / "PHASE_4_PLANNING_ACCEPTANCE.md"
ACCEPTANCE = ROOT / "docs" / "PHASE_4_ACCEPTANCE.md"
ADR = ROOT / "docs" / "adr" / "0004-learned-neuromorphic-backend-strategy.md"
STATUS = ROOT / "docs" / "PHASE_STATUS.md"
ROADMAP = ROOT / "docs" / "SIONA_PHASE_ROADMAP.md"
DEFERRED = ROOT / "docs" / "DEFERRED_CAPABILITIES.md"
NEURO = ROOT / "docs" / "SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md"
REGISTRY = ROOT / "config" / "model_registry.json"


class TestPhase4PlanningDocs(unittest.TestCase):
    def test_planning_record_remains_historical_while_current_state_is_accepted(self):
        spec = SPEC.read_text(encoding="utf-8")
        planning = PLANNING.read_text(encoding="utf-8")
        acceptance = ACCEPTANCE.read_text(encoding="utf-8")
        status = STATUS.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")

        self.assertIn("**Status:** Accepted planning gate", planning)
        self.assertIn("A real SNN training run is **not yet authorized**", planning)
        self.assertIn("EXP-4-001", planning)

        self.assertIn("Completed and accepted", spec)
        self.assertIn("ADR 0004 Accepted (Phase 4)", spec)
        self.assertIn("**Status:** Accepted", acceptance)
        self.assertIn("**Phase 4 is COMPLETE**", acceptance)
        self.assertIn("Phase 4 | **Completed and accepted", status)
        self.assertIn("ADR 0004 **Accepted (Phase 4)**", status)
        self.assertIn("## Phase 4 — Learned neuromorphic backend", roadmap)
        self.assertIn("**Completed and accepted.**", roadmap)
        self.assertIn("No next phase has started", roadmap)

    def test_adr0004_is_accepted_only_after_evidence_chain(self):
        adr = ADR.read_text(encoding="utf-8")
        status_block = adr.replace("\r\n", "\n").split("## Status", 1)[1].split(
            "## Context", 1
        )[0]
        self.assertIn("Accepted (Phase 4)", status_block)
        self.assertNotRegex(status_block, r"(?m)^\s*Proposed\s*$")
        for exp in ("EXP-4-001", "EXP-4-003", "EXP-4-004", "EXP-4-005"):
            self.assertIn(exp, adr)
        self.assertIn("satisfied", adr.lower())

    def test_phase4_training_and_authority_exclusions_remain(self):
        combined = "\n".join(
            p.read_text(encoding="utf-8")
            for p in (SPEC, PLANNING, ACCEPTANCE, ADR, STATUS, ROADMAP, DEFERRED, NEURO)
        ).lower()

        for required in (
            "qwen lora/qlora/peft",
            "physical actuation",
            "robotics",
            "owner-control",
            "deterministic",
            "no cuda gpu",
        ):
            self.assertIn(required, combined)

        self.assertIn("software snn", combined)
        self.assertIn("hardware_neuromorphic", combined)
        self.assertIn("learned snn provider", combined)
        self.assertIn("event-by-event", combined)

    def test_existing_qwen_registry_is_not_promoted(self):
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

    def test_deferred_capabilities_are_reconciled(self):
        deferred = DEFERRED.read_text(encoding="utf-8")
        self.assertIn("### ID: HW-SNN-001", deferred)
        self.assertIn("Phase 4 accepted for the bounded CPU-trained software SNN provider", deferred)
        self.assertIn("CUDA/GPU training or benchmarking", deferred)
        self.assertIn("### ID: HW-LLM-001", deferred)
        self.assertIn("Phase 3B accepted for the pinned conservative baseline", deferred)
        self.assertIn("### ID: MODEL-ADAPT-001", deferred)
        self.assertIn("no adapter training has occurred", deferred)


if __name__ == "__main__":
    unittest.main()
