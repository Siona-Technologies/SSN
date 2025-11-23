"""
SSN Brain Router (Phase 3.4 – Hybrid Fusion Brain)

Responsibilities:
- Integrates BrainModes (fast / deep / hybrid)
- Routes OWNER through full fusion brain
- Restricts GUEST to safe LLM-only mode
- Applies automatic mode switching
"""

from __future__ import annotations
from typing import Any, Dict, Optional

from ssn.core.language_engine import LanguageEngine
from ssn.core.snn_engine import SNNEngine
from ssn.core.brain_modes import BrainModes
from ssn.core.fusion_engine import FusionEngine


class BrainRouter:
    """
    Phase 3.4 Hybrid Router:
    - OWNER → full intelligence (LLM / SNN / Fusion)
    - GUEST → restricted LLM only
    - Mode-aware routing (fast, deep, hybrid)
    """

    def __init__(self):
        self.llm = LanguageEngine()
        self.snn = SNNEngine()
        self.fusion = FusionEngine()
        self.modes = BrainModes()  # full mode manager

    # ----------------------------------------------------------------------
    # MAIN ROUTER ENTRY
    # ----------------------------------------------------------------------
    def route(
        self,
        role: str,
        user_input: Any,
        context: Optional[Dict] = None
    ) -> Dict:

        # 1. Auto mode decision (updates internal state unless locked)
        auto_note = self.modes.auto_set_mode(
            role=role,
            user_input=user_input,
            context=context
        )

        current_mode = self.modes.get_mode()

        # 2. OWNER routing (full access)
        if role == "OWNER":
            return {
                "mode": current_mode,
                "mode_locked": self.modes.is_locked(),
                "auto_message": auto_note,
                "result": self._route_owner(user_input, context, current_mode)
            }

        # 3. Guest routing (restricted)
        return {
            "mode": "hybrid (restricted for GUEST)",
            "mode_locked": False,
            "auto_message": auto_note,
            "result": self._route_guest(user_input)
        }

    # ----------------------------------------------------------------------
    # OWNER ROUTER (FULL POWER)
    # ----------------------------------------------------------------------
    def _route_owner(
        self,
        user_input: Any,
        context: Optional[Dict],
        mode: str
    ) -> Dict:

        # FAST MODE → SNN dominates
        if mode == "fast":
            snn_out = self.snn.process(user_input)
            return {
                "engine": "snn-fast",
                "snn": snn_out,
                "note": "Fast Reaction Mode: SNN dominates for rapid processing."
            }

        # DEEP MODE → LLM dominates
        if mode == "deep":
            llm_out = self.llm.process(
                str(user_input),
                context=context,
                role="OWNER"
            )
            return {
                "engine": "llm-deep",
                "llm": llm_out,
                "note": "Deep Reasoning Mode: LLM dominates for structured logic."
            }

        # HYBRID MODE → Fusion Brain
        fusion_out = self.fusion.fuse(
            user_input=user_input,
            role="OWNER",
            context=context
        )
        return {
            "engine": "fusion",
            "fusion": fusion_out,
            "note": "Hybrid Intuition Mode: LLM + SNN fused."
        }

    # ----------------------------------------------------------------------
    # GUEST ROUTER (LIMITED)
    # ----------------------------------------------------------------------
    def _route_guest(self, user_input: Any) -> Dict:
        """
        Guests:
        - No SNN access
        - No Fusion Engine
        - LLM only, simplified
        """

        llm_out = self.llm.process(
            str(user_input),
            role="GUEST",
            context=None
        )

        return {
            "engine": "llm-only",
            "llm": llm_out,
            "note": "Guest mode: LLM only, fusion and SNN restricted."
        }
