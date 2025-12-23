# ssn/interfaces/agent_shell.py

from __future__ import annotations

from typing import Any, Dict, Tuple

from ssn.interfaces.contracts import InterfaceRequest, InterfaceResponse, ErrorInfo
from ssn.interfaces.gateway import InterfaceGateway


class AgentShell:
    """
    Phase 4.1+ — Agent Shell
    Bridges runtime/CLI events -> InterfaceGateway requests.

    Supported event types:
      - chat       -> action: think
      - state      -> action: explain_state
      - memory     -> action: summarize_memory
      - suggest    -> action: suggest
      - world      -> action: world
      - sense_tick -> action: sense_tick
      - tool       -> action: tool      (legacy ToolBus, uses meta.tool_name)
      - run_tool   -> action: run_tool  (ToolRegistry path, uses context.tool_name/context.args)
    """

    def __init__(self, gateway: InterfaceGateway, default_role: str = "GUEST"):
        self.gateway = gateway
        self.default_role = default_role if default_role in ("OWNER", "GUEST") else "GUEST"

    @staticmethod
    def _get(d: Any, key: str, default=None):
        if isinstance(d, dict):
            return d.get(key, default)
        return getattr(d, key, default)

    @staticmethod
    def _normalize_context_meta(context: Any, meta: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if not isinstance(context, dict):
            context = {}
        if not isinstance(meta, dict):
            meta = {}

        # If a caller incorrectly put master_key in context, migrate it into meta and redact context.
        if "master_key" in context and "master_key" not in meta:
            meta = dict(meta)
            meta["master_key"] = context.get("master_key")

        if "master_key" in context:
            context = dict(context)
            context.pop("master_key", None)

        # Also redact nested auth.master_key
        auth = context.get("auth")
        if isinstance(auth, dict) and "master_key" in auth:
            auth2 = dict(auth)
            auth2.pop("master_key", None)
            context = dict(context)
            context["auth"] = auth2

        return context, meta

    @staticmethod
    def _derive_role(default_role: str, claimed_role: Any, meta: Dict[str, Any]) -> str:
        """
        Production rule:
        - If master_key is present, treat as OWNER *candidate* (handlers re-verify).
        - Otherwise fall back to claimed role if valid, else default_role.
        """
        mk = meta.get("master_key") if isinstance(meta, dict) else None
        if isinstance(mk, str) and mk.strip():
            return "OWNER"

        if isinstance(claimed_role, str) and claimed_role in ("OWNER", "GUEST"):
            return claimed_role

        return default_role if default_role in ("OWNER", "GUEST") else "GUEST"

    def handle_event(self, event: Any) -> InterfaceResponse:
        etype = self._get(event, "type", None)

        claimed_role = self._get(event, "role", None)
        text = self._get(event, "text", "")
        context = self._get(event, "context", None)
        meta = self._get(event, "meta", None)

        context, meta = self._normalize_context_meta(context, meta)
        role = self._derive_role(self.default_role, claimed_role, meta)

        if etype == "chat":
            req = InterfaceRequest(action="think", role=role, user_input=str(text or ""), context=context, meta=meta)
            return self.gateway.handle(req)

        if etype == "state":
            req = InterfaceRequest(action="explain_state", role=role, user_input="", context={}, meta=meta)
            return self.gateway.handle(req)

        if etype == "memory":
            req = InterfaceRequest(action="summarize_memory", role=role, user_input="", context={}, meta=meta)
            return self.gateway.handle(req)

        if etype == "suggest":
            req = InterfaceRequest(action="suggest", role=role, user_input="", context={}, meta=meta)
            return self.gateway.handle(req)

        if etype == "world":
            req = InterfaceRequest(action="world", role=role, user_input="", context=context, meta=meta)
            return self.gateway.handle(req)

        if etype == "sense_tick":
            req = InterfaceRequest(action="sense_tick", role=role, user_input="", context=context, meta=meta)
            return self.gateway.handle(req)

        # Legacy ToolBus path: gateway requires meta.tool_name
        if etype == "tool":
            tool_name = self._get(event, "tool_name", None)
            args = self._get(event, "args", None)

            meta2 = dict(meta or {})
            if isinstance(tool_name, str) and tool_name.strip():
                meta2.setdefault("tool_name", tool_name.strip())
            if isinstance(args, dict):
                meta2.setdefault("args", args)

            req = InterfaceRequest(action="tool", role=role, user_input=str(text or ""), context=context, meta=meta2)
            return self.gateway.handle(req)

        # ToolRegistry execution path: handlers_tools expects context.tool_name + context.args
        if etype == "run_tool":
            tool_name = self._get(event, "tool_name", None)
            args = self._get(event, "args", None)

            ctx2 = dict(context or {})
            if isinstance(tool_name, str) and tool_name.strip():
                ctx2["tool_name"] = tool_name.strip()
            if isinstance(args, dict):
                ctx2["args"] = args

            req = InterfaceRequest(action="run_tool", role=role, user_input="", context=ctx2, meta=meta)
            return self.gateway.handle(req)

        return InterfaceResponse(
            ok=False,
            action="unknown",
            role=role,
            data={},
            error=ErrorInfo(code="UNKNOWN_EVENT_TYPE", message=f"Unsupported event type: {etype}", details={}),
        )
