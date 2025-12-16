# ssn/interfaces/agent_shell.py

from __future__ import annotations

from typing import Any

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
      - tool       -> action: tool
      - run_tool   -> action: run_tool   (Phase 6.5A)
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
    def _normalize_context_meta(context: Any, meta: Any):
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

    def handle_event(self, event: Any) -> InterfaceResponse:
        etype = self._get(event, "type", None)

        role = self._get(event, "role", None)
        if not isinstance(role, str) or role not in ("OWNER", "GUEST"):
            role = self.default_role

        text = self._get(event, "text", "")
        context = self._get(event, "context", None)
        meta = self._get(event, "meta", None)

        context, meta = self._normalize_context_meta(context, meta)

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

        if etype == "tool":
            req = InterfaceRequest(action="tool", role=role, user_input=str(text or ""), context=context, meta=meta)
            return self.gateway.handle(req)

        # Phase 6.5A — tool registry execution
        if etype == "run_tool":
            req = InterfaceRequest(action="run_tool", role=role, user_input="", context=context, meta=meta)
            return self.gateway.handle(req)

        return InterfaceResponse(
            ok=False,
            action="unknown",
            role=role,
            data={},
            error=ErrorInfo(code="UNKNOWN_EVENT_TYPE", message=f"Unsupported event type: {etype}", details={}),
        )
