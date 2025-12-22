# ssn/tools/net_sanitize.py
"""
Network Sanitizer Tool — Phase 7.2.2 (Production hardened)

READ-ONLY
SAFE
OFFLINE-COMPATIBLE

Goals:
- Truncation-tolerant HTML -> text extraction (stdlib-only, HTMLParser)
- Entity unescape (HTMLParser convert_charrefs=True + html.unescape)
- Prefer extracting "main-like" content:
  - Wikipedia/MediaWiki: prefer .mw-parser-output, else #mw-content-text
  - Else: prefer <main>, <article>, <body>
- Boilerplate heuristics (cookie/nav/footer/auth/share)
- Drop leaked Wikipedia language selector blocks
- Drop MediaWiki client state/config blobs (RLSTATE/RLCONF etc.)
- Bounded output (max_bytes hard-capped)

Tool name: net.sanitize
Export: NET_SANITIZE_T
"""

from __future__ import annotations

import html as _html
import re
import time
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

from ssn.tools.contracts import ToolSpec

DEFAULT_MAX_BYTES = 80_000
HARD_MAX_BYTES = 200_000

DEFAULT_MAX_TEXT_CHARS = 200_000  # internal safety; output is bounded by max_bytes

_CTRL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_WS_RE = re.compile(r"[ \t]+")
_NL_RE = re.compile(r"\n{3,}")

_TAG_LIKE_RE = re.compile(r"(?is)<\s*([a-z]|/|!doctype)")
_TAG_RE = re.compile(r"(?is)<[^>]+>")  # last-resort only

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
    # wikipedia maintenance leakage
    "please help clean up",
    "this article needs additional citations",
    "citation needed",
    "this article is in list format",
)

# Wikipedia language selector leakage patterns (text-level)
_WIKI_LANG_HEADER_RE = re.compile(r"(?i)^\s*\d{1,4}\s+languages?\s*$")
_WIKI_LANG_LINE_RE = re.compile(r"^[^\d][^:]{1,40}$")

# High-signal “junk” patterns (post-extraction)
_JS_LIKE_RE = re.compile(
    r"(?i)\b(function\s*\(|var\s+[a-z_]{2,}\s*=|document\.|window\.|client-js|vector-feature|mw\.config)\b"
)

# MediaWiki client state/config blobs and loader noise
# Example: RLSTATE={...}, RLCONF={...}
_WIKI_STATE_RE = re.compile(r"(?i)^\s*(RLSTATE|RLCONF)\s*=\s*\{")
# Example: mw.config.set(...), mw.loader...
_WIKI_MWCFG_RE = re.compile(r"(?i)\bmw\.(config|loader)\b")
# Example: {"ext.globalCssJs.user.styles":"ready", ...}
_WIKI_JSON_READY_RE = re.compile(r'(?i)"(site\.styles|user\.styles|ext\.)[^"]*"\s*:\s*"(ready|loading)"')

_BLOCK_TAGS = {
    "p", "div", "li", "ul", "ol",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "br", "hr", "tr", "td", "th",
    "section", "article", "main",
    "header", "footer", "nav", "aside",
    "table", "blockquote",
}

_SKIP_TAGS = {"script", "style", "noscript", "svg"}


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _strip_control_chars(text: str) -> str:
    return _CTRL_CHARS_RE.sub("", text or "")


def _normalize_preserve_paragraphs(text: str) -> str:
    """
    Keep paragraph breaks so downstream cite can pick coherent segments.
    """
    if not isinstance(text, str):
        return ""

    t = text.replace("\r", "\n")
    lines: List[str] = []
    for line in t.split("\n"):
        line = _WS_RE.sub(" ", (line or "")).strip()
        lines.append(line)

    t = "\n".join(lines)
    t = _NL_RE.sub("\n\n", t).strip()
    return t


def _is_wikipedia_url(url: Optional[str]) -> bool:
    if not isinstance(url, str) or not url.strip():
        return False
    u = url.strip().lower()
    return ("wikipedia.org/" in u) or ("wikimedia.org/" in u)


def _drop_wikipedia_language_block(text: str) -> str:
    """
    Remove leaked Wikipedia language selector blocks (conservative).
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    lines = text.split("\n")
    if not lines:
        return text

    scan_limit = min(len(lines), 400)

    start_idx = None
    for i in range(scan_limit):
        li = (lines[i] or "").strip()
        if _WIKI_LANG_HEADER_RE.match(li):
            start_idx = i
            break
        if li.lower() in ("languages", "language"):
            start_idx = i
            break

    if start_idx is None:
        return text

    removed = 0
    end_idx = start_idx

    for j in range(start_idx, scan_limit):
        line = (lines[j] or "").strip()
        if not line:
            if removed >= 6:
                end_idx = j
                break
            continue

        low = line.lower()

        if j == start_idx:
            removed += 1
            end_idx = j
            continue

        if len(line) > 60 and any(ch in line for ch in (".", ":", ";", "—", "–")):
            end_idx = j - 1
            break
        if len(line) > 80:
            end_idx = j - 1
            break
        if low.startswith("contents") or low.startswith("from wikipedia") or low.startswith("edit"):
            end_idx = j - 1
            break

        if _WIKI_LANG_LINE_RE.match(line):
            removed += 1
            end_idx = j
            if removed >= 160:
                break
            continue

        if removed >= 6:
            end_idx = j - 1
            break

    if removed < 6:
        return text

    kept = lines[:start_idx] + lines[end_idx + 1 :]
    return "\n".join(kept).strip()


def _drop_boilerplate_lines(text: str) -> str:
    """
    Remove lines that look like nav/cookie/auth boilerplate.
    Conservative: only drops short-ish lines with boilerplate needles.
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    out_lines: List[str] = []
    for raw in text.split("\n"):
        line = (raw or "").strip()
        if not line:
            continue

        low = line.lower()

        if len(line) <= 180 and any(n in low for n in _BOILERPLATE_NEEDLES):
            continue

        if len(line) <= 60 and low in ("home", "about", "contact", "privacy", "terms", "login", "sign in", "menu"):
            continue

        out_lines.append(line)

    t = "\n".join(out_lines)
    t = _NL_RE.sub("\n\n", t).strip()
    return t


def _looks_like_junk_line(line: str) -> bool:
    """
    Deterministically drop “JS/classname/config” garbage that can leak from modern HTML pages.
    Includes MediaWiki RLSTATE/RLCONF and mw.config/mw.loader noise.
    """
    if not isinstance(line, str):
        return True
    s = line.strip()
    if not s:
        return True

    # MediaWiki state/config blobs
    if _WIKI_STATE_RE.search(s):
        return True
    if _WIKI_MWCFG_RE.search(s):
        return True
    if _WIKI_JSON_READY_RE.search(s) and len(s) > 40:
        return True

    # direct JS-like signals
    if _JS_LIKE_RE.search(s):
        return True

    # Very low alphabetic ratio (typical of class lists / minified fragments)
    letters = sum(ch.isalpha() for ch in s)
    if len(s) >= 80 and (letters / max(1, len(s)) < 0.22):
        return True

    # Extremely long single tokens (minified)
    tokens = re.split(r"\s+", s)
    if any(len(t) > 60 for t in tokens) and (letters / max(1, len(s)) < 0.35):
        return True

    return False


def _drop_junk_lines(text: str, *, max_scan_lines: int = 1200) -> str:
    """
    Post-extraction filter applied before boilerplate removal.
    Only drops lines that are strongly code-ish / classname-ish.
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    lines = text.split("\n")
    out: List[str] = []

    scan = min(len(lines), max_scan_lines)
    for i in range(scan):
        line = lines[i]
        if _looks_like_junk_line(line):
            continue
        out.append(line)

    if scan < len(lines):
        out.extend(lines[scan:])

    t = "\n".join(out)
    t = _NL_RE.sub("\n\n", t).strip()
    return t


class _TextExtractor(HTMLParser):
    """
    Truncation-tolerant HTML -> text extractor.

    Capturing strategy (priority-based):
      3: MediaWiki .mw-parser-output
      2: MediaWiki #mw-content-text
      1: <main>/<article>/<body>
      0: nothing

    If a higher-priority container appears, we reset output and switch capture to it.
    """
    def __init__(self, *, treat_as_wiki: bool):
        super().__init__(convert_charrefs=True)
        self.treat_as_wiki = bool(treat_as_wiki)

        self._skip_depth = 0
        self._stack: List[str] = []

        self._capture_active = False
        self._capture_root_depth = 0
        self._capture_priority = 0

        self._out: List[str] = []
        self._last_was_nl = False

    def _attrs_dict(self, attrs) -> Dict[str, str]:
        d: Dict[str, str] = {}
        for k, v in (attrs or []):
            if not k:
                continue
            d[k.lower()] = v or ""
        return d

    def _newline(self):
        if not self._last_was_nl:
            self._out.append("\n")
            self._last_was_nl = True

    def _push_text(self, s: str):
        if not s:
            return
        self._out.append(s)
        self._last_was_nl = s.endswith("\n")

    def _start_capture(self, priority: int):
        if priority <= self._capture_priority:
            return
        self._capture_priority = priority
        self._capture_active = True
        self._capture_root_depth = len(self._stack)
        self._out = []
        self._last_was_nl = False

    def _is_capturing(self) -> bool:
        if not self._capture_active:
            return False
        return len(self._stack) >= self._capture_root_depth

    def handle_starttag(self, tag, attrs):
        tag = (tag or "").lower()
        self._stack.append(tag)

        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return

        if self._skip_depth > 0:
            return

        ad = self._attrs_dict(attrs)
        _id = (ad.get("id") or "").strip().lower()
        _cls = (ad.get("class") or "")

        if self.treat_as_wiki:
            if "mw-parser-output" in _cls:
                self._start_capture(3)
            elif _id == "mw-content-text":
                self._start_capture(2)
        else:
            if tag in ("main", "article", "body"):
                self._start_capture(1)

        if tag in _BLOCK_TAGS and self._is_capturing():
            self._newline()

    def handle_endtag(self, tag):
        tag = (tag or "").lower()

        if tag in _SKIP_TAGS:
            if self._skip_depth > 0:
                self._skip_depth -= 1
            if self._stack:
                self._stack.pop()
            return

        if self._skip_depth > 0:
            if self._stack:
                self._stack.pop()
            return

        if tag in _BLOCK_TAGS and self._is_capturing():
            self._newline()

        if self._stack:
            self._stack.pop()

        if self._capture_active and len(self._stack) < self._capture_root_depth:
            self._capture_active = False

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        if not self._is_capturing():
            return
        self._push_text(data)

    def get_text(self) -> str:
        return "".join(self._out)


def _sanitize_html_to_text(html: str, *, url: Optional[str] = None) -> str:
    raw = (html or "")[:DEFAULT_MAX_TEXT_CHARS]
    wiki = _is_wikipedia_url(url) or ("mw-content-text" in raw) or ("mw-parser-output" in raw)

    parser = _TextExtractor(treat_as_wiki=bool(wiki))
    try:
        parser.feed(raw)
        parser.close()
    except Exception:
        pass

    txt = parser.get_text()

    txt = _html.unescape(txt)
    txt = _strip_control_chars(txt)
    txt = _normalize_preserve_paragraphs(txt)

    # Drop junk/code-ish lines FIRST (fixes RLSTATE / mw.config / vector-feature / etc.)
    txt = _drop_junk_lines(txt)

    if wiki:
        txt = _drop_wikipedia_language_block(txt)

    txt = _drop_boilerplate_lines(txt)

    if _TAG_LIKE_RE.search(txt):
        txt = _TAG_RE.sub(" ", txt)
        txt = _normalize_preserve_paragraphs(txt)
        txt = _drop_junk_lines(txt)
        if wiki:
            txt = _drop_wikipedia_language_block(txt)
        txt = _drop_boilerplate_lines(txt)

    return txt.strip()


def _sanitize_plain_text(text: str) -> str:
    t = (text or "")[:DEFAULT_MAX_TEXT_CHARS]
    t = _strip_control_chars(t)
    t = _html.unescape(t)
    t = _normalize_preserve_paragraphs(t)
    t = _drop_boilerplate_lines(t)
    t = _drop_junk_lines(t)
    return t.strip()


def _truncate_to_bytes(text: str, max_bytes: int) -> Dict[str, Any]:
    b = (text or "").encode("utf-8", errors="replace")
    if len(b) <= max_bytes:
        return {"clean_text": text, "clean_bytes": len(b), "truncated": False}

    b2 = b[:max_bytes]
    t2 = b2.decode("utf-8", errors="ignore")
    b3 = t2.encode("utf-8", errors="replace")
    return {"clean_text": t2, "clean_bytes": len(b3), "truncated": True}


def net_sanitize_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
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
        cleaned = _sanitize_html_to_text(content, url=url)
    else:
        cleaned = _sanitize_plain_text(content)

    # If sanitizer got too aggressive, fall back to a safe minimal path (never raw HTML)
    if not cleaned.strip():
        cleaned = _sanitize_plain_text(content)
        if _TAG_LIKE_RE.search(cleaned):
            cleaned = _TAG_RE.sub(" ", cleaned)
            cleaned = _normalize_preserve_paragraphs(cleaned)
            cleaned = _drop_boilerplate_lines(cleaned)
            cleaned = _drop_junk_lines(cleaned)

    trunc = _truncate_to_bytes(cleaned, max_bytes)

    # Final “tag-like” safety pass after truncation
    if _TAG_LIKE_RE.search(trunc["clean_text"]):
        fixed = _TAG_RE.sub(" ", trunc["clean_text"])
        fixed = _normalize_preserve_paragraphs(fixed)
        fixed = _drop_boilerplate_lines(fixed)
        fixed = _drop_junk_lines(fixed)
        trunc = _truncate_to_bytes(fixed, max_bytes)

    return {
        "url": url,
        "content_type": "text/plain",
        "original_content_type": content_type,
        "original_bytes": original_bytes,
        "clean_bytes": trunc["clean_bytes"],
        "clean_text": trunc["clean_text"],
        "truncated": trunc["truncated"],
        "sanitized_at": time.time(),
        "note": "net.sanitize (Phase 7.2.2, parser-based, read-only, bounded; priority capture; MW junk/boilerplate reduced; never returns raw HTML)",
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
