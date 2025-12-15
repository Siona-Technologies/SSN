"""
SSN Orchestrator (Phase 3.5 – Full Memory Architecture, Phase 5.7 World Context)

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
- World context injection (Phase 5.7):
    • OWNER-only bounded/redacted world snapshot added to context["world"]
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

# Phase 5.7
from ssn.world.world_context import WorldContextProvider, WorldContextConfig


class Orchestrator:
    """
    Phase 3.5 hybrid orchestrator that merges:
    identity → policy → cognition → fusion → memory

    Phase 5.7 adds:
    world_model → bounded snapshot → context["world"] (OWNER only)
    """

    def __init__(
        self,
        output_mode: str = "full",
        *,
        world_model: Optional[Any] = None,
        world_context_provider: Optional[WorldContextProvider] = None,
    ):
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

        # World Model (optional)
        self.world_model = world_model
        self.world_context_provider = world_context_provider or WorldContextProvider(
            WorldContextConfig(
                max_entities=8,
                max_events=8,
                max_attr_keys=10,
                include_events=True,
            )
        )

    # ==================================================================
    # INTERNAL HELPERS
    # ==================================================================
    def _inject_world_context(self, *, role: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        OWNER-only: attach a bounded/redacted world snapshot into context["world"].

        - Never blocks cognition if world model/provider fails
        - Never overwrites context["world"] if caller already supplied it
        """
        ctx = dict(context or {})

        if role != "OWNER":
            return ctx

        if self.world_model is None:
            return ctx

        if "world" in ctx:
            return ctx

        try:
            ctx["world"] = self.world_context_provider.build(self.world_model)
        except Exception:
            ctx["world"] = {"available": False, "reason": "world_context_build_failed"}

        return ctx

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
        # 2. World Context Injection (Phase 5.7) — OWNER only
        # --------------------------------------------------------------
        context = self._inject_world_context(role=role, context=context)

        # --------------------------------------------------------------
        # 3. Law Enforcement
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
        # 4. Brain Mode Selection (auto)
        # --------------------------------------------------------------
        mode_message = self.modes.auto_set_mode(
            role=role,
            user_input=user_input,
            context=context,
        )
        current_mode = self.modes.get_mode()

        # --------------------------------------------------------------
        # 5. Brain Routing (LLM/SNN)
        # --------------------------------------------------------------
        routed = self.router.route(role, user_input, context)

        # --------------------------------------------------------------
        # 6. Hybrid Fusion Output (LLM + SNN)
        # --------------------------------------------------------------
        fusion = self.fusion.fuse(
            user_input,
            role=role,
            mode=current_mode,
            context=context,
        )

        # --------------------------------------------------------------
        # 7. MEMORY UPDATE PIPELINE (OWNER ONLY)
        # --------------------------------------------------------------
        if role == "OWNER":

            # 7.1 Episodic Memory
            self.memory.episodic.add_event(
                event_type="interaction",
                actor="Samson",
                details={
                    "input": str(user_input),
                    "mode": current_mode,
                    "fusion_score": fusion.get("fusion_score"),
                }
            )

            # 7.2 Semantic Memory (store last input)
            self.memory.semantic.store_fact(
                key="last_user_input",
                value=str(user_input)
            )

            # 7.3 Personal profile
            if isinstance(user_input, str):
                self.memory.profile.update_preferences(
                    {"last_sentence": user_input}
                )

            # 7.4 Auto-index text for semantic memory
            if isinstance(user_input, str):
                self.memory.auto_index_from_text(role, user_input)

        # --------------------------------------------------------------
        # 8. OUTPUT SYSTEM (minimal/full)
        # --------------------------------------------------------------
        if self.output_mode == "minimal":
            return {
                "result": fusion.get("final_message"),
                "role": role,
                "brain_mode": current_mode,
                "identity_verified": is_owner,
                "allowed": True,
            }

        # FULL INTROSPECTION OUTPUT
        world_block = None
        if isinstance(context, dict) and "world" in context and isinstance(context.get("world"), dict):
            world_block = {
                "attached": True,
                "available": context["world"].get("available"),
                "entity_count": context["world"].get("entity_count"),
            }
        else:
            world_block = {"attached": False, "available": None, "entity_count": None}

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

            "world_context": world_block,

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
