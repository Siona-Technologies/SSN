# ssn/tools/contracts.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Literal, Optional, Tuple


Role = Literal["OWNER", "GUEST"]


def _default_allowed_roles(required_role: Role) -> Tuple[Role, ...]:
    """
    Backward compatible mapping:
      - required_role == "OWNER"  => only OWNER
      - required_role == "GUEST"  => OWNER and GUEST
    """
    return ("OWNER",) if required_role == "OWNER" else ("OWNER", "GUEST")


@dataclass(frozen=True)
class ToolSpec:
    """
    Tool contract for the ToolRegistry layer.

    Backward compatibility:
      - required_role is still supported and used as the default source of truth.
      - allowed_roles, if provided, overrides required_role logic.

    Approval semantics:
      - Tools that are both state_changing AND external_effect
        automatically require explicit OWNER approval.
    """

    name: str
    description: str

    # Legacy gate (keep for compatibility)
    required_role: Role = "OWNER"

    # New: explicit allowlist for roles (preferred)
    allowed_roles: Optional[Tuple[Role, ...]] = None

    # Tool properties
    state_changing: bool = False

    # NEW: indicates real-world or external side effects
    # (calls, payments, device actions, speech output, code writes, etc.)
    external_effect: bool = False

    public: bool = False  # if True, appears in a "public tools list" for GUEST

    # Optional metadata (enforced elsewhere)
    max_calls_per_minute: Optional[int] = None

    input_schema: Dict[str, Any] = field(default_factory=dict)

    # handler(deps, args) -> dict
    handler: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]] = field(
        default=lambda deps, args: {}
    )

    def roles_allowed(self) -> Tuple[Role, ...]:
        return (
            self.allowed_roles
            if self.allowed_roles is not None
            else _default_allowed_roles(self.required_role)
        )

    def is_role_allowed(self, role: Role) -> bool:
        return role in self.roles_allowed()

    @property
    def requires_approval(self) -> bool:
        """
        A tool requires explicit OWNER approval if it:
          - changes state, AND
          - causes an external side effect.
        """
        return bool(self.state_changing and self.external_effect)


@dataclass
class ToolResult:
    ok: bool
    tool: str
    role: Role
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None
