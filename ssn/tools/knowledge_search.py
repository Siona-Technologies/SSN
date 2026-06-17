# ssn/tools/knowledge_search.py

from __future__ import annotations

from typing import Any, Dict

from ssn.tools.contracts import ToolSpec
from ssn.knowledge.store import KnowledgeStore


def _safe_int(x: Any, default: int) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _safe_bool(x: Any, default: bool = False) -> bool:
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        v = x.strip().lower()
        if v in ("1", "true", "yes", "y", "on"):
            return True
        if v in ("0", "false", "no", "n", "off"):
            return False
    return default


def knowledge_search_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    role = deps.get("role") or "OWNER"
    if role != "OWNER":
        return {"error": {"code": "FORBIDDEN", "message": "knowledge.search is OWNER-only"}}

    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {"error": {"code": "INVALID_QUERY", "message": "Missing or invalid 'query'"}}

    top_k = max(1, min(_safe_int(args.get("top_k"), 5), 25))
    scan_limit = max(1, min(_safe_int(args.get("scan_limit"), 500), 5000))
    include_text = _safe_bool(args.get("include_text"), default=False)
    snippet_chars = max(80, min(_safe_int(args.get("snippet_chars"), 260), 800))

    ks = KnowledgeStore()
    sr = ks.search(
        query=query.strip(),
        top_k=top_k,
        scan_limit=scan_limit,
        include_text=include_text,
        snippet_chars=snippet_chars,
    )

    if not sr.get("ok", False):
        return {"error": sr.get("error") or {"code": "SEARCH_FAILED", "message": "Knowledge search failed"}}

    return {
        "query": query.strip(),
        "results": sr.get("results", []),
        "scanned": sr.get("scanned", 0),
        "note": "knowledge.search (Phase 5 RAG, local-only, bounded)",
    }


KNOWLEDGE_SEARCH_T = ToolSpec(
    name="knowledge.search",
    description="Search local curated knowledge store (OWNER-only, read-only).",
    required_role="OWNER",
    allowed_roles=("OWNER",),
    state_changing=False,
    external_effect=False,
    public=False,
    max_calls_per_minute=120,
    input_schema={
        "query": {"type": "string", "required": True, "description": "Search query"},
        "top_k": {"type": "integer", "required": False, "description": "Max results (1–25)"},
        "scan_limit": {"type": "integer", "required": False, "description": "Max records scanned (1–5000)"},
        "include_text": {"type": "boolean", "required": False, "description": "Include full text in results"},
        "snippet_chars": {"type": "integer", "required": False, "description": "Snippet length (80–800 chars)"},
    },
    handler=knowledge_search_handler,
)
