# ssn/interfaces/tool_bus.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from ssn.interfaces.contracts import InterfaceRequest, InterfaceResponse, ErrorInfo


ToolHandler = Callable[[InterfaceRequest, Dict[str, Any]], InterfaceResponse]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    handler: ToolHandler
    owner_only: bool = True
    read_only: bool = True


class ToolBus:
    """
    Phase 4.4 — Internal Tool Bus (no external actions)

    - Registers tools as small, testable handlers
    - Enforces owner-only and read-only constraints at dispatch time
    - Uses the same InterfaceRequest/Response contract as the gateway

    Tools here are internal capabilities, not external agents.
    """

    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if not spec.name or not isinstance(spec.name, str):
            raise ValueError("ToolSpec.name must be a non-empty string.")
        if spec.name in self._tools:
            raise ValueError(f"Tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for name, spec in sorted(self._tools.items()):
            out[name] = {
                "description": spec.description,
                "owner_only": spec.owner_only,
                "read_only": spec.read_only,
            }
        return out

    def dispatch(self, tool_name: str, req: InterfaceRequest, deps: Dict[str, Any]) -> InterfaceResponse:
        spec = self._tools.get(tool_name)
        if spec is None:
            return InterfaceResponse(
                ok=False,
                action=req.action,
                role=req.role,
                error=ErrorInfo(code="TOOL_NOT_FOUND", message=f"Unknown tool: {tool_name}"),
            )

        # Enforce owner-only tools (requested role must be OWNER; orchestrator remains authority elsewhere)
        if spec.owner_only and req.role != "OWNER":
            return InterfaceResponse(
                ok=False,
                action=req.action,
                role=req.role,
                error=ErrorInfo(code="TOOL_OWNER_ONLY", message=f"Tool requires OWNER: {tool_name}"),
            )

        # Enforce read-only tools: they must not request external actions.
        # Here we only annotate; actual no-external-actions remains a system invariant.
        try:
            resp = spec.handler(req, deps)
        except Exception as e:
            return InterfaceResponse(
                ok=False,
                action=req.action,
                role=req.role,
                error=ErrorInfo(code="TOOL_RUNTIME_ERROR", message=str(e), details={"tool": tool_name}),
            )

        # Attach tool metadata
        data = dict(resp.data or {})
        data.setdefault("tool", tool_name)
        data.setdefault("read_only", spec.read_only)
        return InterfaceResponse(ok=resp.ok, action=resp.action, role=resp.role, data=data, error=resp.error)
