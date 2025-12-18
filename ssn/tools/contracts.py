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
    """

    name: str
    description: str

    # Legacy gate (keep for compatibility)
    required_role: Role = "OWNER"

    # New: explicit allowlist for roles (preferred)
    allowed_roles: Optional[Tuple[Role, ...]] = None

    # Tool properties
    state_changing: bool = False
    public: bool = False  # if True, appears in a "public tools list" for GUEST

    # Optional metadata (enforce later in registry/handlers)
    max_calls_per_minute: Optional[int] = None

    input_schema: Dict[str, Any] = field(default_factory=dict)

    # handler(deps, args) -> dict
    handler: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]] = field(
        default=lambda deps, args: {}
    )

    def roles_allowed(self) -> Tuple[Role, ...]:
        return self.allowed_roles if self.allowed_roles is not None else _default_allowed_roles(self.required_role)

    def is_role_allowed(self, role: Role) -> bool:
        return role in self.roles_allowed()


@dataclass
class ToolResult:
    ok: bool
    tool: str
    role: Role
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None
