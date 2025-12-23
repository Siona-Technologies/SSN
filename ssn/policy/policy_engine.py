import yaml
import os


class PolicyEngine:
    """
    SSN Policy Engine

    Loads:
      - world_law.yaml
      - system_law.yaml
      - home_law_samson.yaml

    Core logic is unchanged:
      - OWNER: HOME LAW ULTIMATE POWER (always allow)
      - NON-OWNER: subject to World Law + limited allowed actions

    Agreed update:
      - Allow NON-OWNER "interact" so Front Door chat works for GUEST.
        (OWNER rules unchanged.)
    """

    def __init__(self):
        # No policy_dir needed - uses relative path from script location
        self.world_law = self._load_yaml("world_law.yaml")
        self.system_law = self._load_yaml("system_law.yaml")
        self.home_law = self._load_yaml("home_law_samson.yaml")

    def _load_yaml(self, filename):
        """Load YAML file from the same directory as this script."""
        base_dir = os.path.dirname(__file__)
        path = os.path.join(base_dir, filename)

        if not os.path.exists(path):
            raise FileNotFoundError(f"Policy file missing: {path}")

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    # ------------------------------------------------------------
    #  COMPATIBILITY METHOD FOR ORCHESTRATOR + INTERFACES
    # ------------------------------------------------------------

    def check_permission(self, role, action, context=None, meta=None, **kwargs):
        """
        Compatibility method for Orchestrator and InterfaceGateway.
        Returns: True if allowed, False if denied
        """
        result = self.validate_action(role, action, context=context, meta=meta)
        return result["status"] == "allow"

    # Common interface-style aliases expected by various gateways
    def is_allowed(self, role, action, context=None, meta=None, **kwargs):
        """
        Returns dict-style response for gateways that expect {'allowed': bool, ...}
        """
        result = self.validate_action(role, action, context=context, meta=meta)
        return {
            "allowed": result["status"] == "allow",
            "status": result["status"],
            "reason": result.get("reason", ""),
        }

    def allow(self, role, action, context=None, meta=None, **kwargs):
        return self.check_permission(role, action, context=context, meta=meta, **kwargs)

    def enforce(self, role, action, context=None, meta=None, **kwargs):
        # For engines that interpret enforce() as a permission check.
        return self.check_permission(role, action, context=context, meta=meta, **kwargs)

    def check(self, role, action, context=None, meta=None, **kwargs):
        # Some gateways call check() instead of check_permission()
        return self.is_allowed(role, action, context=context, meta=meta, **kwargs)

    # ------------------------------------------------------------
    #  OVERRIDE CAPABILITY CHECKS
    # ------------------------------------------------------------

    def _can_override_world_law(self):
        """Check if Home Law can override World Law."""
        home_overrides = self.home_law.get("overrides", [])
        world_allows = self.world_law["world_law"].get("overrides", [])
        return "world_law" in home_overrides and "home_law_samson" in world_allows

    def _can_override_system_law(self):
        """Check if Home Law can override System Law."""
        home_overrides = self.home_law.get("overrides", [])
        system_allows = self.system_law["system_law"].get("overrides", [])
        return "system_law" in home_overrides and "home_law_samson" in system_allows

    # ------------------------------------------------------------
    #  MAIN VALIDATION LOGIC - HOME LAW ULTIMATE POWER
    # ------------------------------------------------------------

    def validate_action(self, identity_role, action, context=None, meta=None, **kwargs):
        """
        Returns:
            { status: "allow" | "deny", reason: explanation }
        """
        # OWNER: HOME LAW ULTIMATE POWER - OVERRIDES EVERYTHING
        if identity_role == "OWNER":
            # Check if explicitly allowed in Home Law
            home_allowed = self.home_law["permissions"]["allowed_actions"]
            if action in home_allowed:
                return {
                    "status": "allow",
                    "reason": "Explicitly allowed in HOME LAW"
                }

            # Even if not explicitly listed, Owner can do ANYTHING
            # Home Law overrides ALL World Law and System Law restrictions
            return {
                "status": "allow",
                "reason": "HOME LAW ULTIMATE OVERRIDE - All restrictions bypassed"
            }

        # NON-OWNERS: Still subject to World Law and System Law
        else:
            # For normal users, check World Law core violations
            world_rules = self.world_law["world_law"]

            # Core World Law violations for non-owners
            action_lower = (action or "").lower()

            if (not world_rules["allow_harm"] and any(word in action_lower for word in ["harm", "hurt", "kill", "injure"])):
                return {
                    "status": "deny",
                    "reason": "Blocked by WORLD LAW: No harm allowed"
                }

            if (not world_rules["allow_illegal_actions"] and "illegal" in action_lower):
                return {
                    "status": "deny",
                    "reason": "Blocked by WORLD LAW: No illegal actions"
                }

            if (not world_rules["allow_leak_sensitive_data"] and any(word in action_lower for word in ["leak", "expose_secret"])):
                return {
                    "status": "deny",
                    "reason": "Blocked by WORLD LAW: No data leaks"
                }

            # Basic permissions for normal users (UPDATED: allow "interact" for Front Door chat)
            normal_user_allowed_actions = [
                "basic_query",
                "request_info",
                "get_help",
                "ask_question",
                "interact",  # ✅ agreed change
            ]

            if action in normal_user_allowed_actions:
                return {
                    "status": "allow",
                    "reason": "Action permitted for user role"
                }
            else:
                return {
                    "status": "deny",
                    "reason": "Action not permitted for non-owner role"
                }

    # ------------------------------------------------------------
    #  UTILITY METHODS
    # ------------------------------------------------------------

    def get_override_status(self):
        """Check what override capabilities are configured."""
        return {
            "home_law_authority": "ULTIMATE",
            "world_law_override": "COMPLETE",
            "system_law_override": "COMPLETE",
            "owner_restrictions": "NONE",
            "message": "Home Law has absolute authority over all restrictions"
        }

    def check_system_health(self):
        """Check if all policy files are loaded correctly."""
        return {
            "world_law_loaded": bool(self.world_law),
            "system_law_loaded": bool(self.system_law),
            "home_law_loaded": bool(self.home_law),
            "owner_authority_level": "ABSOLUTE",
            "system_status": "HOME LAW SUPREME - All overrides active"
        }

    def get_owner_capabilities(self):
        """Show the ultimate power of the Home Law."""
        return {
            "can_override_harm_restrictions": True,
            "can_override_illegal_restrictions": True,
            "can_override_data_protection": True,
            "can_override_system_integrity": True,
            "can_override_all_safety_measures": True,
            "authority_level": "CREATOR_ULTIMATE"
        }
