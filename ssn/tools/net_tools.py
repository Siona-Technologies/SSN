# ssn/tools/net_tools.py

from __future__ import annotations

from typing import Any, Dict, List

from ssn.tools.contracts import ToolSpec


# -----------------------------
# Helper bounds
# -----------------------------

_MAX_QUERY_LEN = 200
_MAX_URL_LEN = 500
_MAX_RESULTS = 5
_MAX_BYTES = 100_000


def _clamp_int(v: Any, *, default: int, lo: int, hi: int) -> int:
    try:
        iv = int(v)
    except Exception:
        iv = default
    return max(lo, min(iv, hi))


def _safe_str(v: Any, *, max_len: int) -> str:
    if not isinstance(v, str):
        return ""
    return v.strip()[:max_len]


# -----------------------------
# Tool handlers (placeholders)
# -----------------------------

def _net_search_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Placeholder for web search.
    No real network access yet.
    """
    query = _safe_str(args.get("query"), max_len=_MAX_QUERY_LEN)
    if not query:
        return {
            "ok": False,
            "error": {"code": "BAD_REQUEST", "message": "query is required"},
        }

    limit = _clamp_int(args.get("limit"), default=3, lo=1, hi=_MAX_RESULTS)

    return {
        "ok": True,
        "query": query,
        "limit": limit,
        "results": [],
        "note": "net.search is a placeholder; backend not wired yet",
    }


def _net_fetch_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Placeholder for bounded URL fetch.
    No real network access yet.
    """
    url = _safe_str(args.get("url"), max_len=_MAX_URL_LEN)
    if not url:
        return {
            "ok": False,
            "error": {"code": "BAD_REQUEST", "message": "url is required"},
        }

    max_bytes = _clamp_int(
        args.get("max_bytes"),
        default=_MAX_BYTES,
        lo=1_000,
        hi=_MAX_BYTES,
    )

    if not (url.startswith("http://") or url.startswith("https://")):
        return {
            "ok": False,
            "error": {"code": "INVALID_URL", "message": "Only http/https URLs allowed"},
        }

    return {
        "ok": True,
        "url": url,
        "max_bytes": max_bytes,
        "content": None,
        "note": "net.fetch is a placeholder; fetching disabled",
    }


# -----------------------------
# Registration
# -----------------------------

def register_net_tools(registry) -> None:
    """
    Register read-only, bounded network tools.
    """

    registry.register(
        ToolSpec(
            name="net.search",
            description="Search the web (read-only, bounded).",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=False,
            external_effect=False,
            max_calls_per_minute=10,
            input_schema={
                "query": {"type": "string", "required": True, "max_length": _MAX_QUERY_LEN},
                "limit": {"type": "integer", "default": 3, "min": 1, "max": _MAX_RESULTS},
            },
            handler=_net_search_handler,
        )
    )

    registry.register(
        ToolSpec(
            name="net.fetch",
            description="Fetch a URL (read-only, bounded).",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=False,
            external_effect=False,
            max_calls_per_minute=5,
            input_schema={
                "url": {"type": "string", "required": True, "max_length": _MAX_URL_LEN},
                "max_bytes": {"type": "integer", "default": _MAX_BYTES, "min": 1000, "max": _MAX_BYTES},
            },
            handler=_net_fetch_handler,
        )
    )
