# ssn/tools/contracts.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Literal, Optional


Role = Literal["OWNER", "GUEST"]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    required_role: Role = "OWNER"
    state_changing: bool = False
    input_schema: Dict[str, Any] = field(default_factory=dict)
    handler: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]] = field(default=lambda deps, args: {})


@dataclass
class ToolResult:
    ok: bool
    tool: str
    role: Role
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None
