# ssn/tools/registry.py

from __future__ import annotations

from typing import Any, Dict, Optional

from ssn.tools.contracts import ToolResult, ToolSpec


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if not spec.name or not isinstance(spec.name, str):
            raise ValueError("Tool name must be a non-empty string.")
        self._tools[spec.name] = spec

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def list(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "description": spec.description,
                "required_role": spec.required_role,
                "state_changing": bool(spec.state_changing),
                "input_schema": dict(spec.input_schema or {}),
            }
            for name, spec in sorted(self._tools.items(), key=lambda kv: kv[0])
        }

    def run(self, *, name: str, role: str, deps: Dict[str, Any], args: Dict[str, Any]) -> ToolResult:
        spec = self.get(name)
        if spec is None:
            return ToolResult(ok=False, tool=name, role=role, error={"code": "TOOL_NOT_FOUND", "message": name})

        if spec.required_role == "OWNER" and role != "OWNER":
            return ToolResult(ok=False, tool=name, role=role, error={"code": "TOOL_FORBIDDEN", "message": "OWNER only"})

        try:
            out = spec.handler(deps, args or {})
            if not isinstance(out, dict):
                out = {"result": out}
            return ToolResult(ok=True, tool=name, role=role, data=out)
        except Exception as e:
            return ToolResult(ok=False, tool=name, role=role, error={"code": "TOOL_ERROR", "message": str(e)})
