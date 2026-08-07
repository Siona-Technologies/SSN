"""Phase 4 learned-neuromorphic planning/closeout consistency (offline only)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs" / "PHASE_4_ENGINEERING_SPEC.md"
PLANNING = ROOT / "docs" / "PHASE_4_PLANNING_ACCEPTANCE.md"
CLOSEOUT = ROOT / "docs" / "PHASE_4_ACCEPTANCE.md"
ADR = ROOT / "docs" / "adr" / "0004-learned-neuromorphic-backend-strategy.md"
STATUS = ROOT / "docs" / "PHASE_STATUS.md"
ROADMAP = ROOT / "docs" / "SIONA_PHASE_ROADMAP.md"
DEFERRED = ROOT / "docs" / "DEFERRED_CAPABILITIES.md"
NEURO = ROOT / "docs" / "SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md"
REGISTRY = ROOT / "config" / "model_registry.json"


class TestPhase4PlanningDocs(unittest.TestCase):
    def test_historical_planning_gate_is_preserved(self):
        spec = SPEC.read_text(encoding="utf-8")
        planning = PLANNING.read_text(encoding="utf-8")
        self.assertIn("Planning gate accepted", spec)
        self.assertIn("Phase 4A", spec)
        self.assertIn("**Status:** Accepted planning gate", planning)
        self.assertIn("A real SNN training run is **not yet authorized**", planning)
        # Planning records remain historical; current authority is the closeout.
        self.assertIn("EXP-4-001", planning)

    def test_current_phase4_closeout_status(self):
        closeout = CLOSEOUT.read_text(encoding="utf-8")
        status = STATUS.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        adr = ADR.read_text(encoding="utf-8")

        self.assertIn("**Status:** Accepted", closeout)
        self.assertIn("Phase 4: **Complete**", closeout)
        self.assertIn("Phase 5: **Not Started**", closeout)
        self.assertIn("Phase 4 | **Completed and accepted", status)
        self.assertIn("ADR 0004 **Accepted (Phase 4)**", status)
        self.assertIn("Phase 5 | **Not started", status)
        self.assertIn("## Phase 4 — Learned neuromorphic backend", roadmap)
        self.assertIn("**Completed and accepted.**", roadmap)
        self.assertIn("## Phase 5 — Planning boundary", roadmap)
        self.assertIn("Phase 5 remains NOT STARTED", roadmap)

        status_block = adr.replace("\r\n", "\n").split("## Status", 1)[1].split(
            "## Context", 1
        )[0]
        self.assertIn("Accepted (Phase 4)", status_block)
        self.assertNotRegex(status_block, r"(?m)^\s*Proposed\s*$")

    def test_phase4_training_and_authority_exclusions_remain(self):
        combined = "\n".join(
            p.read_text(encoding="utf-8")
            for p in (SPEC, PLANNING, CLOSEOUT, ADR, STATUS, ROADMAP, DEFERRED, NEURO)
        ).lower()

        for required in (
            "physical actuation",
            "robotics",
            "deterministic",
            "cuda",
            "qwen",
        ):
            self.assertIn(required, combined)
        self.assertIn("no tool or physical authority", combined)
        self.assertIn("cpu software", combined)
        self.assertIn("phase 5", combined)

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


if __name__ == "__main__":
    unittest.main()
