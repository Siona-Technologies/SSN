# ssn/tools/research_ingest.py

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from ssn.tools.contracts import ToolSpec


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

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


def _truncate_text(text: Any, max_chars: int) -> str:
    if not isinstance(text, str):
        return ""
    if max_chars <= 0:
        return ""
    return text[:max_chars]


def _tool_fail(step: str, tool_err: Any, fallback_code: str) -> Dict[str, Any]:
    """
    Normalize tool failure into a single error payload for research.ingest.
    """
    if isinstance(tool_err, dict) and tool_err.get("code"):
        return {"error": {"step": step, **tool_err}}
    return {"error": {"step": step, "code": fallback_code, "message": f"{step} failed"}}


def _compute_degraded(
    *,
    forced_offline: bool,
    search_data: Dict[str, Any],
    chosen: Dict[str, Any],
    url: str,
) -> bool:
    """
    Degraded means: we did NOT get real web search results; we used mock/fallback
    or we are operating in forced offline mode.
    """
    if forced_offline:
        return True

    try:
        if isinstance(search_data, dict) and bool(search_data.get("degraded", False)):
            return True
    except Exception:
        pass

    try:
        provider = str((search_data or {}).get("provider", "") or "").strip().lower()
        if provider == "mock-search":
            return True
    except Exception:
        pass

    try:
        src = str((chosen or {}).get("source", "") or "").strip().lower()
        if src == "mock-search":
            return True
    except Exception:
        pass

    try:
        if "example.com" in (url or "").lower():
            return True
    except Exception:
        pass

    return False


def _arg_provided(args: Dict[str, Any], *names: str) -> bool:
    return any(n in args for n in names)


# ---------------------------------------------------------
# Disambiguation (project-aware)
# ---------------------------------------------------------

def _looks_like_siona_project_query(q: str) -> bool:
    s = (q or "").lower()
    if "siona" in s:
        return True
    if "ssn" in s and ("system" in s or "hybrid" in s or "brain" in s or "samson" in s):
        return True
    if "samson" in s or "sibona" in s or "njaji" in s:
        return True
    if "jarvis" in s and ("ssn" in s or "siona" in s):
        return True
    return False


def _build_siona_disambiguated_query(q: str) -> str:
    """
    This is ONLY the query sent to net.search (effective_query).
    We still return the ORIGINAL query for API stability.
    """
    q = (q or "").strip()

    must = (
        '"SIONA" '
        '"Samson Sibona Njaji" '
        '"Hybrid Human-Like Brain" '
        '"SSN"'
    )

    excludes = (
        '-"social security" -ssa.gov -investopedia -moneydigest -einvestigator '
        '-"social security number" -wikipedia '
        '-nvlabs -sionna -"communication systems" -"ray tracer"'
    )

    return f"{must} {q} {excludes}".strip()


# ---------------------------------------------------------
# Result scoring / selection
# ---------------------------------------------------------

_BAD_TERMS = (
    "social security",
    "social security number",
    "ssa.gov",
    "investopedia",
    "moneydigest",
    "einvestigator",
    "wikipedia.org/wiki/social_security_number",
    "nvlabs",
    "github.com/nvlabs/sionna",
    "nvlabs.github.io/sionna",
    "ray tracer",
    "communication systems",
)

_GOOD_TERMS = (
    "siona",
    "samson",
    "sibona",
    "njaji",
    "hybrid human-like brain",
    "law-bound",
    "owner-bound",
    "toolregistry",
    "orchestrator",
    "memoryhub",
    "brainrouter",
    "bootstrap",
    "blueprint",
)


def _score_result(r: Dict[str, Any], query: str, *, project_disambiguation: bool) -> float:
    title = str(r.get("title", "")).lower()
    url = str(r.get("url", "")).lower()
    snippet = str(r.get("snippet", "")).lower()
    blob = f"{title} {url} {snippet}"

    score = 0.0

    # Generic scoring (always)
    if url.startswith("https://"):
        score += 0.4
    if snippet.strip():
        score += 0.2

    # Token overlap with query (always)
    q_tokens = [tok for tok in query.lower().split() if len(tok) >= 4]
    for tok in q_tokens[:12]:
        if tok in blob:
            score += 0.25

    # SSN/SIONA disambiguation scoring (ONLY when disambiguating)
    if project_disambiguation:
        for t in _BAD_TERMS:
            if t in blob:
                score -= 4.0
        for t in _GOOD_TERMS:
            if t in blob:
                score += 2.0

    return score


def _choose_best_result(results: List[Dict[str, Any]], query: str, *, project_disambiguation: bool) -> Optional[Dict[str, Any]]:
    best: Optional[Dict[str, Any]] = None
    best_score = float("-inf")
    for r in results:
        if not isinstance(r, dict):
            continue
        if not isinstance(r.get("url"), str):
            continue
        s = _score_result(r, query, project_disambiguation=project_disambiguation)
        if s > best_score:
            best_score = s
            best = r
    return best


def _extract_relevant_window(clean_text: str, *, max_chars: int = 20_000) -> str:
    if not isinstance(clean_text, str) or not clean_text.strip():
        return ""
    txt = clean_text.strip()
    lower = txt.lower()

    anchors = []
    for a in ("siona", "samson", "sibona", "njaji", "owner-bound", "law-bound", "hybrid"):
        i = lower.find(a)
        if i >= 0:
            anchors.append(i)

    if anchors:
        start = max(0, min(anchors) - 500)
        return txt[start: start + max_chars]

    return txt[:max_chars]


# ---------------------------------------------------------
# research.ingest handler
# ---------------------------------------------------------

def research_ingest_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    research.ingest (Phase 7.2)

    Pipeline:
      net.search -> net.fetch -> net.sanitize -> net.cite

    Returns:
      A bounded ingest bundle (NO memory writes).

    NOTE (important):
    - We DO NOT force live search by default.
      net.search owns default behavior (offline-safe mock unless env/args enable live).
    """
    tools = deps.get("tools")
    if tools is None:
        return {"error": {"code": "MISSING_DEPS", "message": "deps['tools'] is required"}}

    role = deps.get("role", "OWNER")

    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {"error": {"code": "INVALID_QUERY", "message": "Missing or invalid 'query'"}}
    original_query = query.strip()

    top_k = _safe_int(args.get("top_k"), 3)
    top_k = max(1, min(top_k, 5))

    max_bytes = _safe_int(args.get("max_bytes"), 50_000)
    max_bytes = max(1_000, min(max_bytes, 200_000))

    max_answer_chars = _safe_int(args.get("max_answer_chars"), 600)
    max_answer_chars = max(100, min(max_answer_chars, 2000))

    # Network controls
    timeout_s = float(_safe_int(args.get("timeout_s"), 10))
    timeout_s = max(2.0, min(timeout_s, 20.0))

    forced_offline = os.getenv("SSN_OFFLINE") == "1"

    # Disambiguation (only changes effective_query, not returned query)
    disambiguate_default = _looks_like_siona_project_query(original_query)
    disambiguate = _safe_bool(args.get("disambiguate"), default=disambiguate_default)
    effective_query = _build_siona_disambiguated_query(original_query) if disambiguate else original_query

    # Decide whether to override net.search live/strict:
    # - If user provided live_search/live, we pass it through.
    # - Else, we OMIT live so net.search can use its env-driven default.
    # - If SSN_OFFLINE=1, we force live=False and strict=False.
    search_args: Dict[str, Any] = {
        "query": effective_query,
        "top_k": top_k,
        "timeout_s": int(timeout_s),
    }

    if forced_offline:
        search_args["live"] = False
        search_args["strict"] = False
    else:
        if _arg_provided(args, "live_search", "live"):
            live_val = _safe_bool(args.get("live_search", args.get("live")), default=False)
            search_args["live"] = live_val
        if _arg_provided(args, "strict_live", "strict"):
            strict_val = _safe_bool(args.get("strict_live", args.get("strict")), default=False)
            search_args["strict"] = strict_val

    # --------------------------
    # 1) net.search
    # --------------------------
    sr = tools.run(
        name="net.search",
        role=role,
        deps=deps,
        args=search_args,
    )
    if not sr.ok:
        return _tool_fail("net.search", sr.error, "SEARCH_FAILED")

    search_data = sr.data or {}
    results: List[Dict[str, Any]] = list(search_data.get("results") or [])
    if not results:
        return {"error": {"step": "net.search", "code": "NO_RESULTS", "message": "No results returned"}}

    chosen = _choose_best_result(results, effective_query, project_disambiguation=bool(disambiguate)) or (
        results[0] if isinstance(results[0], dict) else {}
    )
    url = chosen.get("url")
    if not isinstance(url, str) or not url.strip():
        return {"error": {"step": "net.search", "code": "NO_URL", "message": "Selected result missing url"}}
    url = url.strip()

    degraded = _compute_degraded(
        forced_offline=forced_offline,
        search_data=search_data if isinstance(search_data, dict) else {},
        chosen=chosen if isinstance(chosen, dict) else {},
        url=url,
    )

    # --------------------------
    # 2) net.fetch
    # --------------------------
    fr = tools.run(
        name="net.fetch",
        role=role,
        deps=deps,
        args={
            "url": url,
            "max_bytes": max_bytes,
            "timeout_s": int(timeout_s),
        },
    )
    if not fr.ok:
        return _tool_fail("net.fetch", fr.error, "FETCH_FAILED")

    fetch_data = fr.data or {}
    fetched_content = fetch_data.get("content", "")
    fetched_ct = fetch_data.get("content_type", "application/octet-stream")

    # --------------------------
    # 3) net.sanitize
    # --------------------------
    san = tools.run(
        name="net.sanitize",
        role=role,
        deps=deps,
        args={
            "content": fetched_content,
            "content_type": fetched_ct,
            "url": url,
            "max_bytes": min(max_bytes, 120_000),
        },
    )
    if not san.ok:
        return _tool_fail("net.sanitize", san.error, "SANITIZE_FAILED")

    sanitize_data = san.data or {}
    clean_text = sanitize_data.get("clean_text") or ""
    if not isinstance(clean_text, str) or not clean_text.strip():
        return {
            "error": {
                "step": "net.sanitize",
                "code": "EMPTY_CLEAN_TEXT",
                "message": "Sanitizer produced empty text",
            }
        }

    # --------------------------
    # 4) net.cite
    # --------------------------
    clean_for_cite = _extract_relevant_window(clean_text, max_chars=20_000) or clean_text[:20_000]

    cite = tools.run(
        name="net.cite",
        role=role,
        deps=deps,
        args={
            "url": url,
            "clean_text": clean_for_cite,
            "title": chosen.get("title"),
            "snippet": chosen.get("snippet"),
            "retrieved_at": chosen.get("retrieved_at"),
            "content_type": "text/plain",
        },
    )
    if not cite.ok:
        return _tool_fail("net.cite", cite.error, "CITE_FAILED")

    cite_data = cite.data or {}

    # --------------------------
    # Bounded answer (extractive, deterministic)
    # --------------------------
    answer = _truncate_text(_extract_relevant_window(clean_text, max_chars=max_answer_chars), max_answer_chars).strip()
    if not answer:
        answer = _truncate_text(clean_text, max_answer_chars).strip()

    return {
        "query": original_query,
        "effective_query": effective_query,
        "disambiguated": bool(disambiguate),

        "selected_source": {
            "title": chosen.get("title"),
            "url": url,
            "snippet": chosen.get("snippet"),
            "source": chosen.get("source"),
        },

        "search": {
            "provider": search_data.get("provider"),
            "providers_tried": search_data.get("providers_tried"),
            "degraded": bool(degraded),
            "result_count": search_data.get("result_count"),
            "results": results[:top_k],
            "note": search_data.get("note"),
        },

        "fetch": {
            "url": fetch_data.get("url"),
            "content_type": fetch_data.get("content_type"),
            "content_bytes": fetch_data.get("content_bytes"),
            "fetched_at": fetch_data.get("fetched_at"),
            "truncated": fetch_data.get("truncated", False),
        },

        "sanitize": {
            "content_type": sanitize_data.get("content_type"),
            "note": sanitize_data.get("note"),
            "truncated": sanitize_data.get("truncated"),
            "clean_bytes": sanitize_data.get("clean_bytes"),
        },

        "cite": cite_data,
        "answer": answer,
        "ingested_at": time.time(),
        "offline": bool(forced_offline),
        "degraded": bool(degraded),
    }


# ---------------------------------------------------------
# ToolSpec registration
# ---------------------------------------------------------

RESEARCH_INGEST_T = ToolSpec(
    name="research.ingest",
    description="Run net.* pipeline (search→fetch→sanitize→cite) and return an ingest bundle (OWNER-only).",
    required_role="OWNER",
    allowed_roles=("OWNER",),
    state_changing=False,
    external_effect=True,
    public=False,
    max_calls_per_minute=30,
    input_schema={
        "query": {"type": "string", "required": True, "description": "Research query to ingest"},
        "top_k": {"type": "integer", "required": False, "description": "Results to consider (1–5)"},
        "max_bytes": {"type": "integer", "required": False, "description": "Fetch cap (hard capped)"},
        "max_answer_chars": {"type": "integer", "required": False, "description": "Answer cap (100–2000)"},
        # compatibility: user can pass either live_search/strict_live OR live/strict
        "live_search": {"type": "boolean", "required": False, "description": "Override: request live search (otherwise net.search uses env/default)"},
        "strict_live": {"type": "boolean", "required": False, "description": "Override: strict live (otherwise net.search uses env/default)"},
        "live": {"type": "boolean", "required": False, "description": "Alias for live_search"},
        "strict": {"type": "boolean", "required": False, "description": "Alias for strict_live"},
        "timeout_s": {"type": "integer", "required": False, "description": "Network timeout seconds (2–20)"},
        "disambiguate": {"type": "boolean", "required": False, "description": "Disambiguate SIONA/SSN project vs Social Security (default auto)"},
    },
    handler=research_ingest_handler,
)
