"""Current phase-roadmap consistency after Phase 3 closeout and Phase 4 planning."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROADMAP = ROOT / "docs" / "SIONA_PHASE_ROADMAP.md"
STATUS = ROOT / "docs" / "PHASE_STATUS.md"
ADR3 = ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md"
ADR4 = ROOT / "docs" / "adr" / "0004-learned-neuromorphic-backend-strategy.md"


class TestPhaseRoadmapCurrentStatus(unittest.TestCase):
    def test_current_phase_sequence_matches_accepted_governance(self):
        roadmap = ROADMAP.read_text(encoding="utf-8")
        status = STATUS.read_text(encoding="utf-8")
        adr3 = ADR3.read_text(encoding="utf-8")
        adr4 = ADR4.read_text(encoding="utf-8")

        self.assertIn("## Phase 3 — Local model and evaluation layer", roadmap)
        self.assertIn("**Completed and accepted.**", roadmap)
        self.assertIn("ADR 0003 — **Accepted (Phase 3B)**", roadmap)
        self.assertIn("Phase 3 is complete", roadmap)

        self.assertIn("## Phase 4 — Learned neuromorphic backend", roadmap)
        self.assertIn(
            "**Planning gate accepted; EXP-4-003 training verified; EXP-4-004 learned provider integrated + parity verified; breadth/safety gate pending.**",
            roadmap,
        )
        self.assertIn("Completed through EXP-4-004", roadmap)
        self.assertIn("learned provider + fallback/parity", roadmap)
        self.assertIn("SIONA_BUILD_PLAN.md", roadmap)
        self.assertIn("dated planning reference", roadmap)

        self.assertNotIn("Phase 3 — Local model and evaluation layer\n\n**Specified but not started.**", roadmap)
        self.assertNotIn("Recommended future branch (do not create until Phase 3 is authorized)", roadmap)

        self.assertIn("Phase 3 | **Completed", status)
        self.assertIn("Phase 3B | **Completed and accepted", status)
        self.assertIn("Phase 4 | **In progress", status)
        self.assertIn("EXP-4-004 learned provider integrated + parity VERIFIED", status)
        self.assertIn("ADR 0004 **Proposed**", status)

        leading_status3 = adr3.replace("\r\n", "\n").split("## Status", 1)[1].split(
            "## Context", 1
        )[0]
        self.assertIn("Accepted (Phase 3B)", leading_status3)

        leading_status4 = adr4.replace("\r\n", "\n").split("## Status", 1)[1].split(
            "## Context", 1
        )[0]
        self.assertRegex(leading_status4, r"(?m)^\s*Proposed\s*$")

    def test_phase4_is_not_silently_defined_by_legacy_numbering(self):
        roadmap = ROADMAP.read_text(encoding="utf-8")
        lower_plain = re.sub(r"\*+", "", roadmap).lower()
        self.assertIn("must not be treated as the current phase 4\nauthorization", lower_plain)
        self.assertIn("not part of the accepted\nphase 4 learned-neuromorphic scope", lower_plain)
        self.assertIn("learned neuromorphic", lower_plain)


if __name__ == "__main__":
    unittest.main()
