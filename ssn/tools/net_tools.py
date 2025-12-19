"""
Network tools — Phase 7.2.1

READ-ONLY
SAFE
OFFLINE-COMPATIBLE

Live HTTP fetching will be added in Phase 7.2.2
after sanitization + citation pipeline exists.
"""

from __future__ import annotations
import time
from typing import Any, Dict, List

from ssn.tools.contracts import ToolSpec


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _sanitize_text(text: str, *, max_len: int = 500) -> str:
    if not isinstance(text, str):
        return ""
    text = text.replace("\n", " ").strip()
    return text[:max_len]


# ---------------------------------------------------------
# net.search handler (MOCK / SAFE)
# ---------------------------------------------------------

def net_search_handler(
    deps: Dict[str, Any],
    args: Dict[str, Any],
) -> Dict[str, Any]:
    """
    READ-ONLY network search (simulated).

    ✔ OWNER only
    ✔ Bounded
    ✔ Deterministic
    ✔ Offline-safe
    """

    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {
            "error": {
                "code": "INVALID_QUERY",
                "message": "Missing or invalid 'query' string",
            }
        }

    top_k = _safe_int(args.get("top_k"), 5)
    top_k = max(1, min(top_k, 10))

    # -------------------------------------------------
    # Simulated results (placeholder for live search)
    # -------------------------------------------------
    results: List[Dict[str, Any]] = []

    for i in range(top_k):
        results.append(
            {
                "title": _sanitize_text(
                    f"Simulated search result {i + 1} for '{query}'",
                    max_len=120,
                ),
                "url": f"https://example.com/search/{query.replace(' ', '_')}/{i + 1}",
                "snippet": _sanitize_text(
                    "This is a simulated search result used for safe pipeline testing.",
                    max_len=300,
                ),
                "source": "mock-search",
                "retrieved_at": time.time(),
            }
        )

    return {
        "query": query,
        "result_count": len(results),
        "results": results,
        "note": "Simulated net.search (offline-safe, Phase 7.2.1)",
    }


# ---------------------------------------------------------
# ToolSpec registration
# ---------------------------------------------------------

NET_SEARCH_T = ToolSpec(
    name="net.search",
    description="Read-only network search (safe, bounded, offline-compatible).",
    required_role="OWNER",
    allowed_roles=("OWNER",),
    state_changing=False,
    external_effect=True,   # network knowledge
    public=False,

    # OWNER-friendly but bounded
    max_calls_per_minute=60,

    input_schema={
        "query": {
            "type": "string",
            "required": True,
            "description": "Search query",
        },
        "top_k": {
            "type": "integer",
            "required": False,
            "description": "Number of results (1–10)",
        },
    },

    handler=net_search_handler,
)
