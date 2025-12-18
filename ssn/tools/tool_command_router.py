# ssn/tools/tool_command_router.py

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: Dict[str, Any]


def _safe_lower(s: Any) -> str:
    try:
        return str(s or "").lower().strip()
    except Exception:
        return ""


def _try_parse_json_tail(text: str) -> Dict[str, Any]:
    """
    If the user includes a JSON object at the end of the command,
    e.g. "run world.read {\"max_events\":2}", parse it.
    """
    t = (text or "").strip()
    if not t.endswith("}"):
        return {}
    i = t.rfind("{")
    if i < 0:
        return {}
    blob = t[i:]
    try:
        obj = json.loads(blob)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def build_tool_plan(text: str, context: Optional[Dict[str, Any]] = None) -> List[ToolCall]:
    """
    Deterministic mapping from chat text to tool calls (Phase 6.6).

    Notes:
    - We keep it simple and explicit to avoid surprising actions.
    - State-changing action allowed only for explicit "sense tick" intents.
    """
    ctx = context if isinstance(context, dict) else {}
    t = _safe_lower(text)

    # Explicit override: allow "run-tool <name> {json}"
    # Examples:
    #   "run-tool world.read {"max_events":2}"
    #   "/tool tools.list"
    if t.startswith("run-tool ") or t.startswith("/tool ") or t.startswith("tool "):
        parts = (text or "").strip().split(maxsplit=2)
        if len(parts) >= 2:
            name = parts[1].strip()
            args = {}
            if len(parts) == 3:
                # allow json blob as third part
                try:
                    parsed = json.loads(parts[2])
                    if isinstance(parsed, dict):
                        args = parsed
                except Exception:
                    args = _try_parse_json_tail(text)
            return [ToolCall(name=name, args=args)]

    # Heuristic composite commands
    wants_tick = any(k in t for k in ["sense tick", "sense-tick", "perceive", "scan", "tick"])
    wants_world = any(k in t for k in ["show world", "read world", "world status", "world"])
    wants_tools = any(k in t for k in ["list tools", "tools list", "what tools"])
    wants_memory = any(k in t for k in ["memory summary", "summarize memory", "memory report"])
    wants_policy = any(k in t for k in ["policy snapshot", "policy status", "policy"])
    wants_safety = any(k in t for k in ["safety status", "safety report", "safety"])
    wants_identity = any(k in t for k in ["identity view", "show identity", "who is the creator", "who is the owner"])

    # Optional JSON tail to override args (bounded in tools anyway)
    tail_args = _try_parse_json_tail(text)

    plan: List[ToolCall] = []

    if wants_tick:
        args = {"events": [], "max_events": int(ctx.get("max_events", 25) or 25)}
        args.update(tail_args)
        plan.append(ToolCall(name="world.sense_tick", args=args))

    if wants_world:
        args = {
            "max_entities": int(ctx.get("max_entities", 8) or 8),
            "max_events": int(ctx.get("max_events", 8) or 8),
            "include_events": True,
        }
        args.update(tail_args)
        plan.append(ToolCall(name="world.read", args=args))

    if wants_tools:
        plan.append(ToolCall(name="tools.list", args={}))

    if wants_memory:
        args = {"trace_limit": int(ctx.get("trace_limit", 30) or 30), "episodic_limit": int(ctx.get("episodic_limit", 10) or 10)}
        args.update(tail_args)
        plan.append(ToolCall(name="memory.summary", args=args))

    if wants_policy:
        plan.append(ToolCall(name="policy.snapshot", args={}))

    if wants_safety:
        plan.append(ToolCall(name="safety.status", args={}))

    if wants_identity:
        # Read-only: identity.view only (enroll remains explicit via run-tool)
        plan.append(ToolCall(name="identity.view", args={}))

    # Deduplicate while keeping order
    seen = set()
    out: List[ToolCall] = []
    for c in plan:
        key = (c.name, json.dumps(c.args, sort_keys=True, default=str))
        if key in seen:
            continue
        seen.add(key)
        out.append(c)

    return out
