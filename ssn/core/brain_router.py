"""
SSN Brain Router (Phase 3.4 – Hybrid Fusion Brain)
+ Phase 3.9 Mode Damping (internal-only, advisory)

Responsibilities:
- Integrates BrainModes (fast / deep / hybrid / sensory / language)
- Routes OWNER through full fusion brain
- Restricts GUEST to safe LLM-only mode
- Applies automatic mode switching
- Phase 3.9: damp mode switching using drift_report (reduces oscillation)
"""

from __future__ import annotations
from typing import Any, Dict, Optional

from ssn.core.language_engine import LanguageEngine
from ssn.core.snn_engine import SNNEngine
from ssn.core.brain_modes import BrainModes
from ssn.core.fusion_engine import FusionEngine

# Phase 3.9 (safe import, never break router if missing)
try:
    from ssn.core.mode_damper import ModeDamper
except Exception:
    ModeDamper = None  # type: ignore


class BrainRouter:
    """
    Phase 3.4 Hybrid Router:
    - OWNER → full intelligence (LLM / SNN / Fusion)
    - GUEST → restricted LLM only
    - Mode-aware routing (fast, deep, hybrid, sensory, language)
    - Phase 3.9: mode damping to reduce oscillations under drift
    """

    def __init__(self, memory_hub: Any = None, safety_monitor: Any = None):
        self.llm = LanguageEngine()
        self.snn = SNNEngine()

        # Pass memory_hub + safety_monitor into FusionEngine (Phase 3.8 stabilization reads these)
        self.memory_hub = memory_hub
        self.safety_monitor = safety_monitor
        self.fusion = FusionEngine(memory_hub=memory_hub, safety_monitor=safety_monitor)

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

        # Normalize context
        if context is None:
            context = {}

        # 1) Auto mode decision (updates internal state unless locked)
        auto_note = self.modes.auto_set_mode(
            role=role,
            user_input=user_input,
            context=context
        )

        current_mode = self.modes.get_mode()
        mode_damping_info: Optional[Dict[str, Any]] = None

        # 1.5) Phase 3.9 — Mode damping (OWNER only, and do not override locked mode)
        if role == "OWNER" and (not self.modes.is_locked()) and ModeDamper is not None:
            try:
                damper = ModeDamper(
                    memory_hub=getattr(self, "memory_hub", None),
                    safety_monitor=getattr(self, "safety_monitor", None),
                )
                decision = damper.damp_mode(current_mode)
                current_mode = decision.selected_mode
                mode_damping_info = {
                    "original_mode": decision.original_mode,
                    "selected_mode": decision.selected_mode,
                    "damped": decision.damped,
                    "reason": decision.reason,
                    "drift_score": decision.drift_score,
                    "drift_tags": decision.drift_tags,
                    "timestamp": decision.timestamp,
                }
            except Exception:
                # never break routing if damping fails
                mode_damping_info = {"status": "skipped"}

        # 2) OWNER routing (full access)
        if role == "OWNER":
            return {
                "mode": current_mode,
                "mode_locked": self.modes.is_locked(),
                "auto_message": auto_note,
                "mode_damping": mode_damping_info,  # traceability (may be None)
                "result": self._route_owner(user_input, context, current_mode)
            }

        # 3) Guest routing (restricted)
        return {
            "mode": "hybrid (restricted for GUEST)",
            "mode_locked": False,
            "auto_message": auto_note,
            "mode_damping": None,
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

        # HYBRID / SENSORY / LANGUAGE / DEFAULT → Fusion Brain (mode-aware)
        fusion_out = self.fusion.fuse(
            user_input=user_input,
            role="OWNER",
            context=context,
            mode=mode,  # important: honor BrainModes if it returns sensory/language/hybrid
        )
        return {
            "engine": "fusion",
            "fusion": fusion_out,
            "note": "Hybrid Intuition Mode: LLM + SNN fused (mode-aware)."
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
