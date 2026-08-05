"""
Documentation consistency for Phase 2 closeout / Vision Charter.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CORE_DOCS = [
    ROOT / "docs" / "SIONA_VISION_CHARTER.md",
    ROOT / "docs" / "PHASE_2_ACCEPTANCE.md",
    ROOT / "docs" / "PHASE_3_ENGINEERING_SPEC.md",
    ROOT / "docs" / "PHASE_STATUS.md",
    ROOT / "docs" / "SIONA_VISION.md",
    ROOT / "docs" / "SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md",
    ROOT / "docs" / "SIONA_PHASE_ROADMAP.md",
    ROOT / "docs" / "adr" / "0001-hybrid-runtime-integration.md",
    ROOT / "docs" / "DEFERRED_CAPABILITIES.md",
    ROOT / "docs" / "HARDWARE_ROADMAP.md",
    ROOT / "docs" / "TECHNICAL_DEBT_REGISTER.md",
    ROOT / "docs" / "EXPERIMENT_LOG.md",
    ROOT / "docs" / "PHASE_3B_HARDWARE_INVENTORY.md",
    ROOT / "docs" / "PHASE_3B_MODEL_INDEPENDENCE.md",
    ROOT / "docs" / "PHASE_3B_MODEL_RUNTIME_RESEARCH.md",
    ROOT / "docs" / "PHASE_3B_INSTALLATION_RUNBOOK.md",
    ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md",
    ROOT / "docs" / "SIONA_BUILD_PLAN.md",
    ROOT / "docs" / "SIONA_AWS_ARCHITECTURE_SHOWCASE.md",
]

BANNED_PRODUCT = re.compile(r"\b(Pulse|Weza AI|Weza|Jarvis)\b", re.IGNORECASE)
BANNED_CLAIM = re.compile(
    r"trained SIONA-native foundation model exists|"
    r"deterministic neuromorphic provider is a trained SNN|"
    r"models? (?:may|can|should) directly command unrestricted",
    re.IGNORECASE,
)


class TestPhase2CloseoutDocs(unittest.TestCase):
    def test_required_closeout_docs_exist(self):
        for path in (
            ROOT / "docs" / "SIONA_VISION_CHARTER.md",
            ROOT / "docs" / "PHASE_2_ACCEPTANCE.md",
            ROOT / "docs" / "PHASE_3_ENGINEERING_SPEC.md",
        ):
            self.assertTrue(path.is_file(), f"missing {path}")

    def test_vision_charter_core_principles(self):
        text = (ROOT / "docs" / "SIONA_VISION_CHARTER.md").read_text(encoding="utf-8")
        plain = re.sub(r"\*+", "", text).lower()
        self.assertIn("One brain, many bodies", text)
        self.assertIn("SIBONA", text)
        self.assertIn("not implemented in phase 2", plain)
        self.assertIn("never directly command unrestricted physical actuators", plain)
        self.assertIn("Trace IDs are not authentication", text)

    def test_phase_status_labels(self):
        text = (ROOT / "docs" / "PHASE_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("7b92114", text)
        self.assertIn("19b3b13", text)
        self.assertNotIn("Final branch tip", text)
        self.assertIn("d6c17d0", text)
        self.assertIn("2e6abb6", text)
        self.assertIn("Completed and hosted-CI accepted", text)
        self.assertIn("Phase 3A completed; Phase 3B research recorded", text)
        self.assertIn(
            "Official-source research completed; provisional recommendation recorded — no runtime/model installed",
            text,
        )
        self.assertIn("SIONA_VISION_CHARTER.md", text)
        self.assertIn("PHASE_2_ACCEPTANCE.md", text)
        self.assertIn("PHASE_3_ENGINEERING_SPEC.md", text)
        self.assertIn("not started", text.lower())  # Phase 4 remains not started
        self.assertIn("PHASE_3B_HARDWARE_INVENTORY.md", text)
        self.assertIn("0003-first-local-model-strategy.md", text)
        self.assertNotIn("Phase 3A status (this branch)", text)
        self.assertNotIn("not marked accepted until", text)

    def test_phase3_spec_status(self):
        # Phase 3A completed/merged; Phase 3 overall in progress; Phase 3B research recorded.
        text = (ROOT / "docs" / "PHASE_3_ENGINEERING_SPEC.md").read_text(encoding="utf-8")
        self.assertIn("phase 3a", text.lower())
        self.assertIn("completed", text.lower())
        self.assertIn("in progress", text.lower())
        self.assertIn("phase 3b", text.lower())
        self.assertIn("d6c17d0", text)
        self.assertIn("2e6abb6", text)
        self.assertIn("install or download a real model", text.lower())

    def test_phase3b_planning_docs_exist(self):
        for path in (
            ROOT / "docs" / "PHASE_3B_HARDWARE_INVENTORY.md",
            ROOT / "docs" / "PHASE_3B_MODEL_INDEPENDENCE.md",
            ROOT / "docs" / "PHASE_3B_MODEL_RUNTIME_RESEARCH.md",
            ROOT / "docs" / "PHASE_3B_INSTALLATION_RUNBOOK.md",
            ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md",
        ):
            self.assertTrue(path.is_file(), f"missing {path}")
        independence = (ROOT / "docs" / "PHASE_3B_MODEL_INDEPENDENCE.md").read_text(
            encoding="utf-8"
        )
        plain = re.sub(r"\*+", "", independence).lower()
        self.assertIn("does not currently own a trained foundation model", plain)
        self.assertIn("replaceable", plain)
        adr = (ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Proposed", adr)
        self.assertIn("No final runtime or model is approved", adr)

    def test_phase3b_official_research_gate(self):
        research = (ROOT / "docs" / "PHASE_3B_MODEL_RUNTIME_RESEARCH.md").read_text(
            encoding="utf-8"
        )
        # Research must contain completed comparisons, not only unresolved placeholders.
        self.assertIn("Provisional runtime recommendation", research)
        self.assertIn("PROVISIONAL — REQUIRES OWNER APPROVAL BEFORE INSTALLATION", research)
        self.assertIn("PROVISIONAL — NO MODEL DOWNLOAD AUTHORIZED", research)
        self.assertIn("llama.cpp native Windows", research)
        self.assertIn("Qwen3-1.7B", research)
        self.assertNotIn(
            "Do not fill unstable facts from memory",
            research,
        )
        # Ensure the document is not still the empty template form.
        self.assertGreater(research.count("Officially stated"), 10)
        runbook = (ROOT / "docs" / "PHASE_3B_INSTALLATION_RUNBOOK.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("no install authorized", runbook.lower())
        self.assertIn("UNAPPROVED", runbook)
        status = (ROOT / "docs" / "PHASE_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("Phase 4 remains **not started**", status)
        adr = (ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md").read_text(
            encoding="utf-8"
        )
        self.assertRegex(adr.replace("\r\n", "\n"), r"(?m)^## Status\n\nProposed\n")
        status_block = adr.replace("\r\n", "\n").split("## Status", 1)[1].split("## Context", 1)[0]
        self.assertIn("Proposed", status_block)
        self.assertNotIn("Accepted", status_block)
        self.assertIn("no model download authorized", research.lower())

    def test_no_banned_product_names_in_core_docs(self):
        for path in CORE_DOCS:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(BANNED_PRODUCT.search(text), f"banned product name in {path}")

    def test_no_false_capability_claims_in_core_docs(self):
        for path in CORE_DOCS:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(BANNED_CLAIM.search(text), f"false capability claim in {path}")

    def test_sibona_only_as_working_name(self):
        charter = (ROOT / "docs" / "SIONA_VISION_CHARTER.md").read_text(encoding="utf-8")
        plain = re.sub(r"\*+", "", charter).lower()
        self.assertIn("working name", plain)
        self.assertIn("not a separate intelligence core", plain)


if __name__ == "__main__":
    unittest.main()
