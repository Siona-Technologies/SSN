# ssn/tools/net_cite.py
"""
Citation tools — Phase 7.2.3 (Production hardened)

READ-ONLY
SAFE
OFFLINE-COMPATIBLE

Purpose:
- Convert sanitized text into bounded citation objects (evidence snippets)
- Emits provenance (url/title/retrieved_at/content_type) + stable hashes for audit
- Deterministic, boilerplate-aware extraction (better than naive chunking)
"""

from __future__ import annotations

import hashlib
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from ssn.tools.contracts import ToolSpec


# ---------------------------------------------------------
# Bounds
# ---------------------------------------------------------

DEFAULT_MAX_QUOTES = 5
HARD_MAX_QUOTES = 10

DEFAULT_QUOTE_LEN = 240
HARD_QUOTE_LEN = 600

DEFAULT_MIN_SEGMENT_LEN = 80
HARD_MIN_SEGMENT_LEN = 40

DEFAULT_MAX_TEXT_CHARS = 120_000  # hard bound inside cite (sanitize already bounds)

# Candidate generation caps
_MAX_PARAS = 80
_MAX_SENTENCES_PER_PARA = 40
_MAX_CANDIDATES = 300

# Boilerplate gating
_WEAK_BOILERPLATE_MAX_LEN = 180  # only treat "weak" needles as boilerplate when segment is short-ish


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

_WS = re.compile(r"\s+")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

# Strong boilerplate needles (almost always non-evidence)
_STRONG_BOILERPLATE_NEEDLES = (
    # nav/auth/cookie
    "jump to content",
    "skip to content",
    "create account",
    "log in",
    "sign in",
    "sign up",
    "privacy policy",
    "cookie",
    "cookies",
    "consent",
    "accept all",
    "reject all",
    "all rights reserved",
    "subscribe",
    "newsletter",
    "navigation",
    "donate",
    "advert",
    "advertisement",

    # wikipedia / maintenance templates
    "please help clean up",
    "this article needs additional citations",
    "this article may contain",
    "this article includes a list of",
    "please help improve this article",
    "this section needs expansion",
    "citation needed",
    "the neutrality of this article is disputed",
    "this article is in list format",
)

# Weak boilerplate needles (often appear as UI fragments; don’t hard-block long evidence)
_WEAK_BOILERPLATE_NEEDLES = (
    "menu",
    "search",
    "languages",
    "toggle",
)

_BAD_PUNCT = set("{}[]<>|;")


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _truncate_on_word_boundary(text: str, max_len: int) -> str:
    if not isinstance(text, str):
        return ""
    t = text.strip()
    if len(t) <= max_len:
        return t
    cut = t[:max_len].rstrip()
    if len(cut) > 40:
        last_space = cut.rfind(" ")
        if last_space >= 60:
            cut = cut[:last_space].rstrip()
    return cut


def _normalize_ws_keep_newlines(text: str) -> str:
    """
    Normalize whitespace but keep paragraph breaks.
    """
    if not isinstance(text, str):
        return ""
    t = text.replace("\r", "\n")
    t = re.sub(r"\n{3,}", "\n\n", t)
    lines = []
    for line in t.split("\n"):
        line = _WS.sub(" ", line).strip()
        lines.append(line)
    rebuilt = "\n".join(lines)
    rebuilt = re.sub(r"\n{3,}", "\n\n", rebuilt).strip()
    return rebuilt


def _normalize_ws_flat(text: str) -> str:
    """
    Fully flatten whitespace to single spaces (for offsets / hashing / searching).
    """
    if not isinstance(text, str):
        return ""
    return _WS.sub(" ", text).strip()


def _sha256_hex(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8", errors="replace")).hexdigest()


def _looks_like_boilerplate(seg: str) -> bool:
    if not seg:
        return True
    s0 = seg.strip()
    if not s0:
        return True

    s = s0.lower()

    # too few alphabetic chars => likely junk/nav
    alpha = sum(1 for c in s if c.isalpha())
    if alpha < 30:
        return True

    # strong needles always block
    if any(n in s for n in _STRONG_BOILERPLATE_NEEDLES):
        return True

    # weak needles only block if segment is short-ish (typical UI fragments)
    if len(s0) <= _WEAK_BOILERPLATE_MAX_LEN and any(n in s for n in _WEAK_BOILERPLATE_NEEDLES):
        return True

    # lots of weird punctuation often means nav/code remnants
    punct = sum(1 for c in s if c in _BAD_PUNCT)
    if punct >= 6:
        return True

    return False


def _tokenize_keywords(text: str, *, min_len: int = 4, cap: int = 24) -> List[str]:
    """
    Deterministic tokenization, bounded.
    """
    base = (text or "").lower()
    toks = [t for t in re.split(r"[^a-z0-9]+", base) if len(t) >= min_len]
    out: List[str] = []
    seen = set()
    for t in toks:
        if t not in seen:
            seen.add(t)
            out.append(t)
        if len(out) >= cap:
            break
    return out


def _keyword_tokens(
    *,
    title: Optional[str],
    snippet: Optional[str],
    query: Optional[str],
) -> List[str]:
    """
    Build keyword set for scoring relevance.
    Uses (query + title + snippet) if provided.
    Deterministic and bounded.
    """
    merged = f"{query or ''} {title or ''} {snippet or ''}"
    return _tokenize_keywords(merged, min_len=4, cap=24)


def _score_segment(seg: str, keywords: List[str]) -> Tuple[float, int]:
    """
    Deterministic scoring:
    - prefer ~90..320 char segments
    - reward keyword hits
    - strong penalty for boilerplate
    Returns (score, kw_hits)
    """
    if not seg:
        return (-999.0, 0)

    s = seg.strip()
    n = len(s)

    score = 0.0
    if 90 <= n <= 320:
        score += 2.0
    elif 60 <= n < 90:
        score += 1.0
    elif n > 520:
        score -= 1.0

    sl = s.lower()
    hits = 0
    for k in keywords:
        if k and k in sl:
            hits += 1
    score += min(3.0, hits * 0.6)

    # tiny “sentence-likeness” bonus (still deterministic)
    if s and s[0].isupper():
        score += 0.10
    if s.endswith((".", "!", "?")):
        score += 0.10

    if _looks_like_boilerplate(s):
        score -= 6.0

    return (score, hits)


def _paragraphs(clean_text: str) -> List[str]:
    t = _normalize_ws_keep_newlines(clean_text)
    if not t:
        return []
    paras = [p.strip() for p in re.split(r"\n\s*\n+", t) if p.strip()]
    return paras[:_MAX_PARAS]


def _sentence_windows(para: str) -> List[str]:
    """
    Build bounded 1–3 sentence windows from a paragraph to land in citation-friendly lengths.
    Deterministic (no randomness).
    """
    flat = _normalize_ws_flat(para)
    if not flat:
        return []

    sents = [s.strip() for s in _SENT_SPLIT.split(flat) if s.strip()]
    sents = sents[:_MAX_SENTENCES_PER_PARA]
    if not sents:
        return []

    out: List[str] = []

    for i in range(len(sents)):
        out.append(sents[i])
        if i + 1 < len(sents):
            out.append(f"{sents[i]} {sents[i+1]}")
        if i + 2 < len(sents):
            out.append(f"{sents[i]} {sents[i+1]} {sents[i+2]}")
        if len(out) >= 120:
            break

    return out


def _split_candidates(clean_text: str) -> List[str]:
    """
    Prefer paragraph-level chunks.
    If paragraph is long, generate sentence windows for better citations.
    """
    paras = _paragraphs(clean_text)
    if not paras:
        flat = _normalize_ws_flat(clean_text)
        parts = _SENT_SPLIT.split(flat)
        return [p.strip() for p in parts if p.strip()][:200]

    candidates: List[str] = []
    for p in paras:
        pflat = _normalize_ws_flat(p)
        if not pflat:
            continue

        if 90 <= len(pflat) <= 420:
            candidates.append(pflat)
        else:
            candidates.extend(_sentence_windows(pflat))

        if len(candidates) >= _MAX_CANDIDATES:
            break

    # de-dupe while preserving order
    out: List[str] = []
    seen = set()
    for c in candidates:
        k = c.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(c)
        if len(out) >= _MAX_CANDIDATES:
            break

    return out


def _pick_best_quotes(
    clean_text: str,
    *,
    title: Optional[str],
    snippet: Optional[str],
    query: Optional[str],
    max_quotes: int,
    quote_len: int,
    min_segment_len: int,
) -> List[Tuple[str, float, int]]:
    """
    Pick up to max_quotes quotes, bounded to quote_len.
    Returns list of (quote, score, kw_hits).
    """
    candidates = _split_candidates(clean_text)
    if not candidates:
        return []

    keywords = _keyword_tokens(title=title, snippet=snippet, query=query)

    scored: List[Tuple[float, int, str]] = []
    for seg in candidates:
        seg2 = _normalize_ws_flat(seg)
        if len(seg2) < min_segment_len:
            continue
        sc, hits = _score_segment(seg2, keywords)
        scored.append((sc, hits, seg2))

    # deterministic ordering: score desc, kw_hits desc, then text asc
    scored.sort(key=lambda x: (-x[0], -x[1], x[2]))

    out: List[Tuple[str, float, int]] = []
    seen = set()
    for sc, hits, seg in scored:
        if len(out) >= max_quotes:
            break
        if sc < -1.5:
            continue

        q = _truncate_on_word_boundary(seg, quote_len)
        k = q.lower()
        if k in seen:
            continue
        seen.add(k)
        if not q:
            continue
        if _looks_like_boilerplate(q):
            continue

        out.append((q, float(sc), int(hits)))

    # fallback if everything filtered
    if not out:
        flat = _normalize_ws_flat(clean_text)
        if flat:
            q = _truncate_on_word_boundary(flat, quote_len)
            out = [(q, 0.0, 0)]

    return out[:max_quotes]


def _locate_offsets(haystack: str, quote: str, *, start_from: int) -> Tuple[Optional[int], Optional[int], int]:
    """
    Best-effort offsets: find quote inside normalized flat text.
    Returns (start, end, next_start_from).
    """
    if not haystack or not quote:
        return None, None, start_from

    i = haystack.find(quote, max(0, start_from))
    if i < 0:
        i = haystack.find(quote)  # retry from start
    if i < 0:
        return None, None, start_from

    j = i + len(quote)
    return i, j, j


# ---------------------------------------------------------
# Handler
# ---------------------------------------------------------

def net_cite_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    url = args.get("url")
    if not isinstance(url, str) or not url.strip():
        return {"error": {"code": "INVALID_URL", "message": "Missing or invalid 'url' string"}}
    url = url.strip()

    clean_text = args.get("clean_text")
    if not isinstance(clean_text, str) or not clean_text.strip():
        return {"error": {"code": "INVALID_CLEAN_TEXT", "message": "Missing or invalid 'clean_text' string"}}

    title = args.get("title")
    title = title.strip() if isinstance(title, str) and title.strip() else None

    snippet = args.get("snippet")
    snippet = snippet.strip() if isinstance(snippet, str) and snippet.strip() else None

    retrieved_at = args.get("retrieved_at")
    if not isinstance(retrieved_at, (int, float)):
        retrieved_at = None

    content_type = args.get("content_type")
    content_type = content_type.strip() if isinstance(content_type, str) and content_type.strip() else None

    query = args.get("query")
    query = query.strip() if isinstance(query, str) and query.strip() else None

    max_quotes = _safe_int(args.get("max_quotes"), DEFAULT_MAX_QUOTES)
    max_quotes = max(1, min(max_quotes, HARD_MAX_QUOTES))

    quote_len = _safe_int(args.get("quote_len"), DEFAULT_QUOTE_LEN)
    quote_len = max(80, min(quote_len, HARD_QUOTE_LEN))

    min_segment_len = _safe_int(args.get("min_segment_len"), DEFAULT_MIN_SEGMENT_LEN)
    min_segment_len = max(HARD_MIN_SEGMENT_LEN, min(min_segment_len, 300))

    clean_text = clean_text[:DEFAULT_MAX_TEXT_CHARS]

    captured_at = time.time()

    flat_text = _normalize_ws_flat(clean_text)
    text_sha256 = _sha256_hex(flat_text)

    picked = _pick_best_quotes(
        clean_text,
        title=title,
        snippet=snippet,
        query=query,
        max_quotes=max_quotes,
        quote_len=quote_len,
        min_segment_len=min_segment_len,
    )

    citations: List[Dict[str, Any]] = []
    start_from = 0
    for idx, (q, score, kw_hits) in enumerate(picked, start=1):
        s, e, start_from = _locate_offsets(flat_text, q, start_from=start_from)
        citations.append(
            {
                "url": url,
                "idx": idx,
                "start": s,
                "end": e,
                "quote": q,
                "quote_sha256": _sha256_hex(q),
                "captured_at": captured_at,
                # additive diagnostics (safe to ignore downstream)
                "score": float(score),
                "kw_hits": int(kw_hits),
                # provenance echo (optional)
                "title": title,
                "snippet": snippet,
                "retrieved_at": retrieved_at,
                "content_type": content_type,
            }
        )

    payload: Dict[str, Any] = {
        "url": url,
        "citation_count": len(citations),
        "citations": citations,
        "cited_at": captured_at,
        "text_sha256": text_sha256,
        "note": "net.cite (Phase 7.2.3, read-only, bounded; query/title/snippet scored; provenance+hashes)",
    }

    if title:
        payload["title"] = title
    if snippet:
        payload["snippet"] = snippet
    if query:
        payload["query"] = query
    if retrieved_at is not None:
        payload["retrieved_at"] = retrieved_at
    if content_type:
        payload["content_type"] = content_type

    return payload


# ---------------------------------------------------------
# ToolSpec
# ---------------------------------------------------------

NET_CITE_T = ToolSpec(
    name="net.cite",
    description="Create bounded citation snippets from sanitized text (read-only, boilerplate-aware, provenance+hashes).",
    required_role="OWNER",
    allowed_roles=("OWNER",),
    state_changing=False,
    external_effect=False,
    public=False,
    max_calls_per_minute=120,
    input_schema={
        "url": {"type": "string", "required": True, "description": "Source URL for citations"},
        "clean_text": {"type": "string", "required": True, "description": "Sanitized clean text to cite from"},
        "max_quotes": {"type": "integer", "required": False, "description": "Max citations to produce (1–10)"},
        "quote_len": {"type": "integer", "required": False, "description": "Max length of each quote (80–600 chars)"},
        "min_segment_len": {"type": "integer", "required": False, "description": "Minimum segment length before scoring/filtering"},
        "query": {"type": "string", "required": False, "description": "Original user query (optional; improves relevance scoring)"},
        "title": {"type": "string", "required": False, "description": "Source page title (optional)"},
        "snippet": {"type": "string", "required": False, "description": "Search snippet (optional)"},
        "retrieved_at": {"type": "number", "required": False, "description": "When content was retrieved (epoch seconds)"},
        "content_type": {"type": "string", "required": False, "description": "Content type (optional)"},
    },
    handler=net_cite_handler,
)
