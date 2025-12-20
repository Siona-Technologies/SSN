# ssn/tools/net_sanitize.py
"""
Network Sanitizer Tool — Phase 7.2.2

READ-ONLY
SAFE
OFFLINE-COMPATIBLE

Upgrades:
- Truncation-safe removal of script/style/noscript blocks (even if unclosed)
- HTML entity unescape
- CSS/boilerplate heuristics (reduces citations from stylesheet text)
- Still bounded output (max_bytes hard-capped)

Tool name: net.sanitize
Export: NET_SANITIZE_T
"""

from __future__ import annotations

import html as _html
import re
import time
from typing import Any, Dict

from ssn.tools.contracts import ToolSpec


DEFAULT_MAX_BYTES = 80_000
HARD_MAX_BYTES = 200_000


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


_CTRL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_WS_RE = re.compile(r"\s+")

# Remove blocks even if truncated (no closing tag)
# - (?is): case-insensitive + dot matches newline
_BLOCK_RE = re.compile(
    r"(?is)<(script|style|noscript)\b[^>]*>.*?(</\1\s*>|$)"
)

_COMMENT_RE = re.compile(r"(?is)<!--.*?-->")
_TAG_RE = re.compile(r"(?is)<[^>]+>")

# Heuristics to drop obvious CSS/boilerplate fragments
# (kept conservative to avoid deleting legitimate prose)
_CSS_RULE_RE = re.compile(r"(?i)\.[a-z0-9_-]{2,}\s*\{[^}]{0,500}\}")
_CSS_KV_RE = re.compile(r"(?i)\b(display|position|padding|margin|width|height|font|color|background)\s*:\s*[^;]{1,80};")
_JSONLD_HINT_RE = re.compile(r'(?i)"@context"\s*:\s*"https?://schema\.org"')


def _strip_control_chars(text: str) -> str:
    return _CTRL_CHARS_RE.sub("", text)


def _collapse_whitespace(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def _sanitize_html_to_text(html: str) -> str:
    """
    Conservative HTML-to-text that remains safe on truncated HTML.
    """
    # Remove scripts/styles/noscript even if truncated mid-block
    html = _BLOCK_RE.sub(" ", html)

    # Remove comments
    html = _COMMENT_RE.sub(" ", html)

    # Strip remaining tags
    html = _TAG_RE.sub(" ", html)

    # Unescape entities
    html = _html.unescape(html)

    # Remove control chars and collapse whitespace
    html = _strip_control_chars(html)
    html = _collapse_whitespace(html)

    # Heuristic cleanup for CSS/boilerplate that sometimes leaks in truncated pages
    html = _CSS_RULE_RE.sub(" ", html)
    html = _CSS_KV_RE.sub(" ", html)

    # Reduce schema.org JSON-LD fragments if they leak into text
    if _JSONLD_HINT_RE.search(html):
        # Keep it conservative: remove only dense brace-y regions around the hint
        # This helps when the top of the page is mostly JSON-LD.
        html = re.sub(r'(?is)\{[^{}]{0,2000}"@context"\s*:\s*"https?://schema\.org"[^{}]{0,2000}\}', " ", html)

    html = _collapse_whitespace(html)
    return html


def _sanitize_plain_text(text: str) -> str:
    text = _strip_control_chars(text)
    text = _html.unescape(text)
    text = _collapse_whitespace(text)
    return text


def _truncate_to_bytes(text: str, max_bytes: int) -> Dict[str, Any]:
    b = text.encode("utf-8", errors="replace")
    if len(b) <= max_bytes:
        return {"clean_text": text, "clean_bytes": len(b), "truncated": False}

    b2 = b[:max_bytes]
    t2 = b2.decode("utf-8", errors="ignore")
    b3 = t2.encode("utf-8", errors="replace")
    return {"clean_text": t2, "clean_bytes": len(b3), "truncated": True}


def net_sanitize_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitizes fetched content into bounded clean text.

    Args:
      - content (required, str)
      - content_type (optional, str) e.g. "text/html", "text/plain"
      - url (optional, str) passthrough metadata
      - max_bytes (optional, int) output cap (hard-capped)
    """
    content = args.get("content")
    if not isinstance(content, str) or not content.strip():
        return {"error": {"code": "INVALID_CONTENT", "message": "Missing or invalid 'content' string"}}

    content_type = args.get("content_type")
    if not isinstance(content_type, str) or not content_type.strip():
        content_type = "text/plain"

    url = args.get("url")
    if url is not None and not isinstance(url, str):
        url = None

    max_bytes = _safe_int(args.get("max_bytes"), DEFAULT_MAX_BYTES)
    max_bytes = max(1_000, min(max_bytes, HARD_MAX_BYTES))

    original_bytes = len(content.encode("utf-8", errors="replace"))

    ct = content_type.lower()
    if "html" in ct:
        cleaned = _sanitize_html_to_text(content)
    else:
        cleaned = _sanitize_plain_text(content)

    trunc = _truncate_to_bytes(cleaned, max_bytes)

    return {
        "url": url,
        "content_type": "text/plain",
        "original_content_type": content_type,
        "original_bytes": original_bytes,
        "clean_bytes": trunc["clean_bytes"],
        "clean_text": trunc["clean_text"],
        "truncated": trunc["truncated"],
        "sanitized_at": time.time(),
        "note": "net.sanitize (Phase 7.2.2, read-only, bounded; scripts/styles/noscript removed; entities decoded)",
    }


NET_SANITIZE_T = ToolSpec(
    name="net.sanitize",
    description="Sanitize fetched content into bounded clean text (read-only, safe).",
    required_role="OWNER",
    allowed_roles=("OWNER",),
    state_changing=False,
    external_effect=False,
    public=False,
    max_calls_per_minute=120,
    input_schema={
        "content": {"type": "string", "required": True, "description": "Raw fetched content to sanitize"},
        "content_type": {"type": "string", "required": False, "description": "Content type hint (e.g., text/html, text/plain)"},
        "url": {"type": "string", "required": False, "description": "Source URL (metadata passthrough)"},
        "max_bytes": {"type": "integer", "required": False, "description": "Max bytes to return for clean_text (hard capped)"},
    },
    handler=net_sanitize_handler,
)
