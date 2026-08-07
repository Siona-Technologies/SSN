"""Current phase-roadmap consistency after Phase 4 closeout."""

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
        self.assertIn("ADR 0003 — **Accepted (Phase 3B)**", roadmap)
        self.assertIn("Phase 3 is complete", roadmap)

        self.assertIn("## Phase 4 — Learned neuromorphic backend", roadmap)
        self.assertIn("**Completed and accepted.**", roadmap)
        self.assertIn("EXP-4-003", roadmap)
        self.assertIn("EXP-4-004", roadmap)
        self.assertIn("EXP-4-005", roadmap)
        self.assertIn("ADR 0004 — **Accepted (Phase 4)**", roadmap)

        self.assertIn("## Phase 5 — Planning boundary", roadmap)
        self.assertIn("**Not started.**", roadmap)
        self.assertIn("Phase 5 remains NOT STARTED", roadmap)
        self.assertIn("SIONA_BUILD_PLAN.md", roadmap)
        self.assertIn("dated planning reference", roadmap)

        self.assertIn("Phase 3 | **Completed", status)
        self.assertIn("Phase 4 | **Completed and accepted", status)
        self.assertIn("Phase 5 | **Not started", status)
        self.assertIn("ADR 0004 **Accepted (Phase 4)**", status)

        leading_status3 = adr3.replace("\r\n", "\n").split("## Status", 1)[1].split(
            "## Context", 1
        )[0]
        self.assertIn("Accepted (Phase 3B)", leading_status3)

        leading_status4 = adr4.replace("\r\n", "\n").split("## Status", 1)[1].split(
            "## Context", 1
        )[0]
        self.assertIn("Accepted (Phase 4)", leading_status4)

    def test_future_scope_is_not_silently_defined_by_legacy_numbering(self):
        roadmap = ROADMAP.read_text(encoding="utf-8")
        lower_plain = re.sub(r"\*+", "", roadmap).lower()
        self.assertIn("older\nphase labels must not be treated as current authorization", lower_plain)
        self.assertIn("phase 5 remains not started", lower_plain)
        self.assertIn("none of these is automatically phase 5", lower_plain)


if __name__ == "__main__":
    unittest.main()
