"""
SSN Brain Modes (Phase 3.3)

This module manages SSN's cognitive modes:

- deep    -> Deep Reasoning Mode (slow, careful, logical)
- fast    -> Fast Reaction Mode (quick, SNN-heavy)
- hybrid  -> Hybrid Intuition Mode (balanced, default)

Features:
- Automatic mode selection based on input + role
- Manual override by Samson
- Lock to prevent auto-switching
- Personality-rich confirmation messages
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Any, Dict, Literal

BrainMode = Literal["deep", "fast", "hybrid"]


@dataclass
class BrainModeState:
    current_mode: BrainMode = "hybrid"
    locked: bool = False
    last_auto_reason: str = "initial_default"


class ModeManager:
    """
    Controls SSN's brain mode.

    - auto_select_mode(...) decides which mode is best
    - manual_set_mode(...) lets Samson override
    - lock_mode(...) prevents auto changes (but still allows manual changes)
    - describe_mode_change(...) returns personality-rich confirmations
    """

    def __init__(self, default_mode: BrainMode = "hybrid"):
        self.state = BrainModeState(current_mode=default_mode)

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------
    def get_mode(self) -> BrainMode:
        return self.state.current_mode

    def is_locked(self) -> bool:
        return self.state.locked

    def lock_mode(self, locked: bool) -> str:
        self.state.locked = locked
        if locked:
            return (
                "🛡️ Mode lock enabled. I'll stay in the current brain mode until "
                "you tell me otherwise, Samson."
            )
        else:
            return (
                "🔓 Mode lock disabled. I can now adapt my brain mode automatically "
                "based on what you ask me."
            )

    def manual_set_mode(self, mode: BrainMode, role: str = "OWNER") -> str:
        old_mode = self.state.current_mode
        self.state.current_mode = mode
        self.state.last_auto_reason = "manual_override"

        return self._describe_mode_change(
            old_mode=old_mode,
            new_mode=mode,
            reason="manual_override",
            role=role,
            manual=True,
        )

    # --------------------------------------------------
    # Automatic Mode Selection
    # --------------------------------------------------
    def auto_select_mode(
        self,
        role: str,
        user_input: Any,
        context: Optional[Dict] = None,
    ) -> BrainMode:

        context = context or {}

        if role != "OWNER":
            return "hybrid"

        if isinstance(user_input, (int, float, bytes, list, dict)):
            return "fast"

        if isinstance(user_input, str):
            text = user_input.strip().lower()
            length = len(text)

            deep_keywords = [
                "explain", "analyze", "analysis", "why", "design",
                "architecture", "research", "derive", "prove", "plan",
            ]

            fast_keywords = [
                "quick", "fast", "alert", "danger", "emergency",
                "urgent", "monitor", "watch",
            ]

            if any(k in text for k in deep_keywords) or length > 300:
                return "deep"

            if any(k in text for k in fast_keywords) or length < 40:
                return "fast"

            return "hybrid"

        return "hybrid"

    def auto_set_mode(
        self,
        role: str,
        user_input: Any,
        context: Optional[Dict] = None,
    ) -> Optional[str]:

        if self.state.locked:
            return None

        new_mode = self.auto_select_mode(role, user_input, context)
        old_mode = self.state.current_mode

        if new_mode == old_mode:
            return None

        self.state.current_mode = new_mode
        self.state.last_auto_reason = "auto"

        return self._describe_mode_change(
            old_mode=old_mode,
            new_mode=new_mode,
            reason="auto",
            role=role,
            manual=False,
        )

    # --------------------------------------------------
    # Personality Messages
    # --------------------------------------------------
    def _describe_mode_change(
        self,
        old_mode: BrainMode,
        new_mode: BrainMode,
        reason: str,
        role: str,
        manual: bool,
    ) -> str:

        if role != "OWNER":
            return f"Brain mode switched to '{new_mode}' (restricted guest behavior)."

        if new_mode == "deep":
            return (
                "🧠 Deep Reasoning Mode engaged, Samson. "
                "I'll explore your request with maximum precision and structure."
                if manual else
                "🧠 Shifting into Deep Reasoning Mode. This needs careful thought."
            )

        if new_mode == "fast":
            return (
                "⚡ Fast Reaction Mode enabled — prioritizing quick instincts."
                if manual else
                "⚡ Switching to Fast Reaction Mode — this looks urgent."
            )

        return (
            "🔮 Hybrid Intuition Mode activated — balanced and adaptive."
            if manual else
            "🔮 Moving into Hybrid Intuition Mode — balanced natural thinking."
        )


# ============================================================
# ALIAS FOR COMPATIBILITY WITH ROUTER & ORCHESTRATOR
# ============================================================
class BrainModes(ModeManager):
    """
    Thin wrapper so other modules can import BrainModes
    without breaking anything.

    BrainModes is now just an alias for ModeManager.
    """
    pass
