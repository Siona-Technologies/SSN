"""Phase 4 learned-neuromorphic planning gate consistency (offline only)."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs" / "PHASE_4_ENGINEERING_SPEC.md"
ACCEPTANCE = ROOT / "docs" / "PHASE_4_PLANNING_ACCEPTANCE.md"
ADR = ROOT / "docs" / "adr" / "0004-learned-neuromorphic-backend-strategy.md"
STATUS = ROOT / "docs" / "PHASE_STATUS.md"
ROADMAP = ROOT / "docs" / "SIONA_PHASE_ROADMAP.md"
DEFERRED = ROOT / "docs" / "DEFERRED_CAPABILITIES.md"
NEURO = ROOT / "docs" / "SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md"
REGISTRY = ROOT / "config" / "model_registry.json"


class TestPhase4PlanningDocs(unittest.TestCase):
    def test_planning_gate_scope_and_status(self):
        spec = SPEC.read_text(encoding="utf-8")
        acceptance = ACCEPTANCE.read_text(encoding="utf-8")
        status = STATUS.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")

        self.assertIn("Planning gate accepted", spec)
        self.assertIn("Phase 4A", spec)
        self.assertIn("implementation/training not started", spec)
        self.assertIn("**Status:** Accepted planning gate", acceptance)
        self.assertIn("**Implementation status:** Phase 4A readiness defined; learned-provider implementation/training not started", acceptance)
        self.assertIn("Phase 4A only", acceptance)
        self.assertIn("A real SNN training run is **not yet authorized**", acceptance)
        self.assertIn("Phase 4 | **In progress", status)
        self.assertIn("EXP-4-003 first CPU SNN training VERIFIED", status)
        self.assertIn("ADR 0004 **Proposed**", status)
        self.assertIn(
            "Phase 4 remains **not started** at the learned-provider integration and Phase 4 completion level",
            status,
        )
        self.assertIn("## Phase 4 — Learned neuromorphic backend", roadmap)
        self.assertIn(
            "Planning gate accepted; EXP-4-003 first CPU SNN training verified; learned-provider integration pending",
            roadmap,
        )

    def test_adr0004_remains_proposed(self):
        adr = ADR.read_text(encoding="utf-8")
        status_block = adr.replace("\r\n", "\n").split("## Status", 1)[1].split(
            "## Context", 1
        )[0]
        self.assertRegex(status_block, r"(?m)^\s*Proposed\s*$")
        self.assertNotIn("Accepted", status_block)
        self.assertIn("does not authorize", adr.lower())
        self.assertIn("a training run", adr)
        self.assertIn("dependency installation", adr)

    def test_phase4_training_and_authority_exclusions(self):
        combined = "\n".join(
            p.read_text(encoding="utf-8")
            for p in (SPEC, ACCEPTANCE, ADR, STATUS, ROADMAP, DEFERRED, NEURO)
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

        self.assertIn("real snn training run is **not yet authorized**", combined)
        self.assertIn("no trained snn", combined)
        self.assertIn("learned snn provider", combined)

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
        self.assertIn("Target phase:** Phase 4", deferred)
        self.assertIn("Phase 4 planning candidate", deferred)
        self.assertIn("### ID: HW-LLM-001", deferred)
        self.assertIn("Phase 3B accepted for the pinned conservative baseline", deferred)
        self.assertIn("### ID: MODEL-ADAPT-001", deferred)
        self.assertIn("no adapter training has occurred", deferred)


if __name__ == "__main__":
    unittest.main()
