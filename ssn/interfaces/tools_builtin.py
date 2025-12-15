# ssn/interfaces/tools_builtin.py

from __future__ import annotations

from typing import Any, Dict, Optional

from ssn.interfaces.contracts import InterfaceRequest, InterfaceResponse, ErrorInfo
from ssn.interfaces.tool_bus import ToolBus, ToolSpec
from ssn.interfaces.tool_doc_ingest import doc_ingest_readonly


def tool_list(req: InterfaceRequest, deps: Dict[str, Any]) -> InterfaceResponse:
    bus: ToolBus = deps.get("tool_bus")
    if bus is None:
        return InterfaceResponse(
            ok=False,
            action=req.action,
            role=req.role,
            error=ErrorInfo(code="NO_TOOL_BUS", message="ToolBus not wired into deps."),
        )
    return InterfaceResponse(ok=True, action=req.action, role=req.role, data={"tools": bus.list_tools()})


def memory_types(req: InterfaceRequest, deps: Dict[str, Any]) -> InterfaceResponse:
    memory_hub = deps.get("memory_hub")
    if memory_hub is None:
        return InterfaceResponse(
            ok=False,
            action=req.action,
            role=req.role,
            error=ErrorInfo(code="NO_MEMORY_HUB", message="MemoryHub not available."),
        )

    get_tr = getattr(memory_hub, "get_recent_traces", None)
    traces = get_tr(limit=int(req.meta.get("trace_limit", 50))) if callable(get_tr) else []

    def extract_type(item: Any) -> Optional[str]:
        if isinstance(item, dict):
            payload = item.get("payload", item)
            if isinstance(payload, dict):
                t = payload.get("type")
                return t if isinstance(t, str) else None
        return None

    hist: Dict[str, int] = {}
    for it in traces or []:
        t = extract_type(it) or "unknown"
        hist[t] = hist.get(t, 0) + 1

    return InterfaceResponse(ok=True, action=req.action, role=req.role, data={"trace_type_histogram": hist})


def register_builtin_tools(bus: ToolBus) -> None:
    bus.register(
        ToolSpec(
            name="tools.list",
            description="List all internal tools available on the ToolBus.",
            handler=tool_list,
            owner_only=False,
            read_only=True,
        )
    )
    bus.register(
        ToolSpec(
            name="memory.types",
            description="Read-only histogram of recent trace types.",
            handler=memory_types,
            owner_only=True,
            read_only=True,
        )
    )
    bus.register(
        ToolSpec(
            name="doc.ingest_readonly",
            description="Read-only ingest of provided text/HTML document; returns summary + citations. OWNER may write bounded trace.",
            handler=doc_ingest_readonly,
            owner_only=False,
            read_only=True,
        )
    )
