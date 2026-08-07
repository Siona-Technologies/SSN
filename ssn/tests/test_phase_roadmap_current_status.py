"""Current phase-roadmap consistency after governed Phase 5 planning."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROADMAP = ROOT / "docs" / "SIONA_PHASE_ROADMAP.md"
STATUS = ROOT / "docs" / "PHASE_STATUS.md"
ADR3 = ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md"
ADR4 = ROOT / "docs" / "adr" / "0004-learned-neuromorphic-backend-strategy.md"
ADR5 = ROOT / "docs" / "adr" / "0005-stateful-streaming-neuromorphic-strategy.md"
ACCEPT4 = ROOT / "docs" / "PHASE_4_ACCEPTANCE.md"
PLAN5 = ROOT / "docs" / "PHASE_5_PLANNING_ACCEPTANCE.md"


class TestPhaseRoadmapCurrentStatus(unittest.TestCase):
    def test_current_phase_sequence_matches_accepted_governance(self):
        roadmap = ROADMAP.read_text(encoding="utf-8")
        status = STATUS.read_text(encoding="utf-8")
        adr3 = ADR3.read_text(encoding="utf-8")
        adr4 = ADR4.read_text(encoding="utf-8")
        adr5 = ADR5.read_text(encoding="utf-8")
        acceptance4 = ACCEPT4.read_text(encoding="utf-8")
        planning5 = PLAN5.read_text(encoding="utf-8")

        self.assertIn("## Phase 3 — Local model and evaluation layer", roadmap)
        self.assertIn("ADR 0003 is **Accepted (Phase 3B)**", roadmap)
        self.assertIn("## Phase 4 — Learned neuromorphic backend", roadmap)
        self.assertIn("ADR 0004 — **Accepted (Phase 4)**", roadmap)
        self.assertIn("## Phase 5 — Stateful streaming neuromorphic runtime", roadmap)
        self.assertIn("**Planning accepted; implementation not started.**", roadmap)
        self.assertIn("Phase 5A authorized now", roadmap)

        self.assertIn("Phase 3 | **Completed", status)
        self.assertIn("Phase 4 | **Completed and accepted", status)
        self.assertIn("ADR 0004 **Accepted (Phase 4)**", status)
        self.assertIn("Phase 5 | **Planning accepted", status)
        self.assertIn("ADR 0005 **Proposed**", status)

        leading_status3 = adr3.replace("\r\n", "\n").split("## Status", 1)[1].split("## Context", 1)[0]
        self.assertIn("Accepted (Phase 3B)", leading_status3)
        leading_status4 = adr4.replace("\r\n", "\n").split("## Status", 1)[1].split("## Context", 1)[0]
        self.assertIn("Accepted (Phase 4)", leading_status4)
        leading_status5 = adr5.replace("\r\n", "\n").split("## Status", 1)[1].split("## Context", 1)[0]
        self.assertRegex(leading_status5, r"(?m)^\s*Proposed\s*$")

        # Historical Phase 4 closeout remains immutable even after Phase 5 is selected.
        self.assertIn("**Phase 4 is COMPLETE**", acceptance4)
        self.assertIn("No subsequent phase starts automatically", acceptance4)
        self.assertIn("At the Phase 4 closeout boundary", roadmap)
        self.assertIn("separate\ngoverned planning decision", roadmap)
        self.assertIn("**Status:** Accepted planning gate", planning5)

    def test_phase_numbering_is_not_silently_inherited_from_legacy_plans(self):
        roadmap = ROADMAP.read_text(encoding="utf-8")
        lower_plain = re.sub(r"\*+", "", roadmap).lower()
        self.assertIn("siona_build_plan.md", lower_plain)
        self.assertIn("do not define current phase 5 authorization", lower_plain)
        self.assertIn("historical phase5", lower_plain)
        self.assertIn("stateful streaming neuromorphic", lower_plain)


if __name__ == "__main__":
    unittest.main()
