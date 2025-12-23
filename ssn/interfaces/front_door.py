# ssn/interfaces/front_door.py
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from ssn.tools.contracts import ToolSpec

# -----------------------------
# Bounds (interface-level)
# -----------------------------
MAX_ANSWER_CHARS = 2500
MAX_USED_TOOLS = 10
MAX_SOURCES = 10
MAX_CITATIONS = 10
MAX_NOTE_CHARS = 600


def _clip(s: str, n: int) -> str:
    s = s or ""
    return s if len(s) <= n else (s[: n - 3] + "...")


def _forced_offline() -> bool:
    return os.getenv("SSN_OFFLINE") == "1"


def _scrub_secrets(x: Any) -> Any:
    """
    Defensive redaction: ensure no secret fields leak in outputs.
    """
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            lk = str(k).lower()
            if lk in {"master_key", "ssn_master_key"}:
                continue
            out[k] = _scrub_secrets(v)
        return out
    if isinstance(x, list):
        return [_scrub_secrets(v) for v in x]
    return x


def _sanitize_context(ctx: dict) -> dict:
    """
    Production rule: NEVER forward master_key inside context to tools/LLM.
    """
    if not isinstance(ctx, dict):
        return {}
    clean = dict(ctx)

    clean.pop("master_key", None)

    meta = clean.get("meta")
    if isinstance(meta, dict):
        meta2 = dict(meta)
        meta2.pop("master_key", None)
        clean["meta"] = meta2

    auth = clean.get("auth")
    if isinstance(auth, dict):
        auth2 = dict(auth)
        auth2.pop("master_key", None)
        clean["auth"] = auth2

    return clean


def _extract_master_key(context: dict) -> Optional[str]:
    """
    Accept master_key from:
      - context["master_key"] (legacy)
      - context["meta"]["master_key"] (preferred if caller provides meta)
    Then caller must NOT forward it downstream; we scrub it immediately.
    """
    if not isinstance(context, dict):
        return None

    mk = context.get("master_key")
    if isinstance(mk, str) and mk.strip():
        return mk.strip()

    meta = context.get("meta")
    if isinstance(meta, dict):
        mk2 = meta.get("master_key")
        if isinstance(mk2, str) and mk2.strip():
            return mk2.strip()

    return None


def _safe_session_state(ctx: dict) -> dict:
    return {
        "session_id": ctx.get("session_id"),
        "turn_id": ctx.get("turn_id"),
        "role": ctx.get("role"),
        "offline": bool(ctx.get("offline", False)) or _forced_offline(),
        "strict": bool(ctx.get("strict", False)),
        "degraded": bool(ctx.get("degraded", False)),
    }


# -----------------------------
# Intent routing (deterministic)
# -----------------------------
_KNOWLEDGE_PATTERNS = [
    r"^\s*(kb|knowledge)\s*:\s*",
    r"\bwhat do we know about\b",
    r"\b(search|lookup|find)\b.*\b(knowledge|kb)\b",
]

_PROMOTE_PATTERNS = [
    r"^\s*promote\s*:\s*",
    r"^\s*save\s+to\s+knowledge\s*:\s*",
    r"\b(save|store|promote)\b.*\b(knowledge|kb)\b",
]

_RESEARCH_PATTERNS = [
    r"\bresearch\b",
    r"\bsearch the web\b|\binternet\b|\bonline\b",
    r"\bcitation\b|\bsources?\b",
]


def _match_any(patterns: List[str], text: str) -> bool:
    t = (text or "").strip().lower()
    for p in patterns:
        if re.search(p, t, flags=re.IGNORECASE):
            return True
    return False


def _route_intent(user_input: str, context: dict) -> str:
    """
    Returns one of:
      - knowledge_promote
      - knowledge_search
      - research_answer
      - llm_only
    """
    offline = bool(context.get("offline", False)) or _forced_offline()
    allow_tools = bool(context.get("allow_tools", True))
    allow_research = bool(context.get("allow_research", True))

    if _match_any(_PROMOTE_PATTERNS, user_input):
        return "knowledge_promote"

    if _match_any(_KNOWLEDGE_PATTERNS, user_input):
        return "knowledge_search"

    if not allow_tools:
        return "llm_only"

    if allow_research and not offline and _match_any(_RESEARCH_PATTERNS, user_input):
        return "research_answer"

    looks_like_question = (
        "?" in (user_input or "")
        or re.match(r"^\s*(what|why|how|when|where|who)\b", user_input or "", re.I) is not None
    )
    if allow_research and not offline and looks_like_question:
        return "research_answer"

    return "llm_only"


def _extract_prefixed_payload(user_input: str, patterns: List[str]) -> str:
    t = (user_input or "").strip()
    for pat in patterns:
        m = re.match(pat, t, flags=re.IGNORECASE)
        if m:
            return (m.group(1) or "").strip()
    return ""


def _is_owner(role: str) -> bool:
    return (role or "").upper().strip() == "OWNER"


# -----------------------------
# Tool approval enforcement
# -----------------------------
def _approval_required(spec: Optional[ToolSpec]) -> bool:
    if spec is None:
        return False
    try:
        return bool(getattr(spec, "requires_approval", False))
    except Exception:
        return False


def _build_approval_envelope(
    *,
    tool: str,
    args: dict,
    context: dict,
    reason: str,
    used_tools: List[str],
) -> dict:
    safe_args = _scrub_secrets(args)
    return {
        "answer": "Approval required before executing this action.",
        "degraded": bool(context.get("degraded", False)),
        "used_tools": used_tools[:MAX_USED_TOOLS],
        "session_state": _safe_session_state(context),
        "approval_request": {
            "tool": tool,
            "args": safe_args,
            "reason": _clip(reason, MAX_NOTE_CHARS),
            "instruction": "To approve, re-send the same request with context.confirm=True (OWNER only).",
        },
        "note": _clip(reason, MAX_NOTE_CHARS),
    }


def _resolve_registry(orch: Any, deps: Dict[str, Any]) -> Any:
    reg = deps.get("tool_registry")
    if reg is not None:
        return reg
    return getattr(orch, "tools", None) or getattr(orch, "tool_registry", None)


def _tool_deps_for_run(
    *,
    orch: Any,
    deps: Dict[str, Any],
    role: str,
    master_key: Optional[str],
) -> Dict[str, Any]:
    out = dict(deps or {})
    out["orchestrator"] = orch

    mem = getattr(orch, "memory_hub", None) or getattr(orch, "memory", None)
    if mem is not None:
        out["memory_hub"] = mem
        out["memory"] = mem

    reg = _resolve_registry(orch, out)
    if reg is not None:
        out["tool_registry"] = reg
        out["tools"] = reg

    wm = getattr(orch, "world_model", None)
    if wm is not None:
        out["world_model"] = wm

    wcp = getattr(orch, "world_context_provider", None)
    if wcp is not None:
        out["world_context_provider"] = wcp

    pol = getattr(orch, "policy_engine", None) or getattr(orch, "policy", None)
    if pol is not None:
        out["policy_engine"] = pol
        sm = getattr(pol, "safety_monitor", None)
        if sm is not None:
            out["safety_monitor"] = sm

    out["role"] = role

    if _is_owner(role) and master_key:
        out["master_key"] = master_key

    return out


def _run_tool_production(
    *,
    orch: Any,
    deps: Dict[str, Any],
    role: str,
    master_key: Optional[str],
    tool_name: str,
    tool_args: Dict[str, Any],
    context: Dict[str, Any],
    used_tools: List[str],
) -> Dict[str, Any]:
    reg = _resolve_registry(orch, deps)
    if reg is None or not callable(getattr(reg, "run", None)):
        return {
            "ok": False,
            "error": {"code": "TOOL_REGISTRY_MISSING", "message": "Tool registry not wired."},
            "data": None,
        }

    try:
        spec = reg.get(tool_name)
    except Exception:
        spec = None

    if _approval_required(spec):
        confirmed = bool(context.get("confirm") is True)
        if not (_is_owner(role) and confirmed):
            return {
                "ok": False,
                "needs_approval": True,
                "approval_envelope": _build_approval_envelope(
                    tool=tool_name,
                    args=tool_args,
                    context=context,
                    reason="Tool requires explicit approval (state_changing + external_effect).",
                    used_tools=used_tools,
                ),
            }

    args2 = dict(tool_args or {})
    if _is_owner(role) and master_key:
        args2["master_key"] = master_key

    deps_for_tool = _tool_deps_for_run(orch=orch, deps=deps, role=role, master_key=master_key)

    r = reg.run(name=tool_name, role=role, deps=deps_for_tool, args=args2)
    used_tools.append(tool_name)

    ok = bool(getattr(r, "ok", False))
    data = _scrub_secrets(getattr(r, "data", None))
    err = _scrub_secrets(getattr(r, "error", None))

    return {"ok": ok, "data": data, "error": err}


# -----------------------------
# Orchestrator output extraction
# -----------------------------
def _extract_text(obj: Any) -> Optional[str]:
    """
    Robustly extract a final answer string from varying orchestrator shapes.
    """
    if obj is None:
        return None

    if isinstance(obj, str):
        s = obj.strip()
        return s or None

    for attr in ("data", "result", "output"):
        try:
            v = getattr(obj, attr, None)
        except Exception:
            v = None
        if v is not None:
            t = _extract_text(v)
            if t:
                return t

    if isinstance(obj, dict):
        for k in ("final_message", "answer", "message", "text", "response", "final"):
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()

        fusion = None
        try:
            fusion = obj.get("routed_engine", {}).get("result", {}).get("fusion")
        except Exception:
            fusion = None
        if fusion is None:
            try:
                fusion = obj.get("result", {}).get("fusion")
            except Exception:
                fusion = None
        if isinstance(fusion, dict):
            fm = fusion.get("final_message")
            if isinstance(fm, str) and fm.strip():
                return fm.strip()

        for k in ("routed_engine", "result", "fusion", "data"):
            v = obj.get(k)
            t = _extract_text(v)
            if t:
                return t

    return None


# -----------------------------
# Entry point
# -----------------------------
def handle_user_message(user_input: str, deps: dict, context: dict) -> dict:
    deps = dict(deps or {})
    context_in = dict(context or {})

    orch = deps.get("orchestrator")
    if orch is None:
        raise ValueError("FrontDoor requires deps['orchestrator'].")

    # Secret handling: extract then scrub downstream context
    master_key = _extract_master_key(context_in)
    ctx = _sanitize_context(context_in)

    # Identity / role (do NOT trust caller-provided role)
    _is_owner_verified, role, _scores = orch.resolve_identity(master_key)
    ctx["role"] = role

    # Policy engine lookup (robust)
    pol = getattr(orch, "policy_engine", None) or getattr(orch, "policy", None)

    # AGREED BEHAVIOR (do not change policy rules):
    # - OWNER checks "interact"
    # - GUEST checks "ask_question" (since your policy only allows basics to non-owner)
    policy_action = "interact" if _is_owner(role) else "ask_question"

    try:
        allowed = bool(
            getattr(pol, "check_permission")(
                role=role,
                action=policy_action,
                context=ctx,
                meta=ctx.get("meta"),
            )
        )
    except Exception:
        allowed = False

    if not allowed:
        return {
            "answer": "Blocked by policy.",
            "degraded": False,
            "used_tools": [],
            "session_state": _safe_session_state(ctx),
            "note": f"Policy denied action={policy_action}.",
        }

    used_tools: List[str] = []
    degraded = bool(ctx.get("degraded", False))
    offline = bool(ctx.get("offline", False)) or _forced_offline()

    intent = _route_intent(user_input, ctx)

    # knowledge.promote (OWNER only)
    if intent == "knowledge_promote":
        if not _is_owner(role):
            return {
                "answer": "Not authorized: knowledge promotion is OWNER-only.",
                "degraded": degraded,
                "used_tools": [],
                "session_state": _safe_session_state(ctx),
                "note": "Promotion denied due to role.",
            }

        payload = _extract_prefixed_payload(
            user_input,
            patterns=[
                r"^\s*promote\s*:\s*(.*)$",
                r"^\s*save\s+to\s+knowledge\s*:\s*(.*)$",
            ],
        ) or (user_input or "").strip()

        out = _run_tool_production(
            orch=orch,
            deps=deps,
            role=role,
            master_key=master_key,
            tool_name="knowledge.promote",
            tool_args={"text": payload},
            context=ctx,
            used_tools=used_tools,
        )

        if out.get("needs_approval"):
            return out["approval_envelope"]

        if out.get("ok"):
            data = out.get("data") or {}
            kid = data.get("kid") if isinstance(data, dict) else None
            status = data.get("status") if isinstance(data, dict) else None
            msg = "Knowledge promoted."
            if kid or status:
                msg = f"Knowledge promoted (kid={kid}, status={status})."
            note = str(data.get("note") or "") if isinstance(data, dict) else ""
            return {
                "answer": _clip(msg, MAX_ANSWER_CHARS),
                "degraded": degraded,
                "used_tools": used_tools[:MAX_USED_TOOLS],
                "session_state": _safe_session_state(ctx),
                "note": _clip(note, MAX_NOTE_CHARS) if note else None,
            }

        return {
            "answer": "Knowledge promotion failed.",
            "degraded": True,
            "used_tools": used_tools[:MAX_USED_TOOLS],
            "session_state": _safe_session_state({**ctx, "degraded": True}),
            "note": _clip(str(out.get("error") or {}), MAX_NOTE_CHARS),
        }

    # knowledge.search
    if intent == "knowledge_search":
        query = _extract_prefixed_payload(user_input, patterns=[r"^\s*(?:kb|knowledge)\s*:\s*(.*)$"]) or user_input

        out = _run_tool_production(
            orch=orch,
            deps=deps,
            role=role,
            master_key=master_key,
            tool_name="knowledge.search",
            tool_args={"query": query},
            context=ctx,
            used_tools=used_tools,
        )

        if out.get("needs_approval"):
            return out["approval_envelope"]

        if not out.get("ok"):
            return {
                "answer": "Knowledge search failed or was blocked.",
                "degraded": True,
                "used_tools": used_tools[:MAX_USED_TOOLS],
                "session_state": _safe_session_state({**ctx, "degraded": True}),
                "note": _clip(str(out.get("error") or {}), MAX_NOTE_CHARS),
            }

        data = out.get("data") or {}
        results = data.get("results") if isinstance(data, dict) else None

        answer = "No knowledge results found."
        sources: List[dict] = []
        if isinstance(results, list) and results:
            top = results[0] if isinstance(results[0], dict) else {"value": str(results[0])}
            answer = str(top.get("text") or top.get("snippet") or top)
            sources = [r for r in results if isinstance(r, dict)]

        note = str(data.get("note") or "") if isinstance(data, dict) else ""
        return {
            "answer": _clip(answer, MAX_ANSWER_CHARS),
            "sources": sources[:MAX_SOURCES],
            "degraded": degraded,
            "used_tools": used_tools[:MAX_USED_TOOLS],
            "session_state": _safe_session_state(ctx),
            "note": _clip(note, MAX_NOTE_CHARS) if note else None,
        }

    # research.answer (OWNER only, online only)
    if intent == "research_answer":
        if offline:
            return {
                "answer": "Offline mode is enabled; external research is unavailable. Try knowledge search or provide local sources.",
                "degraded": True,
                "used_tools": [],
                "session_state": _safe_session_state({**ctx, "degraded": True}),
                "note": "Research blocked by offline mode (SSN_OFFLINE=1 or context.offline=True).",
            }

        if not _is_owner(role):
            return {
                "answer": "Not authorized: web research is OWNER-only.",
                "degraded": degraded,
                "used_tools": [],
                "session_state": _safe_session_state(ctx),
                "note": "Research denied due to role.",
            }

        out = _run_tool_production(
            orch=orch,
            deps=deps,
            role=role,
            master_key=master_key,
            tool_name="research.answer",
            tool_args={"query": user_input},
            context=ctx,
            used_tools=used_tools,
        )

        if out.get("needs_approval"):
            return out["approval_envelope"]

        if not out.get("ok"):
            return {
                "answer": "Research failed or was blocked (see note).",
                "degraded": True,
                "used_tools": used_tools[:MAX_USED_TOOLS],
                "session_state": _safe_session_state({**ctx, "degraded": True}),
                "note": _clip(str({"error": out.get("error")}), MAX_NOTE_CHARS),
            }

        data = out.get("data") or {}
        answer = str(data.get("answer") or "") if isinstance(data, dict) else ""
        citations = data.get("citations") if isinstance(data, dict) and isinstance(data.get("citations"), list) else []
        sources = data.get("sources") if isinstance(data, dict) and isinstance(data.get("sources"), list) else []
        degraded2 = degraded or (bool(data.get("degraded", False)) if isinstance(data, dict) else False)
        note = str(data.get("note") or "") if isinstance(data, dict) else ""

        return {
            "answer": _clip(answer, MAX_ANSWER_CHARS),
            "citations": [c for c in citations if isinstance(c, dict)][:MAX_CITATIONS],
            "sources": [s for s in sources if isinstance(s, dict)][:MAX_SOURCES],
            "degraded": degraded2,
            "used_tools": used_tools[:MAX_USED_TOOLS],
            "session_state": _safe_session_state({**ctx, "degraded": degraded2}),
            "note": _clip(note, MAX_NOTE_CHARS) if note else None,
        }

    # -------------------------
    # LLM-only path (prefer Orchestrator pipeline)
    # -------------------------
    try:
        routed = orch.run(master_key, user_input, ctx)
    except Exception:
        routed = orch.llm_route(role=role, user_input=user_input, context=ctx)

    final_msg = _extract_text(routed) or "No response produced."

    return {
        "answer": _clip(str(final_msg), MAX_ANSWER_CHARS),
        "degraded": degraded,
        "used_tools": used_tools[:MAX_USED_TOOLS],
        "session_state": _safe_session_state(ctx),
    }
