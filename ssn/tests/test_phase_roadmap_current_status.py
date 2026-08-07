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
ACCEPT4 = ROOT / "docs" / "PHASE_4_ACCEPTANCE.md"


class TestPhaseRoadmapCurrentStatus(unittest.TestCase):
    def test_current_phase_sequence_matches_accepted_governance(self):
        roadmap = ROADMAP.read_text(encoding="utf-8")
        status = STATUS.read_text(encoding="utf-8")
        adr3 = ADR3.read_text(encoding="utf-8")
        adr4 = ADR4.read_text(encoding="utf-8")
        acceptance4 = ACCEPT4.read_text(encoding="utf-8")

        self.assertIn("## Phase 3 — Local model and evaluation layer", roadmap)
        self.assertIn("**Completed and accepted.**", roadmap)
        self.assertIn("ADR 0003 is **Accepted (Phase 3B)**", roadmap)

        self.assertIn("## Phase 4 — Learned neuromorphic backend", roadmap)
        self.assertIn("EXP-4-003", roadmap)
        self.assertIn("EXP-4-004", roadmap)
        self.assertIn("EXP-4-005", roadmap)
        self.assertIn("ADR 0004 — **Accepted (Phase 4)**", roadmap)
        self.assertIn("Phase 4 is complete", roadmap)
        self.assertIn("## Next phase — not selected", roadmap)
        self.assertIn("No next phase has started", roadmap)

        self.assertIn("Phase 3 | **Completed", status)
        self.assertIn("Phase 3B | **Completed and accepted", status)
        self.assertIn("Phase 4 | **Completed and accepted", status)
        self.assertIn("ADR 0004 **Accepted (Phase 4)**", status)
        self.assertIn("Next phase | **Not started", status)

        leading_status3 = adr3.replace("\r\n", "\n").split("## Status", 1)[1].split(
            "## Context", 1
        )[0]
        self.assertIn("Accepted (Phase 3B)", leading_status3)

        leading_status4 = adr4.replace("\r\n", "\n").split("## Status", 1)[1].split(
            "## Context", 1
        )[0]
        self.assertIn("Accepted (Phase 4)", leading_status4)
        self.assertNotRegex(leading_status4, r"(?m)^\s*Proposed\s*$")

        self.assertIn("**Phase 4 is COMPLETE**", acceptance4)
        self.assertIn("No subsequent phase starts automatically", acceptance4)

    def test_phase_numbering_is_not_silently_inherited_from_legacy_plans(self):
        roadmap = ROADMAP.read_text(encoding="utf-8")
        lower_plain = re.sub(r"\*+", "", roadmap).lower()
        self.assertIn("siona_build_plan.md", lower_plain)
        self.assertIn("must not be treated as current authorization", lower_plain)
        self.assertIn("no next phase has started", lower_plain)
        self.assertIn("separate governed planning decision", lower_plain)


if __name__ == "__main__":
    unittest.main()
