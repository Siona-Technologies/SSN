"""Current phase-roadmap consistency after Phase 3 closeout."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROADMAP = ROOT / "docs" / "SIONA_PHASE_ROADMAP.md"
STATUS = ROOT / "docs" / "PHASE_STATUS.md"
ADR = ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md"


class TestPhaseRoadmapCurrentStatus(unittest.TestCase):
    def test_current_phase_sequence_matches_accepted_governance(self):
        roadmap = ROADMAP.read_text(encoding="utf-8")
        status = STATUS.read_text(encoding="utf-8")
        adr = ADR.read_text(encoding="utf-8")

        self.assertIn("## Phase 3 — Local model and evaluation layer", roadmap)
        self.assertIn("**Completed and accepted.**", roadmap)
        self.assertIn("ADR 0003 — **Accepted (Phase 3B)**", roadmap)
        self.assertIn("Phase 3 is complete", roadmap)
        self.assertIn("## Phase 4 — Planning boundary", roadmap)
        self.assertIn("**Not started.**", roadmap)
        self.assertIn("Phase 4 remains NOT STARTED", roadmap)
        self.assertIn("SIONA_BUILD_PLAN.md", roadmap)
        self.assertIn("dated planning reference", roadmap)

        self.assertNotIn("Phase 3 — Local model and evaluation layer\n\n**Specified but not started.**", roadmap)
        self.assertNotIn("Recommended future branch (do not create until Phase 3 is authorized)", roadmap)

        self.assertIn("Phase 3 | **Completed", status)
        self.assertIn("Phase 3B | **Completed and accepted", status)
        self.assertIn("Phase 4 | **Not started", status)

        leading_status = adr.replace("\r\n", "\n").split("## Status", 1)[1].split(
            "## Context", 1
        )[0]
        self.assertIn("Accepted (Phase 3B)", leading_status)

    def test_phase4_is_not_silently_defined_by_legacy_numbering(self):
        roadmap = ROADMAP.read_text(encoding="utf-8")
        lower = roadmap.lower()
        self.assertIn("must not be treated as the current\nphase 4 authorization", lower)
        self.assertIn("unsequenced until phase 4 planning", lower)
        self.assertIn("separate governed planning", lower)


if __name__ == "__main__":
    unittest.main()
