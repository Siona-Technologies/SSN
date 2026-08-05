from __future__ import annotations

from typing import Any, Dict, Optional
import time

from ssn.core.language_engine import LanguageEngine
from ssn.core.snn_engine import SNNEngine
from ssn.core.brain_modes import BrainModes
from ssn.core.fusion_engine import FusionEngine

# Phase 3.9 (safe import)
try:
    from ssn.core.mode_damper import ModeDamper
except Exception:
    ModeDamper = None  # type: ignore


class BrainRouter:
    """
    Phase 3.4 Hybrid Router
    + Phase 3.9 Mode Damping (advisory, internal-only)
    """

    def __init__(self, memory_hub: Any = None, safety_monitor: Any = None):
        self.llm = LanguageEngine()
        self.snn = SNNEngine()

        self.memory_hub = memory_hub
        self.safety_monitor = safety_monitor

        self.fusion = FusionEngine(
            memory_hub=memory_hub,
            safety_monitor=safety_monitor,
        )

        self.modes = BrainModes()

    # ------------------------------------------------------------
    # INTERNAL TRACE WRITER (NEW)
    # ------------------------------------------------------------
    def _write_trace(self, payload: Dict[str, Any]) -> None:
        """
        Writes a router-level trace for drift & stabilization analysis.
        """
        write_fn = getattr(self.memory_hub, "write_trace", None)
        if callable(write_fn):
            try:
                write_fn(
                    {
                        "type": "router_decision",
                        "timestamp": time.time(),
                        **payload,
                    }
                )
            except Exception:
                pass

    # ------------------------------------------------------------
    # MAIN ROUTER ENTRY
    # ------------------------------------------------------------
    def route(
        self,
        role: str,
        user_input: Any,
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:

        ctx = dict(context) if isinstance(context, dict) else {}

        # 1) Automatic mode selection
        auto_note = self.modes.auto_set_mode(
            role=role,
            user_input=user_input,
            context=ctx,
        )

        current_mode = self.modes.get_mode()
        mode_locked = self.modes.is_locked()
        mode_damping_info: Optional[Dict[str, Any]] = None

        # 1.5) Phase 3.9 — Mode damping (OWNER only)
        if role == "OWNER" and not mode_locked and ModeDamper is not None:
            try:
                damper = ModeDamper(
                    memory_hub=self.memory_hub,
                    safety_monitor=self.safety_monitor,
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
                }
            except Exception:
                mode_damping_info = {
                    "status": "skipped",
                    "reason": "exception_during_damping",
                }

        # --------------------------------------------------------
        # OWNER routing
        # --------------------------------------------------------
        if role == "OWNER":
            result = self._route_owner(
                user_input=user_input,
                context=ctx,
                mode=current_mode,
            )

            # 🔹 TRACE WRITE (CRITICAL)
            self._write_trace(
                {
                    "role": "OWNER",
                    "mode": current_mode,
                    "mode_locked": mode_locked,
                    "mode_damping": mode_damping_info,
                    "engine": result.get("engine"),
                }
            )

            out = {
                "role": "OWNER",
                "mode": current_mode,
                "mode_locked": mode_locked,
                "auto_message": auto_note,
                "mode_damping": mode_damping_info,
                "result": result,
            }
            observer = getattr(self, "integration_observer", None)
            if callable(observer):
                try:
                    observer(
                        {
                            "role": "OWNER",
                            "mode": current_mode,
                            "note": result.get("note"),
                            "engine": result.get("engine"),
                        }
                    )
                except Exception:
                    pass
            return out

        # --------------------------------------------------------
        # GUEST routing
        # --------------------------------------------------------
        guest_result = self._route_guest(user_input)
        guest_out = {
            "role": "GUEST",
            "mode": "hybrid (restricted)",
            "mode_locked": False,
            "auto_message": auto_note,
            "mode_damping": None,
            "result": guest_result,
        }
        observer = getattr(self, "integration_observer", None)
        if callable(observer):
            try:
                observer(
                    {
                        "role": "GUEST",
                        "mode": "hybrid (restricted)",
                        "note": guest_result.get("note"),
                        "engine": guest_result.get("engine"),
                    }
                )
            except Exception:
                pass
        return guest_out

    # ------------------------------------------------------------
    # OWNER ROUTING
    # ------------------------------------------------------------
    def _route_owner(
        self,
        user_input: Any,
        context: Dict[str, Any],
        mode: str,
    ) -> Dict[str, Any]:

        if mode == "fast":
            return {
                "engine": "snn-fast",
                "snn": self.snn.process(user_input),
                "note": "Fast Reaction Mode: SNN dominates.",
            }

        if mode == "deep":
            return {
                "engine": "llm-deep",
                "llm": self.llm.process(
                    str(user_input),
                    context=context,
                    role="OWNER",
                ),
                "note": "Deep Reasoning Mode: LLM dominates.",
            }

        fusion_out = self.fusion.fuse(
            user_input=user_input,
            role="OWNER",
            context=context,
            mode=mode,
        )

        return {
            "engine": "fusion",
            "fusion": fusion_out,
            "note": "Hybrid cognition: LLM + SNN (mode-aware).",
        }

    # ------------------------------------------------------------
    # GUEST ROUTING
    # ------------------------------------------------------------
    def _route_guest(self, user_input: Any) -> Dict[str, Any]:
        return {
            "engine": "llm-only",
            "llm": self.llm.process(
                str(user_input),
                role="GUEST",
                context=None,
            ),
            "note": "Guest mode: restricted LLM only.",
        }
