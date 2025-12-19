from __future__ import annotations

import time
from typing import Any, Dict

from ssn.tools.contracts import ToolSpec


def internet_research_handler(
    deps: Dict[str, Any],
    args: Dict[str, Any],
) -> Dict[str, Any]:
    """
    READ-ONLY internet research tool.

    SAFE + OFFLINE-COMPATIBLE mock.
    Allows full pipeline testing before real web access is enabled.

    Future replacements:
      - Web search API
      - Crawler
      - RAG connector
    """

    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {
            "error": {
                "code": "INVALID_QUERY",
                "message": "Missing or invalid 'query' string",
            }
        }

    # --- Simulated research result (bounded, safe) ---
    simulated_sources = [
        {
            "title": "Example Research Source",
            "url": "https://example.com/research",
            "snippet": "This is a simulated research result used for pipeline testing.",
        }
    ]

    return {
        "query": query,
        "timestamp": time.time(),
        "results": simulated_sources,
        "note": "Simulated internet research (Phase 4.3, read-only)",
    }


# ==================================================
# CANONICAL TOOL SPEC (SOURCE OF TRUTH)
# ==================================================
INTERNET_RESEARCH_T = ToolSpec(
    name="internet_research",
    description="Read-only internet research tool (search, facts, summaries).",
    required_role="OWNER",
    allowed_roles=("OWNER",),
    state_changing=False,
    external_effect=True,   # external knowledge access
    public=False,
    max_calls_per_minute=5,
    input_schema={
        "query": {
            "type": "string",
            "description": "Search query or research question",
            "required": True,
        }
    },
    handler=internet_research_handler,
)

# --------------------------------------------------
# BACKWARD-COMPATIBILITY ALIAS (DO NOT REMOVE)
# --------------------------------------------------
INTERNET_RESEARCH_TOOL = INTERNET_RESEARCH_T
