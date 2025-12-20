"""
SSN Orchestrator (Phase 3.5 – Stable Integration Core)
+ Phase 4.4 Tool Execution Integration
+ Phase 5.7 World Context Injection (OWNER-only, bounded)

Responsibilities:
- Identity verification
- Policy enforcement
- Tool execution (registry-based, explicit)
- Brain routing (single cognition authority)
- Memory integration via MemoryHub
- World context injection (OWNER only)
- Output control (full / minimal)

IMPORTANT:
- BrainRouter is the ONLY place where mode, fusion, damping occur
- Orchestrator NEVER calls FusionEngine directly
- Tools must use deps and MUST NOT create their own MemoryHub
"""

from __future__ import annotations

from typing import Optional, Dict, Any

from ssn.identity.owner_verification import verify_owner, is_samson_verified
from ssn.policy.policy_engine import PolicyEngine
from ssn.core.brain_router import BrainRouter
from ssn.memory.memory_hub import MemoryHub

# Tools
from ssn.tools.registry import ToolRegistry

# Phase 5.7
from ssn.world.world_context import WorldContextProvider, WorldContextConfig


class Orchestrator:
    """
    Phase 3.5 Stable Orchestrator

    Flow:
      identity → policy → (optional tool execution) →
      world context → brain routing → memory → output
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

        # Core systems
        self.policy = PolicyEngine()
        self.memory = MemoryHub()

        self.router = BrainRouter(
            memory_hub=self.memory,
            safety_monitor=getattr(self.policy, "safety_monitor", None),
        )

        # Tool system
        self.tools = ToolRegistry()

        # World context (optional)
        self.world_model = world_model
        self.world_context_provider = (
            world_context_provider
            or WorldContextProvider(
                WorldContextConfig(
                    max_entities=8,
                    max_events=8,
                    max_attr_keys=10,
                    include_events=True,
                )
            )
        )

    # ==========================================================
    # INTERNAL HELPERS
    # ==========================================================
    def _inject_world_context(
        self,
        *,
        role: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        OWNER-only: attach bounded world snapshot into context["world"].
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
            ctx["world"] = {
                "available": False,
                "reason": "world_context_build_failed",
            }

        return ctx

    # ==========================================================
    # CORE PIPELINE
    # ==========================================================
    def run(
        self,
        master_key: Optional[str],
        user_input: Any,
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        context = dict(context or {})

        # ------------------------------------------------------
        # 1. Identity Verification (PRODUCTION-SAFE)
        # ------------------------------------------------------
        scores = verify_owner(master_key)
        is_owner = is_samson_verified(scores)
        role = "OWNER" if is_owner else "GUEST"

        # ------------------------------------------------------
        # 2. TOOL OVERRIDE (explicit / test / system-controlled)
        # ------------------------------------------------------
        force_tool = context.get("force_tool_call")
        if isinstance(force_tool, dict):
            tool_deps = {
                "memory": self.memory,  # single memory authority
                "tools": self.tools,    # enables composed tools (research.answer)
                "role": role,           # optional convenience for composed tools
            }

            tool_result = self.tools.run(
                name=force_tool.get("name"),
                role=role,
                deps=tool_deps,
                args=force_tool.get("args", {}) or {},
            )

            # allowed means "permitted to call the tool", not "tool succeeded".
            err = getattr(tool_result, "error", None) or {}
            code = err.get("code") if isinstance(err, dict) else None

            permission_denied_codes = {
                "TOOL_NOT_FOUND",
                "TOOL_FORBIDDEN",
                "TOOL_STATE_CHANGE_FORBIDDEN",
                "RATE_LIMITED",
            }

            allowed = code not in permission_denied_codes

            if tool_result.ok:
                final_result = "TOOL_EXECUTED"
            else:
                final_result = "TOOL_BLOCKED" if not allowed else "TOOL_FAILED"

            return {
                "identity_verified": is_owner,
                "role": role,
                "allowed": allowed,
                "tool_result": {
                    "ok": tool_result.ok,
                    "tool": tool_result.tool,
                    "role": tool_result.role,
                    "data": tool_result.data,
                    "error": tool_result.error,
                },
                "final_result": final_result,
            }

        # ------------------------------------------------------
        # 3. Policy Enforcement (conversation path only)
        # ------------------------------------------------------
        allowed = self.policy.check_permission(
            role=role,
            action="interact",
        )

        if not allowed:
            return {
                "identity_verified": is_owner,
                "role": role,
                "allowed": False,
                "final_result": "BLOCKED_BY_POLICY",
                "scores": scores,
            }

        # ------------------------------------------------------
        # 4. World Context Injection (Phase 5.7)
        # ------------------------------------------------------
        context = self._inject_world_context(role=role, context=context)

        # ------------------------------------------------------
        # 5. Brain Routing (SINGLE cognition authority)
        # ------------------------------------------------------
        routed = self.router.route(
            role=role,
            user_input=user_input,
            context=context,
        )

        # ------------------------------------------------------
        # 6. Memory Integration (OWNER only)
        # ------------------------------------------------------
        if role == "OWNER":
            self.memory.log_interaction(
                role=role,
                user_input=user_input,
                brain_mode=routed.get("mode"),
                routed_engine=routed,
                fusion_result=routed.get("result", {}).get("fusion", {}),
            )

            if isinstance(user_input, str):
                self.memory.auto_index_from_text(role, user_input)

        # ------------------------------------------------------
        # 7. Output System
        # ------------------------------------------------------
        if self.output_mode == "minimal":
            fusion = routed.get("result", {}).get("fusion")
            return {
                "result": fusion.get("final_message") if isinstance(fusion, dict) else None,
                "role": role,
                "brain_mode": routed.get("mode"),
                "identity_verified": is_owner,
                "allowed": True,
            }

        return {
            "identity_verified": is_owner,
            "role": role,
            "allowed": True,
            "scores": scores,
            "brain_mode": routed.get("mode"),
            "mode_locked": routed.get("mode_locked"),
            "mode_damping": routed.get("mode_damping"),
            "routed_engine": routed,
            "world_context": {
                "attached": isinstance(context.get("world"), dict),
                "available": context.get("world", {}).get("available")
                if isinstance(context.get("world"), dict)
                else None,
            },
            "memory_summary": {
                "episodic_events": len(self.memory.recall_recent_events(100)),
                "semantic_facts": len(self.memory.recall_all_facts()),
                "profile": self.memory.recall_profile(),
            },
            "final_result": "EXECUTED",
        }

    # ==========================================================
    # PUBLIC ENTRY POINT
    # ==========================================================
    def handle_request(
        self,
        master_key: Optional[str],
        user_input: Any,
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        return self.run(master_key, user_input, context)
