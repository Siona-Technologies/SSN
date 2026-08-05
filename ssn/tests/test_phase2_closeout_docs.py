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
        self.assertIn("5f0d3ae", text)
        self.assertNotIn("Final branch tip", text)
        self.assertIn("Specified but not started", text)
        self.assertIn("SIONA_VISION_CHARTER.md", text)
        self.assertIn("PHASE_2_ACCEPTANCE.md", text)
        self.assertIn("PHASE_3_ENGINEERING_SPEC.md", text)

    def test_phase3_spec_not_started(self):
        text = (ROOT / "docs" / "PHASE_3_ENGINEERING_SPEC.md").read_text(encoding="utf-8")
        self.assertIn("not started", text.lower())
        self.assertIn("feat/siona-local-model-evals-v3", text)
        self.assertIn("Do not create that branch", text)

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
