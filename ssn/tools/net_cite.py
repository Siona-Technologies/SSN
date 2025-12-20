# ssn/tools/net_cite.py
"""
Citation tools — Phase 7.2.3

READ-ONLY
SAFE
OFFLINE-COMPATIBLE

Purpose:
- Convert sanitized text into bounded citation objects (evidence snippets)
- Enables later summarization with traceable support
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from ssn.tools.contracts import ToolSpec


DEFAULT_MAX_QUOTES = 5
HARD_MAX_QUOTES = 10

DEFAULT_QUOTE_LEN = 240
HARD_QUOTE_LEN = 600


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _normalize_ws(text: str) -> str:
    # sanitizer should already do this, but keep it robust
    return " ".join(text.split()).strip()


def _chunk_quotes(text: str, max_quotes: int, quote_len: int) -> List[Dict[str, Any]]:
    """
    Simple deterministic chunking:
    - take sequential windows of quote_len chars from the clean text
    - store start/end offsets for traceability
    """
    citations: List[Dict[str, Any]] = []
    n = len(text)
    start = 0
    idx = 1

    while start < n and len(citations) < max_quotes:
        end = min(n, start + quote_len)
        quote = text[start:end].strip()
        if quote:
            citations.append(
                {
                    "idx": idx,
                    "start": start,
                    "end": end,
                    "quote": quote,
                }
            )
            idx += 1
        start = end

    return citations


def net_cite_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    url = args.get("url")
    if not isinstance(url, str) or not url.strip():
        return {
            "error": {
                "code": "INVALID_URL",
                "message": "Missing or invalid 'url' string",
            }
        }

    clean_text = args.get("clean_text")
    if not isinstance(clean_text, str) or not clean_text.strip():
        return {
            "error": {
                "code": "INVALID_CLEAN_TEXT",
                "message": "Missing or invalid 'clean_text' string",
            }
        }

    max_quotes = _safe_int(args.get("max_quotes"), DEFAULT_MAX_QUOTES)
    max_quotes = max(1, min(max_quotes, HARD_MAX_QUOTES))

    quote_len = _safe_int(args.get("quote_len"), DEFAULT_QUOTE_LEN)
    quote_len = max(80, min(quote_len, HARD_QUOTE_LEN))

    normalized = _normalize_ws(clean_text)

    chunks = _chunk_quotes(normalized, max_quotes=max_quotes, quote_len=quote_len)
    captured_at = time.time()

    citations: List[Dict[str, Any]] = []
    for c in chunks:
        citations.append(
            {
                "url": url,
                "idx": c["idx"],
                "start": c["start"],
                "end": c["end"],
                "quote": c["quote"],
                "captured_at": captured_at,
            }
        )

    return {
        "url": url,
        "citation_count": len(citations),
        "citations": citations,
        "cited_at": captured_at,
        "note": "net.cite (Phase 7.2.3, read-only, bounded)",
    }


NET_CITE_T = ToolSpec(
    name="net.cite",
    description="Create bounded citation snippets from sanitized text (read-only).",
    required_role="OWNER",
    allowed_roles=("OWNER",),
    state_changing=False,
    external_effect=False,
    public=False,
    max_calls_per_minute=120,
    input_schema={
        "url": {
            "type": "string",
            "required": True,
            "description": "Source URL for citations",
        },
        "clean_text": {
            "type": "string",
            "required": True,
            "description": "Sanitized clean text to cite from",
        },
        "max_quotes": {
            "type": "integer",
            "required": False,
            "description": "Max citations to produce (1–10)",
        },
        "quote_len": {
            "type": "integer",
            "required": False,
            "description": "Max length of each citation quote (80–600 chars)",
        },
    },
    handler=net_cite_handler,
)
