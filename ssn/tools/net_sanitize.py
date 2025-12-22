# ssn/tools/net_sanitize.py
"""
Network Sanitizer Tool — Phase 7.2.2 (Production hardened)

READ-ONLY
SAFE
OFFLINE-COMPATIBLE

Goals:
- Truncation-safe removal of script/style/noscript + comments
- HTML entity unescape
- Prefer extracting "main-like" content when possible (still stdlib-only)
- Boilerplate heuristics (cookie/nav/footer/auth/share) to improve citations
- Bounded output (max_bytes hard-capped)

Tool name: net.sanitize
Export: NET_SANITIZE_T
"""

from __future__ import annotations

import html as _html
import re
import time
from typing import Any, Dict, List, Tuple

from ssn.tools.contracts import ToolSpec


DEFAULT_MAX_BYTES = 80_000
HARD_MAX_BYTES = 200_000

DEFAULT_MAX_TEXT_CHARS = 200_000  # internal safety; output is bounded by max_bytes


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


# ---------------------------------------------------------
# Regex & heuristics
# ---------------------------------------------------------

_CTRL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_WS_RE = re.compile(r"\s+")

# Remove blocks even if truncated (no closing tag)
_BLOCK_RE = re.compile(r"(?is)<(script|style|noscript)\b[^>]*>.*?(</\1\s*>|$)")
_COMMENT_RE = re.compile(r"(?is)<!--.*?-->")

# Remove some head-ish noise
_HEAD_RE = re.compile(r"(?is)<head\b[^>]*>.*?(</head\s*>|$)")

# Remove obvious non-content containers (conservative)
_DROP_BLOCKS_RE = re.compile(
    r"(?is)<(nav|footer|aside|form)\b[^>]*>.*?(</\1\s*>|$)"
)

# Generic tag strip (applied late)
_TAG_RE = re.compile(r"(?is)<[^>]+>")

# HTML line-break-ish tags to preserve paragraph boundaries before stripping
_BREAK_TAG_RE = re.compile(r"(?is)</(p|div|li|h1|h2|h3|h4|h5|h6|br|tr|section|article)\s*>")

# Heuristics to drop CSS/boilerplate fragments that sometimes leak in truncated pages
_CSS_RULE_RE = re.compile(r"(?i)\.[a-z0-9_-]{2,}\s*\{[^}]{0,800}\}")
_CSS_KV_RE = re.compile(
    r"(?i)\b(display|position|padding|margin|width|height|font|color|background|grid|flex)\s*:\s*[^;]{1,100};"
)
_JSONLD_HINT_RE = re.compile(r'(?i)"@context"\s*:\s*"https?://schema\.org"')

# Boilerplate detection (text-level)
_BOILERPLATE_NEEDLES = (
    "cookie",
    "cookies",
    "consent",
    "privacy policy",
    "terms of service",
    "terms and conditions",
    "sign in",
    "log in",
    "create account",
    "subscribe",
    "newsletter",
    "all rights reserved",
    "navigation",
    "menu",
    "share",
    "follow us",
    "accept all",
    "reject all",
    "advert",
    "advertisement",
    "skip to content",
    "jump to content",
)


def _strip_control_chars(text: str) -> str:
    return _CTRL_CHARS_RE.sub("", text)


def _collapse_whitespace(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def _normalize_preserve_paragraphs(text: str) -> str:
    """
    Keep paragraph breaks so downstream cite can pick coherent segments.
    """
    if not isinstance(text, str):
        return ""

    t = text.replace("\r", "\n")
    t = re.sub(r"\n{3,}", "\n\n", t)

    lines: List[str] = []
    for line in t.split("\n"):
        line = _WS_RE.sub(" ", line).strip()
        lines.append(line)

    t = "\n".join(lines)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    return t


def _strip_tags_keep_breaks(html: str) -> str:
    """
    Convert break-ish tags to newlines before stripping tags, to preserve structure.
    """
    html = _BREAK_TAG_RE.sub("\n", html)
    html = _TAG_RE.sub(" ", html)
    return html


def _extract_main_like_html(html: str) -> str:
    """
    Best-effort extraction:
    - Prefer <main>...</main> if present
    - Else prefer <article>...</article>
    - Else prefer <body>...</body>
    - Else keep full html
    Truncation-safe via regex that tolerates missing close tags.
    """
    if not isinstance(html, str) or not html:
        return ""

    patterns = [
        re.compile(r"(?is)<main\b[^>]*>.*?(</main\s*>|$)"),
        re.compile(r"(?is)<article\b[^>]*>.*?(</article\s*>|$)"),
        re.compile(r"(?is)<body\b[^>]*>.*?(</body\s*>|$)"),
    ]
    for rx in patterns:
        m = rx.search(html)
        if m:
            return m.group(0)
    return html


def _drop_boilerplate_lines(text: str) -> str:
    """
    Remove lines that look like nav/cookie/auth boilerplate.
    Conservative: only drops short-ish lines with boilerplate needles.
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    out_lines: List[str] = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue

        low = line.lower()

        # very short lines that contain boilerplate needles are usually junk
        if len(line) <= 140 and any(n in low for n in _BOILERPLATE_NEEDLES):
            continue

        # button-like / menu-like fragments
        if len(line) <= 50 and low in ("home", "about", "contact", "privacy", "terms", "login", "sign in", "menu"):
            continue

        out_lines.append(line)

    # rejoin, preserving paragraphs
    t = "\n".join(out_lines)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    return t


def _sanitize_html_to_text(html: str) -> str:
    """
    Conservative HTML-to-text that remains safe on truncated HTML.
    """
    html = html[:DEFAULT_MAX_TEXT_CHARS]

    # Best-effort select main content region first
    html = _extract_main_like_html(html)

    # Remove scripts/styles/noscript even if truncated mid-block
    html = _BLOCK_RE.sub(" ", html)

    # Remove <head> (common huge noise)
    html = _HEAD_RE.sub(" ", html)

    # Remove comments
    html = _COMMENT_RE.sub(" ", html)

    # Drop some common non-content blocks
    html = _DROP_BLOCKS_RE.sub(" ", html)

    # Convert break-ish tags to newlines, then strip tags
    txt = _strip_tags_keep_breaks(html)

    # Unescape entities
    txt = _html.unescape(txt)

    # Remove control chars
    txt = _strip_control_chars(txt)

    # Remove CSS-ish leakage
    txt = _CSS_RULE_RE.sub(" ", txt)
    txt = _CSS_KV_RE.sub(" ", txt)

    # Reduce schema.org JSON-LD fragments if they leak into text
    if _JSONLD_HINT_RE.search(txt):
        txt = re.sub(
            r'(?is)\{[^{}]{0,2500}"@context"\s*:\s*"https?://schema\.org"[^{}]{0,2500}\}',
            " ",
            txt,
        )

    # Normalize whitespace but preserve paragraphs
    txt = _normalize_preserve_paragraphs(txt)

    # Drop obvious boilerplate lines
    txt = _drop_boilerplate_lines(txt)

    # Final compacting: collapse intra-line whitespace while keeping paragraph breaks
    # (normalize_preserve_paragraphs already handles this)
    return txt.strip()


def _sanitize_plain_text(text: str) -> str:
    text = (text or "")[:DEFAULT_MAX_TEXT_CHARS]
    text = _strip_control_chars(text)
    text = _html.unescape(text)
    text = _normalize_preserve_paragraphs(text)
    text = _drop_boilerplate_lines(text)
    # For plain text, keep paragraphs; do not fully flatten
    return text.strip()


def _truncate_to_bytes(text: str, max_bytes: int) -> Dict[str, Any]:
    """
    Byte-bound output while keeping valid UTF-8.
    """
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

    # If sanitizer got too aggressive, fall back to a safer minimal collapse
    if not cleaned.strip():
        cleaned = _collapse_whitespace(_strip_control_chars(_html.unescape(content)))

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
        "note": "net.sanitize (Phase 7.2.2, read-only, bounded; main/article/body prefer; boilerplate reduced; entities decoded)",
    }


NET_SANITIZE_T = ToolSpec(
    name="net.sanitize",
    description="Sanitize fetched content into bounded clean text (read-only, safe, boilerplate-reduced).",
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
