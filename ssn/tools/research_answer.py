# ssn/tools/research_answer.py

"""
Research Answer Tool — Phase 7.2.4 (Production Front Door)

READ-ONLY
OWNER-only
SAFE
OFFLINE-COMPATIBLE

Purpose:
- Single production entry point for "research" that composes:
  net.search -> net.fetch -> net.sanitize -> net.cite
- Returns a bounded, deterministic answer + citations + sources.

Notes:
- This tool does NOT write to memory.
- This tool does NOT perform raw HTTP itself; it calls ToolRegistry tools.
- In "strict" mode, degraded/mock search results are rejected.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from ssn.tools.contracts import ToolSpec


# ---------------------------------------------------------
# Bounds (OWNER-friendly but finite)
# ---------------------------------------------------------
DEFAULT_TOP_K = 3
HARD_TOP_K = 5

DEFAULT_FETCH_MAX_BYTES = 50_000
HARD_FETCH_MAX_BYTES = 200_000

DEFAULT_MAX_QUOTES = 3
HARD_MAX_QUOTES = 10

DEFAULT_QUOTE_LEN = 240
HARD_QUOTE_LEN = 600

DEFAULT_MAX_ANSWER_CHARS = 800
HARD_MAX_ANSWER_CHARS = 2000

DEFAULT_TIMEOUT_S = 10
HARD_TIMEOUT_S = 20


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("1", "true", "yes", "y", "on"):
            return True
        if v in ("0", "false", "no", "n", "off"):
            return False
    return default


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(value, hi))


def _truncate(text: str, max_chars: int) -> Tuple[str, bool]:
    if not isinstance(text, str):
        return "", False
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def _get_tool_runner(deps: Dict[str, Any]) -> Any:
    """
    Expect either:
      deps["tools"] -> ToolRegistry
    Fallback:
      deps["tool_registry"] -> ToolRegistry
    """
    tr = deps.get("tools") or deps.get("tool_registry")
    if tr is None:
        raise RuntimeError("research.answer requires deps['tools'] (ToolRegistry).")
    return tr


def _run_tool(
    registry: Any,
    *,
    name: str,
    role: str,
    deps: Dict[str, Any],
    args: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Calls ToolRegistry.run(...) and returns its data dict.
    Expects a ToolResult-like object with .ok/.data/.error.
    """
    tr = registry.run(name=name, role=role, deps=deps, args=args)

    if not getattr(tr, "ok", False):
        err = getattr(tr, "error", None) or {"code": "TOOL_FAILED", "message": f"{name} failed"}
        raise RuntimeError(f"{name} failed: {err}")

    data = getattr(tr, "data", None)
    if not isinstance(data, dict):
        raise RuntimeError(f"{name} returned non-dict data")
    return data


def _build_extractive_answer(sanitized_texts: List[str], max_chars: int) -> Dict[str, Any]:
    """
    Deterministic extractive "answer":
    - take the first N chars from the concatenated sanitized texts.
    - intentionally non-LLM for Phase 7.2: safe, testable, predictable.
    """
    joined = " ".join(t for t in sanitized_texts if isinstance(t, str) and t.strip()).strip()
    if not joined:
        return {"answer": "", "truncated": False}

    ans, truncated = _truncate(joined, max_chars)
    return {"answer": ans, "truncated": truncated}


def research_answer_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    # Validate input
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {"error": {"code": "INVALID_QUERY", "message": "Missing or invalid 'query'"}}
    query = query.strip()

    top_k = _clamp(_safe_int(args.get("top_k"), DEFAULT_TOP_K), 1, HARD_TOP_K)
    fetch_max_bytes = _clamp(_safe_int(args.get("max_bytes"), DEFAULT_FETCH_MAX_BYTES), 1000, HARD_FETCH_MAX_BYTES)

    max_quotes = _clamp(_safe_int(args.get("max_quotes"), DEFAULT_MAX_QUOTES), 1, HARD_MAX_QUOTES)
    quote_len = _clamp(_safe_int(args.get("quote_len"), DEFAULT_QUOTE_LEN), 80, HARD_QUOTE_LEN)

    max_answer_chars = _clamp(_safe_int(args.get("max_answer_chars"), DEFAULT_MAX_ANSWER_CHARS), 200, HARD_MAX_ANSWER_CHARS)

    timeout_s = float(_clamp(_safe_int(args.get("timeout_s"), DEFAULT_TIMEOUT_S), 2, HARD_TIMEOUT_S))

    # Live/strict/degraded controls (args override env inside net.search)
    live = _safe_bool(args.get("live"), default=False) if "live" in args else None
    strict = _safe_bool(args.get("strict"), default=False) if "strict" in args else None
    allow_degraded = _safe_bool(args.get("allow_degraded"), default=False)

    role = deps.get("role")
    if not isinstance(role, str):
        role = "OWNER"

    registry = _get_tool_runner(deps)
    started_at = time.time()

    # 1) net.search
    search_args: Dict[str, Any] = {"query": query, "top_k": top_k, "timeout_s": int(timeout_s)}
    if live is not None:
        search_args["live"] = live
    if strict is not None:
        search_args["strict"] = strict

    try:
        search_data = _run_tool(registry, name="net.search", role=role, deps=deps, args=search_args)
    except Exception as e:
        return {"error": {"code": "SEARCH_FAILED", "message": str(e)}}

    results = search_data.get("results", [])
    degraded_search = bool(search_data.get("degraded", False)) or (search_data.get("provider") == "mock-search")

    if degraded_search and not allow_degraded:
        # If caller asked strict or environment is strict-live, net.search may already error.
        # This is the additional guard for cases where net.search fell back to mock.
        if strict is True:
            return {
                "error": {
                    "code": "DEGRADED_RESULTS_BLOCKED",
                    "message": "Search results were degraded/mock; refusing to answer in strict mode. Set allow_degraded=True to override explicitly.",
                }
            }

    if not isinstance(results, list) or not results:
        return {
            "query": query,
            "answer": "",
            "answer_truncated": False,
            "sources": [],
            "citations": [],
            "degraded": degraded_search,
            "note": "No search results",
            "answered_at": time.time(),
            "elapsed_ms": int((time.time() - started_at) * 1000),
        }

    # 2) net.fetch -> 3) net.sanitize -> 4) net.cite
    sources: List[Dict[str, Any]] = []
    all_citations: List[Dict[str, Any]] = []
    sanitized_texts: List[str] = []

    fetch_failures = 0
    max_failures = top_k  # bound failures; still try others

    for r in results[:top_k]:
        if fetch_failures >= max_failures:
            break

        url = r.get("url")
        if not isinstance(url, str) or not url.strip():
            continue
        url = url.strip()

        title = r.get("title") if isinstance(r.get("title"), str) else ""
        snippet = r.get("snippet") if isinstance(r.get("snippet"), str) else ""
        retrieved_at = r.get("retrieved_at")  # may be float/time.time()
        try:
            retrieved_at_f = float(retrieved_at) if retrieved_at is not None else None
        except Exception:
            retrieved_at_f = None

        # fetch
        try:
            fetch_data = _run_tool(
                registry,
                name="net.fetch",
                role=role,
                deps=deps,
                args={"url": url, "max_bytes": fetch_max_bytes, "timeout_s": int(timeout_s)},
            )
        except Exception:
            fetch_failures += 1
            continue

        content_type = fetch_data.get("content_type", "text/plain")
        content = fetch_data.get("content", "")

        # sanitize
        try:
            sanitize_data = _run_tool(
                registry,
                name="net.sanitize",
                role=role,
                deps=deps,
                args={
                    "url": url,
                    "content_type": content_type,
                    "content": content,
                    "max_bytes": fetch_max_bytes,
                },
            )
        except Exception:
            fetch_failures += 1
            continue

        clean_text = sanitize_data.get("clean_text", "")
        if isinstance(clean_text, str) and clean_text.strip():
            sanitized_texts.append(clean_text)

        # cite (pass richer metadata if net.cite supports it; harmless if ignored)
        cite_args: Dict[str, Any] = {
            "url": url,
            "clean_text": clean_text,
            "max_quotes": max_quotes,
            "quote_len": quote_len,
        }
        # optional metadata for citation-grade outputs
        cite_args["title"] = title
        cite_args["snippet"] = snippet
        if retrieved_at_f is not None:
            cite_args["retrieved_at"] = retrieved_at_f
        cite_args["content_type"] = content_type

        try:
            cite_data = _run_tool(registry, name="net.cite", role=role, deps=deps, args=cite_args)
            citations = cite_data.get("citations", [])
            if isinstance(citations, list):
                all_citations.extend([c for c in citations if isinstance(c, dict)])
        except Exception:
            # citation is helpful but not required to produce an answer
            pass

        sources.append(
            {
                "url": url,
                "title": title,
                "snippet": snippet,
                "retrieved_at": retrieved_at_f,
                "provider": search_data.get("provider"),
            }
        )

    # Build deterministic answer (even if citations partially missing)
    ans = _build_extractive_answer(sanitized_texts, max_chars=max_answer_chars)

    return {
        "query": query,
        "answer": ans["answer"],
        "answer_truncated": ans["truncated"],
        "sources": sources,
        "citations": all_citations[: max_quotes * top_k],  # hard bound
        "degraded": bool(degraded_search),
        "answered_at": time.time(),
        "elapsed_ms": int((time.time() - started_at) * 1000),
        "note": "research.answer (Phase 7.2.4, composed, read-only)",
    }


RESEARCH_ANSWER_T = ToolSpec(
    name="research.answer",
    description="Answer a query using composed net.* pipeline (read-only, OWNER-only).",
    required_role="OWNER",
    allowed_roles=("OWNER",),
    state_changing=False,
    # IMPORTANT: the wrapper triggers external-effect tools (net.search/net.fetch),
    # so mark as external_effect=True for conservative policy gating.
    external_effect=True,
    public=False,
    max_calls_per_minute=60,
    input_schema={
        "query": {"type": "string", "required": True, "description": "Question or research query"},
        "top_k": {"type": "integer", "required": False, "description": "Number of sources (1–5)"},
        "max_bytes": {"type": "integer", "required": False, "description": "Max bytes per fetch/sanitize (bounded)"},
        "timeout_s": {"type": "integer", "required": False, "description": "Timeout seconds (2–20)"},
        "max_quotes": {"type": "integer", "required": False, "description": "Max citations per source (1–10)"},
        "quote_len": {"type": "integer", "required": False, "description": "Citation quote length (80–600 chars)"},
        "max_answer_chars": {"type": "integer", "required": False, "description": "Max answer characters (200–2000)"},
        "live": {"type": "boolean", "required": False, "description": "Pass-through to net.search live mode (args override env)"},
        "strict": {"type": "boolean", "required": False, "description": "Pass-through to net.search strict-live (args override env)"},
        "allow_degraded": {"type": "boolean", "required": False, "description": "Allow degraded/mock search results (default False)"},
    },
    handler=research_answer_handler,
)
