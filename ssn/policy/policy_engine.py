# /workspaces/SSN/ssn/policy/policy_engine.py

import os
from typing import Any, Dict, List, Optional

import yaml

from ssn.policy.law_paths import home_law_path, system_law_path, world_law_path


class PolicyEngine:
    """
    SSN Policy Engine

    Loads:
      - world_law.yaml
      - system_law.yaml
      - home_law_samson.yaml

    Core logic unchanged:
      - OWNER: HOME LAW ULTIMATE POWER (always allow)
      - NON-OWNER: subject to World Law + limited allowed actions

    Minimal necessary update:
      - Allow NON-OWNER research/tools ONLY when explicitly enabled by context:
          context.allow_tools == True AND context.allow_research == True
      - Keep existing non-owner "interact" for Front Door chat
    """

    # Research tool/action prefixes (explicit)
    _RESEARCH_PREFIXES = (
        "research.",
        "net.",
    )

    # Common orchestrator/gateway tool action forms (do NOT auto-allow by prefix alone)
    _TOOL_ACTION_PREFIXES = (
        "tool:",
        "run_tool",
        "run-tool",
        "tool_call",
        "tool.call",
        "call_tool",
        "call-tool",
        "execute_tool",
        "execute-tool",
    )

    # Explicit net/research tools (tight allowlist)
    _KNOWN_RESEARCH_TOOLS = {
        "research.answer",
        "net.search",
        "net.fetch",
        "net.sanitize",
        "net.cite",
    }

    def __init__(
        self,
        *,
        world_law_path_override: Optional[str] = None,
        system_law_path_override: Optional[str] = None,
        home_law_path_override: Optional[str] = None,
    ):
        self.world_law_path = world_law_path(world_law_path_override)
        self.system_law_path = system_law_path(system_law_path_override)
        self.home_law_path = home_law_path(home_law_path_override)

        self.world_law = self._load_yaml_path(self.world_law_path)
        self.system_law = self._load_yaml_path(self.system_law_path)
        self.home_law = self._load_yaml_path(self.home_law_path)

    def _load_yaml_path(self, path: str) -> Any:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Policy file missing: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _load_yaml(self, filename):
        """Legacy loader — resolves filename in policy package directory."""
        base_dir = os.path.dirname(__file__)
        path = os.path.join(base_dir, filename)
        return self._load_yaml_path(path)

    def _owner_authority_mode(self) -> str:
        mode = (self.home_law or {}).get("owner_authority")
        if isinstance(mode, str) and mode.strip().lower() in ("ultimate", "bounded"):
            return mode.strip().lower()
        return "ultimate"

    def _owner_allowed_actions(self) -> List[str]:
        perms = (self.home_law or {}).get("permissions") or {}
        actions = perms.get("allowed_actions") or []
        if not isinstance(actions, list):
            return []
        return [str(a) for a in actions if isinstance(a, str)]

    def _guest_allowed_actions(self) -> List[str]:
        gp = (self.home_law or {}).get("guest_permissions") or {}
        actions = gp.get("allowed_actions") or []
        if not isinstance(actions, list):
            return []
        return [str(a) for a in actions if isinstance(a, str)]

    # ------------------------------------------------------------
    #  COMPATIBILITY METHODS FOR ORCHESTRATOR + INTERFACES
    # ------------------------------------------------------------

    def check_permission(self, role, action, context=None, meta=None, **kwargs):
        """
        Compatibility method for Orchestrator and InterfaceGateway.
        Returns: True if allowed, False if denied
        """
        result = self.validate_action(role, action, context=context, meta=meta, **kwargs)
        return result["status"] == "allow"

    def is_allowed(self, role, action, context=None, meta=None, **kwargs):
        """
        Returns dict-style response for gateways that expect {'allowed': bool, ...}
        """
        result = self.validate_action(role, action, context=context, meta=meta, **kwargs)
        return {
            "allowed": result["status"] == "allow",
            "status": result["status"],
            "reason": result.get("reason", ""),
        }

    def allow(self, role, action, context=None, meta=None, **kwargs):
        return self.check_permission(role, action, context=context, meta=meta, **kwargs)

    def enforce(self, role, action, context=None, meta=None, **kwargs):
        return self.check_permission(role, action, context=context, meta=meta, **kwargs)

    def check(self, role, action, context=None, meta=None, **kwargs):
        return self.is_allowed(role, action, context=context, meta=meta, **kwargs)

    # ------------------------------------------------------------
    #  OVERRIDE CAPABILITY CHECKS (unchanged)
    # ------------------------------------------------------------

    def _can_override_world_law(self):
        home_overrides = (self.home_law or {}).get("overrides", [])
        world_allows = ((self.world_law or {}).get("world_law") or {}).get("overrides", [])
        return "world_law" in home_overrides and "home_law_samson" in world_allows

    def _can_override_system_law(self):
        home_overrides = (self.home_law or {}).get("overrides", [])
        system_allows = ((self.system_law or {}).get("system_law") or {}).get("overrides", [])
        return "system_law" in home_overrides and "home_law_samson" in system_allows

    # ------------------------------------------------------------
    #  NEW: Context gating helpers (minimal and safe)
    # ------------------------------------------------------------

    def _ctx_flag(self, context, key: str, default: bool = False) -> bool:
        if not isinstance(context, dict):
            return default

        # tolerate future naming variants without breaking
        aliases = {
            "allow_tools": ("allow_tools", "allowTools", "tools_enabled", "toolsEnabled"),
            "allow_research": ("allow_research", "allowResearch", "research_enabled", "researchEnabled"),
        }
        keys = aliases.get(key, (key,))

        v = default
        for k in keys:
            if k in context:
                v = context.get(k, default)
                break

        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("1", "true", "yes", "y", "on"):
                return True
            if s in ("0", "false", "no", "n", "off"):
                return False
        return bool(default)

    def _is_research_or_tool_action(self, action: str) -> bool:
        """
        Detect research/net tool calls safely.

        We only treat an action as "research/tools" if it explicitly mentions
        known net/research tool names OR contains the prefixes "net."/"research.".

        We DO NOT treat generic tool-call prefixes (run_tool/tool:) alone as research,
        because that would inadvertently classify unrelated tools as "research".
        """
        if not isinstance(action, str):
            return False

        a = action.strip()
        if not a:
            return False

        al = a.lower()

        # Exact prefixes (most reliable)
        if al.startswith(self._RESEARCH_PREFIXES):
            return True

        # Contains explicit known tool names anywhere (handles "tool:net.search", etc.)
        for t in self._KNOWN_RESEARCH_TOOLS:
            if t in al:
                return True

        # If action uses a tool-call prefix, require it ALSO mentions net./research. (or known tool name)
        if al.startswith(self._TOOL_ACTION_PREFIXES):
            if any(px in al for px in self._RESEARCH_PREFIXES):
                return True
            # also allow if it includes a known tool name (already checked above, but keep explicit)
            for t in self._KNOWN_RESEARCH_TOOLS:
                if t in al:
                    return True

        return False

    # ------------------------------------------------------------
    #  MAIN VALIDATION LOGIC - HOME LAW ULTIMATE POWER
    # ------------------------------------------------------------

    def validate_action(self, identity_role, action, context=None, meta=None, **kwargs):
        """
        Returns:
            { status: "allow" | "deny", reason: explanation }
        """
        role = (identity_role or "").strip().upper()
        act = (action or "").strip()

        # OWNER: HOME LAW — ultimate (Samson default) or bounded (tenant deployments)
        if role == "OWNER":
            allowed = self._owner_allowed_actions()
            if act in allowed:
                return {"status": "allow", "reason": "Explicitly allowed in HOME LAW"}
            if self._owner_authority_mode() == "ultimate":
                return {"status": "allow", "reason": "HOME LAW ULTIMATE OVERRIDE - All restrictions bypassed"}
            return {"status": "deny", "reason": f"Action '{act}' not permitted by bounded HOME LAW"}

        # NON-OWNERS: subject to World Law + limited allowed actions
        world_rules = ((self.world_law or {}).get("world_law") or {})
        action_lower = act.lower()

        # Core World Law violations for non-owners (unchanged behavior)
        if (not world_rules.get("allow_harm", False)) and any(
            word in action_lower for word in ["harm", "hurt", "kill", "injure"]
        ):
            return {"status": "deny", "reason": "Blocked by WORLD LAW: No harm allowed"}

        if (not world_rules.get("allow_illegal_actions", False)) and ("illegal" in action_lower):
            return {"status": "deny", "reason": "Blocked by WORLD LAW: No illegal actions"}

        if (not world_rules.get("allow_leak_sensitive_data", False)) and any(
            word in action_lower for word in ["leak", "expose_secret"]
        ):
            return {"status": "deny", "reason": "Blocked by WORLD LAW: No data leaks"}

        # Tenant/org guest allowlist (optional in home law YAML)
        guest_allowed = self._guest_allowed_actions()
        if guest_allowed and act in guest_allowed:
            return {"status": "allow", "reason": "Guest action permitted by HOME LAW guest_permissions"}

        # NEW (minimal): allow research/tool actions only if explicitly enabled by context
        if self._is_research_or_tool_action(act):
            allow_tools = self._ctx_flag(context, "allow_tools", default=False)
            allow_research = self._ctx_flag(context, "allow_research", default=False)

            if allow_tools and allow_research:
                return {
                    "status": "allow",
                    "reason": "Research/tools permitted for non-owner by explicit context gate",
                }

            return {
                "status": "deny",
                "reason": "Research/tools denied for non-owner (requires allow_tools=true and allow_research=true)",
            }

        # Existing basic permissions for normal users (keep your agreed change)
        normal_user_allowed_actions = [
            "basic_query",
            "request_info",
            "get_help",
            "ask_question",
            "interact",  # ✅ agreed change
        ]

        if act in normal_user_allowed_actions:
            return {"status": "allow", "reason": "Action permitted for user role"}

        return {"status": "deny", "reason": "Action not permitted for non-owner role"}

    # ------------------------------------------------------------
    #  UTILITY METHODS (unchanged)
    # ------------------------------------------------------------

    def get_override_status(self):
        return {
            "home_law_authority": "ULTIMATE",
            "world_law_override": "COMPLETE",
            "system_law_override": "COMPLETE",
            "owner_restrictions": "NONE",
            "message": "Home Law has absolute authority over all restrictions",
        }

    def check_system_health(self):
        return {
            "world_law_loaded": bool(self.world_law),
            "system_law_loaded": bool(self.system_law),
            "home_law_loaded": bool(self.home_law),
            "owner_authority_level": "ABSOLUTE",
            "system_status": "HOME LAW SUPREME - All overrides active",
        }

    def get_owner_capabilities(self):
        return {
            "can_override_harm_restrictions": True,
            "can_override_illegal_restrictions": True,
            "can_override_data_protection": True,
            "can_override_system_integrity": True,
            "can_override_all_safety_measures": True,
            "authority_level": "CREATOR_ULTIMATE",
        }
