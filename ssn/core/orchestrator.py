"""
SSN Orchestrator (Phase 3.5 – Full Memory Architecture)

Responsibilities:
- Identity verification (MasterKey + weak biosignals)
- Role assignment (OWNER / GUEST)
- Law enforcement (PolicyEngine)
- Brain routing (BrainRouter)
- Brain modes (ModeManager)
- Hybrid cognition (FusionEngine)
- Memory integration (MemoryHub):
    • episodic logging
    • semantic storage
    • personal profile updates
- Output control (full / minimal)
"""

from __future__ import annotations
from typing import Optional, Dict, Any

from ssn.identity.owner_verification import verify_owner, is_samson_verified
from ssn.policy.policy_engine import PolicyEngine
from ssn.core.brain_router import BrainRouter
from ssn.core.brain_modes import ModeManager
from ssn.core.fusion_engine import FusionEngine
from ssn.memory.memory_hub import MemoryHub


class Orchestrator:
    """
    Phase 3.5 hybrid orchestrator that merges:
    identity → policy → cognition → fusion → memory
    """

    def __init__(self, output_mode: str = "full"):
        if output_mode not in ("full", "minimal"):
            raise ValueError("output_mode must be 'full' or 'minimal'.")

        self.output_mode = output_mode

        # Core cognition systems
        self.policy = PolicyEngine()
        self.router = BrainRouter()
        self.modes = ModeManager()
        self.fusion = FusionEngine()

        # Memory System
        self.memory = MemoryHub()

    # ==================================================================
    # INTERNAL EXECUTION PIPELINE
    # ==================================================================
    def run(self, master_key: Optional[str], user_input: Any, context: Dict = None) -> Dict:
        context = context or {}

        # --------------------------------------------------------------
        # 1. Identity Verification
        # --------------------------------------------------------------
        scores = verify_owner(master_key)
        is_owner = is_samson_verified(scores)
        role = "OWNER" if is_owner else "GUEST"

        # --------------------------------------------------------------
        # 2. Law Enforcement
        # --------------------------------------------------------------
        allowed = self.policy.check_permission(role=role, action="interact")
        if not allowed:
            return {
                "identity_verified": is_owner,
                "role": role,
                "allowed": False,
                "final_result": "BLOCKED_BY_POLICY",
                "scores": scores,
            }

        # --------------------------------------------------------------
        # 3. Brain Mode Selection (auto)
        # --------------------------------------------------------------
        mode_message = self.modes.auto_set_mode(
            role=role,
            user_input=user_input,
            context=context,
        )
        current_mode = self.modes.get_mode()

        # --------------------------------------------------------------
        # 4. Brain Routing (LLM/SNN)
        # --------------------------------------------------------------
        routed = self.router.route(role, user_input, context)

        # --------------------------------------------------------------
        # 5. Hybrid Fusion Output (LLM + SNN)
        # --------------------------------------------------------------
        fusion = self.fusion.fuse(
            user_input,
            role=role,
            mode=current_mode,
            context=context,
        )

        # --------------------------------------------------------------
        # 6. MEMORY UPDATE PIPELINE (OWNER ONLY)
        # --------------------------------------------------------------
        if role == "OWNER":

            # 6.1 Episodic Memory
            self.memory.episodic.add_event(
                event_type="interaction",
                actor="Samson",
                details={
                    "input": str(user_input),
                    "mode": current_mode,
                    "fusion_score": fusion["fusion_score"],
                }
            )

            # 6.2 Semantic Memory (store last input)
            self.memory.semantic.store_fact(
                key="last_user_input",
                value=str(user_input)
            )

            # 6.3 Personal profile
            if isinstance(user_input, str):
                self.memory.profile.update_preferences(
                    {"last_sentence": user_input}
                )

            # 6.4 Auto-index text for semantic memory
            if isinstance(user_input, str):
                self.memory.auto_index_from_text(role, user_input)

            # (Phase 3.6 — cognitive trace will be added later)

        # --------------------------------------------------------------
        # 7. OUTPUT SYSTEM (minimal/full)
        # --------------------------------------------------------------
        if self.output_mode == "minimal":
            return {
                "result": fusion["final_message"],
                "role": role,
                "brain_mode": current_mode,
                "identity_verified": is_owner,
                "allowed": True,
            }

        # FULL INTROSPECTION OUTPUT
        return {
            "identity_verified": is_owner,
            "role": role,
            "allowed": True,
            "scores": scores,

            "brain_mode": current_mode,
            "mode_locked": self.modes.is_locked(),
            "mode_message": mode_message,

            "routed_engine": routed,
            "fusion_engine": fusion,

            "memory_summary": {
                "episodic_events": len(self.memory.episodic.get_all_events()),
                "semantic_facts": len(self.memory.semantic.list_facts()),
                "profile": self.memory.profile.get_profile(),
            },

            "final_result": "EXECUTED",
        }

    # ==================================================================
    # PUBLIC ENTRY POINT
    # ==================================================================
    def handle_request(self, master_key: Optional[str], user_input: Any, context: Dict = None):
        return self.run(master_key, user_input, context)
