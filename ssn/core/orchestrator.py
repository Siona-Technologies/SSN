# ssn/core/orchestrator.py

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

from typing import Optional, Dict, Any, Tuple

from ssn.identity.owner_verification import verify_owner, is_samson_verified
from ssn.policy.policy_engine import PolicyEngine
from ssn.core.brain_router import BrainRouter
from ssn.memory.memory_hub import MemoryHub
from ssn.tools.registry import ToolRegistry
from ssn.world.world_context import WorldContextProvider, WorldContextConfig


_PERMISSION_DENIED_CODES = {
    "TOOL_NOT_FOUND",
    "TOOL_FORBIDDEN",
    "TOOL_STATE_CHANGE_FORBIDDEN",
    "RATE_LIMITED",
}


def _is_owner(role: str) -> bool:
    return (role or "").upper().strip() == "OWNER"


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

        # Core systems (canonical names)
        self.policy = PolicyEngine()
        self.memory = MemoryHub()
        self.router = BrainRouter(
            memory_hub=self.memory,
            safety_monitor=getattr(self.policy, "safety_monitor", None),
        )

        # Tools (canonical)
        self.tools = ToolRegistry()

        # World (optional)
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

        # ------------------------------------------------------
        # Compatibility aliases (prevents split-brain)
        # Many handlers/builders look for these attribute names.
        # ------------------------------------------------------
        self.memory_hub = self.memory
        self.policy_engine = self.policy
        self.brain_router = self.router

        # Optional slots for later phases (wired by runtime_builder when present)
        self.perception_hub = getattr(self, "perception_hub", None)
        self.suggestion_engine = getattr(self, "suggestion_engine", None)
        self.safety_monitor = getattr(self.policy, "safety_monitor", None)

    # ==========================================================
    # IDENTITY / POLICY HELPERS
    # ==========================================================
    def resolve_identity(self, master_key: Optional[str]) -> Tuple[bool, str, Any]:
        """
        Returns: (is_owner: bool, role: str, scores: Any)
        """
        scores = verify_owner(master_key)
        is_owner = is_samson_verified(scores)
        role = "OWNER" if is_owner else "GUEST"
        return is_owner, role, scores

    def _policy_action_for_role(self, role: str) -> str:
        """
        Keep policy logic unchanged:
          - OWNER uses "interact"
          - NON-OWNER uses a basic allowed action in your policy: "ask_question"
        """
        return "interact" if _is_owner(role) else "ask_question"

    # ==========================================================
    # TOOL HELPERS
    # ==========================================================
    def _build_tool_deps(self, *, role: str) -> Dict[str, Any]:
        """
        Single, canonical deps bundle passed to ToolRegistry handlers.
        This prevents tools/handlers from constructing parallel MemoryHub/registries.
        """
        deps: Dict[str, Any] = {
            # Canonical anchors
            "orchestrator": self,
            "role": role,

            # Shared instances
            "tool_registry": self.tools,
            "tools": self.tools,

            "memory_hub": self.memory,
            "memory": self.memory,

            "policy_engine": self.policy,
            "policy": self.policy,

            # World
            "world_model": self.world_model,
            "world_context_provider": self.world_context_provider,

            # Optional systems (may be None)
            "perception_hub": getattr(self, "perception_hub", None),
            "suggestion_engine": getattr(self, "suggestion_engine", None),
            "safety_monitor": getattr(self.policy, "safety_monitor", None),
        }
        return deps

    def call_tool(
        self,
        *,
        name: str,
        role: str,
        args: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Single canonical tool execution entrypoint for external callers.
        Normalizes to dict (never leaks ToolResult class outward).
        """
        _ = context  # reserved for future auditing/correlation if needed
        tool_deps = self._build_tool_deps(role=role)

        tool_result = self.tools.run(
            name=name,
            role=role,
            deps=tool_deps,
            args=(args or {}) if isinstance(args, dict) else {},
        )

        allowed = True
        if not bool(getattr(tool_result, "ok", False)):
            err = getattr(tool_result, "error", None)
            if isinstance(err, dict) and isinstance(err.get("code"), str):
                if err["code"] in _PERMISSION_DENIED_CODES:
                    allowed = False

        return {
            "ok": bool(getattr(tool_result, "ok", False)),
            "tool": getattr(tool_result, "tool", name),
            "role": getattr(tool_result, "role", role),
            "allowed": allowed,
            "data": getattr(tool_result, "data", None),
            "error": getattr(tool_result, "error", None),
        }

    def llm_route(
        self,
        *,
        role: str,
        user_input: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Runs the brain router (LLM cognition path) and returns the routed dict.
        """
        return self.router.route(
            role=role,
            user_input=user_input,
            context=dict(context or {}),
        )

    # ==========================================================
    # INTERNAL HELPERS
    # ==========================================================
    def _inject_world_context(self, *, role: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        OWNER-only: attach bounded world snapshot into context["world"].
        """
        ctx = dict(context or {})

        if not _is_owner(role):
            return ctx
        if self.world_model is None:
            return ctx
        if "world" in ctx:
            return ctx

        try:
            try:
                ctx["world"] = self.world_context_provider.build(
                    self.world_model,
                    include_events=True,
                    max_entities=8,
                    max_events=8,
                )
            except TypeError:
                ctx["world"] = self.world_context_provider.build(self.world_model)
        except Exception:
            ctx["world"] = {"available": False, "reason": "world_context_build_failed"}

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

        # 1) Identity
        is_owner, role, scores = self.resolve_identity(master_key)

        # 2) Tool override path (explicit/test/system-controlled)
        force_tool = context.get("force_tool_call")
        if isinstance(force_tool, dict):
            tool_out = self.call_tool(
                name=force_tool.get("name"),
                role=role,
                args=force_tool.get("args", {}) or {},
                context=context,
            )

            if tool_out.get("ok"):
                final_result = "TOOL_EXECUTED"
            else:
                final_result = "TOOL_BLOCKED" if not tool_out.get("allowed", True) else "TOOL_FAILED"

            return {
                "identity_verified": is_owner,
                "role": role,
                "allowed": bool(tool_out.get("allowed", False)),
                "tool_result": tool_out,
                "final_result": final_result,
                "scores": scores,
            }

        # 3) Policy (conversation path)
        # IMPORTANT: match your policy rules:
        # - OWNER checks "interact"
        # - GUEST checks "ask_question" (allowed action in your policy)
        policy_action = self._policy_action_for_role(role)

        try:
            allowed = bool(self.policy.check_permission(role=role, action=policy_action, context=context, meta=context.get("meta")))
        except Exception:
            allowed = False

        if not allowed:
            return {
                "identity_verified": is_owner,
                "role": role,
                "allowed": False,
                "final_result": "BLOCKED_BY_POLICY",
                "policy_action": policy_action,
                "scores": scores,
            }

        # 4) World context injection (OWNER-only)
        context = self._inject_world_context(role=role, context=context)

        # 5) Brain routing
        routed = self.llm_route(role=role, user_input=user_input, context=context)

        # 6) Memory integration (OWNER only) — SAFE DEFAULTS
        allow_memory_log = bool(context.get("allow_memory_log", False))
        allow_auto_index = bool(context.get("allow_auto_index", False))

        if _is_owner(role) and allow_memory_log:
            try:
                self.memory.log_interaction(
                    role=role,
                    user_input=user_input,
                    brain_mode=routed.get("mode"),
                    routed_engine=routed,
                    fusion_result=routed.get("result", {}).get("fusion", {}),
                )
            except Exception:
                pass

        if _is_owner(role) and allow_auto_index and isinstance(user_input, str):
            try:
                self.memory.auto_index_from_text(role, user_input)
            except Exception:
                pass

        # 7) Output
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
                "available": context.get("world", {}).get("available") if isinstance(context.get("world"), dict) else None,
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
