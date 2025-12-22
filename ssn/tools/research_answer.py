# ssn/tools/research_answer.py

"""
Research Answer Tool — Phase 7.3 (Production Front Door + Deterministic Quality)

READ-ONLY
OWNER-only
SAFE
OFFLINE-COMPATIBLE

Purpose:
- Single production entry point for "research" that composes:
  net.search -> net.fetch -> net.sanitize -> net.cite
- Returns a bounded, deterministic answer + citations + sources.

Phase 7.3 hardening additions:
- Deterministic sentence-ranking summarizer to avoid nav boilerplate.
- Assemble answer from best-ranked sentences across sources (diversity bias).
- Optional pass-through of net.search hardening args:
  preferred_provider, min_results, debug.

Notes:
- This tool does NOT write to memory.
- This tool does NOT perform raw HTTP itself; it calls ToolRegistry tools.
- In strict mode, degraded/mock search results are rejected unless allow_degraded=True.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Tuple, Optional

from ssn.tools.contracts import ToolSpec


# ---------------------------------------------------------
# Bounds
# ---------------------------------------------------------
DEFAULT_TOP_K = 3
HARD_TOP_K = 5

DEFAULT_FETCH_MAX_BYTES = 50_000
HARD_FETCH_MAX_BYTES = 200_000

DEFAULT_MAX_QUOTES = 3
HARD_MAX_QUOTES = 10

DEFAULT_QUOTE_LEN = 240
HARD_QUOTE_LEN = 600

DEFAULT_MAX_ANSWER_CHARS = 800
HARD_MAX_ANSWER_CHARS = 2000

DEFAULT_TIMEOUT_S = 10
HARD_TIMEOUT_S = 20

# Sentence ranker bounds
_MIN_SENT_LEN = 40
_MAX_SENT_LEN = 360
_MAX_SENTS_PER_SOURCE = 40  # keep bounded even if sanitizer output is long
_MAX_CANDIDATE_SENTS = 160  # global cap


# ---------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------

_RE_WS = re.compile(r"\s+")
_RE_SPLIT = re.compile(r"(?<=[\.\?\!])\s+|\n+")

# Common boilerplate / nav/legal phrases (lowercased substring match)
_BOILERPLATE_NEEDLES = (
    "cookie",
    "cookies",
    "privacy policy",
    "terms of service",
    "terms and conditions",
    "accept all",
    "manage preferences",
    "sign in",
    "sign up",
    "subscribe",
    "newsletter",
    "advertis",
    "javascript required",
    "enable javascript",
    "all rights reserved",
    "©",
    "sitemap",
    "contact us",
    "skip to content",
    "menu",
    "breadcrumb",
    "consent",
)


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


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(value, hi))


def _truncate(text: str, max_chars: int) -> Tuple[str, bool]:
    if not isinstance(text, str):
        return "", False
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def _forced_offline() -> bool:
    return os.getenv("SSN_OFFLINE") == "1"


def _env_flag(name: str) -> bool:
    return os.getenv(name) == "1"


def _effective_mode(args: Dict[str, Any]) -> Tuple[bool, bool]:
    """
    Returns (live_effective, strict_effective)

    Rules:
    - SSN_OFFLINE=1 forces live=False and strict=False
    - If args include live/strict, they override env (unless forced offline)
    - Else env controls apply
    """
    if _forced_offline():
        return (False, False)

    if "live" in args:
        live = _safe_bool(args.get("live"), default=False)
    else:
        live = _env_flag("SSN_LIVE_SEARCH")

    if "strict" in args:
        strict = _safe_bool(args.get("strict"), default=False)
    else:
        strict = _env_flag("SSN_LIVE_STRICT")

    return (bool(live), bool(strict))


def _get_tool_runner(deps: Dict[str, Any]) -> Any:
    tr = deps.get("tools") or deps.get("tool_registry")
    if tr is None:
        raise RuntimeError("research.answer requires deps['tools'] (ToolRegistry).")
    return tr


def _run_tool(
    registry: Any,
    *,
    name: str,
    role: str,
    deps: Dict[str, Any],
    args: Dict[str, Any],
) -> Dict[str, Any]:
    tr = registry.run(name=name, role=role, deps=deps, args=args)

    if not getattr(tr, "ok", False):
        err = getattr(tr, "error", None) or {"code": "TOOL_FAILED", "message": f"{name} failed"}
        raise RuntimeError(f"{name} failed: {err}")

    data = getattr(tr, "data", None)
    if not isinstance(data, dict):
        raise RuntimeError(f"{name} returned non-dict data")
    return data


def _tokenize(s: str) -> List[str]:
    s = (s or "").lower()
    toks = re.split(r"[^a-z0-9]+", s)
    return [t for t in toks if len(t) >= 3]


def _normalize_text(s: str) -> str:
    s = (s or "").replace("\r", " ").replace("\n", " ")
    s = _RE_WS.sub(" ", s).strip()
    return s


def _split_sentences(clean_text: str) -> List[str]:
    if not isinstance(clean_text, str) or not clean_text.strip():
        return []
    text = _normalize_text(clean_text)
    parts = _RE_SPLIT.split(text)
    out: List[str] = []
    for p in parts:
        p = _normalize_text(p)
        if p:
            out.append(p)
    return out


def _is_boilerplate_sentence(sent: str) -> bool:
    if not isinstance(sent, str):
        return True
    s = sent.strip()
    if len(s) < _MIN_SENT_LEN or len(s) > _MAX_SENT_LEN:
        return True
    low = s.lower()
    # highly numeric / junk lines
    if sum(ch.isdigit() for ch in low) > max(10, len(low) // 3):
        return True
    return any(n in low for n in _BOILERPLATE_NEEDLES)


def _rank_sentences(
    query: str,
    docs: List[Dict[str, Any]],
    *,
    max_answer_chars: int,
) -> Dict[str, Any]:
    """
    Deterministic extractive summarizer:
    - Collect candidate sentences from each doc (bounded).
    - Score by query overlap + early-position bonus.
    - Encourage multi-source diversity via greedy selection penalty.
    """
    qtok = _tokenize(query)
    if not qtok:
        qtok = _tokenize(query.lower())

    candidates: List[Dict[str, Any]] = []
    for doc in docs:
        url = str(doc.get("url", "") or "")
        clean = doc.get("clean_text")
        if not isinstance(clean, str) or not clean.strip():
            continue

        sents = _split_sentences(clean)
        # per-source cap
        sents = sents[:_MAX_SENTS_PER_SOURCE]

        for idx, sent in enumerate(sents):
            if _is_boilerplate_sentence(sent):
                continue
            low = sent.lower()
            overlap = sum(1 for t in qtok if t in low)
            # early position bonus (deterministic)
            pos_bonus = 1.0 if idx < 3 else (0.5 if idx < 8 else 0.0)

            # Slight preference for informative-length sentences
            slen = len(sent)
            len_bonus = 0.5 if 90 <= slen <= 240 else 0.0

            score = (0.20 * overlap) + (0.10 * pos_bonus) + (0.05 * len_bonus)

            candidates.append(
                {
                    "url": url,
                    "sent": sent,
                    "sent_idx": idx,
                    "base_score": float(score),
                }
            )

            if len(candidates) >= _MAX_CANDIDATE_SENTS:
                break
        if len(candidates) >= _MAX_CANDIDATE_SENTS:
            break

    if not candidates:
        return {"answer": "", "truncated": False, "selected": []}

    # Deterministic ordering by base score then url then sentence index then sentence text
    candidates.sort(key=lambda c: (-c["base_score"], c["url"], c["sent_idx"], c["sent"]))

    selected: List[Dict[str, Any]] = []
    used_urls: Dict[str, int] = {}
    used_sent_hashes: set[str] = set()
    out_text_parts: List[str] = []
    total_len = 0
    truncated = False

    for c in candidates:
        url = c["url"]
        sent = c["sent"]

        # near-duplicate suppression (deterministic)
        norm = re.sub(r"\W+", "", sent.lower())
        h = norm[:220]
        if h in used_sent_hashes:
            continue

        # diversity penalty (soft): skip if we've already taken too many from same source
        cnt = used_urls.get(url, 0)
        if cnt >= 2:
            continue

        add_len = len(sent) + (1 if out_text_parts else 0)
        if total_len + add_len > max_answer_chars:
            truncated = True
            break

        used_sent_hashes.add(h)
        used_urls[url] = cnt + 1
        selected.append(c)
        out_text_parts.append(sent)
        total_len += add_len

        if total_len >= max_answer_chars:
            truncated = True
            break

        # stop if we already have a good compact answer
        if len(out_text_parts) >= 8:
            break

    answer = " ".join(out_text_parts).strip()
    return {"answer": answer, "truncated": truncated, "selected": selected}


def _dedupe_citations(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Best-effort dedupe using (url, start, end, quote prefix).
    Works with your net.cite format.
    """
    out: List[Dict[str, Any]] = []
    seen = set()
    for c in citations:
        if not isinstance(c, dict):
            continue
        url = str(c.get("url", "") or "")
        start = c.get("start")
        end = c.get("end")
        quote = str(c.get("quote", "") or "")
        key = (url, int(start) if isinstance(start, int) else start, int(end) if isinstance(end, int) else end, quote[:80])
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def _filter_citations_to_answer(
    answer: str,
    citations: List[Dict[str, Any]],
    *,
    max_total: int,
) -> List[Dict[str, Any]]:
    """
    Best-effort: prefer citations whose quote appears in the answer.
    If none match, fall back to the first citations (already bounded).
    """
    if not isinstance(answer, str) or not answer.strip():
        return []
    ans_low = answer.lower()

    hits: List[Dict[str, Any]] = []
    rest: List[Dict[str, Any]] = []
    for c in citations:
        quote = str(c.get("quote", "") or "")
        if quote and quote.lower() in ans_low:
            hits.append(c)
        else:
            rest.append(c)

    out = hits + rest
    return out[:max_total]


# ---------------------------------------------------------
# Handler
# ---------------------------------------------------------

def research_answer_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {"error": {"code": "INVALID_QUERY", "message": "Missing or invalid 'query'"}}
    query = query.strip()

    top_k = _clamp(_safe_int(args.get("top_k"), DEFAULT_TOP_K), 1, HARD_TOP_K)
    fetch_max_bytes = _clamp(_safe_int(args.get("max_bytes"), DEFAULT_FETCH_MAX_BYTES), 1000, HARD_FETCH_MAX_BYTES)

    max_quotes = _clamp(_safe_int(args.get("max_quotes"), DEFAULT_MAX_QUOTES), 1, HARD_MAX_QUOTES)
    quote_len = _clamp(_safe_int(args.get("quote_len"), DEFAULT_QUOTE_LEN), 80, HARD_QUOTE_LEN)

    max_answer_chars = _clamp(
        _safe_int(args.get("max_answer_chars"), DEFAULT_MAX_ANSWER_CHARS),
        200,
        HARD_MAX_ANSWER_CHARS,
    )

    timeout_s = float(_clamp(_safe_int(args.get("timeout_s"), DEFAULT_TIMEOUT_S), 2, HARD_TIMEOUT_S))
    allow_degraded = _safe_bool(args.get("allow_degraded"), default=False)

    # Optional pass-through to net.search (Phase 7.3 hardening)
    preferred_provider = args.get("preferred_provider")
    min_results = args.get("min_results")
    debug = _safe_bool(args.get("debug"), default=False)

    live_effective, strict_effective = _effective_mode(args)

    role = deps.get("role")
    if not isinstance(role, str):
        role = "OWNER"

    registry = _get_tool_runner(deps)
    started_at = time.time()

    # 1) net.search (only pass keys it expects)
    search_args: Dict[str, Any] = {
        "query": query,
        "top_k": top_k,
        "timeout_s": int(timeout_s),
    }

    if "live" in args:
        search_args["live"] = _safe_bool(args.get("live"), default=False)

    if "strict" in args:
        search_args["strict"] = _safe_bool(args.get("strict"), default=False)

    if isinstance(preferred_provider, str) and preferred_provider.strip():
        search_args["preferred_provider"] = preferred_provider.strip()

    if min_results is not None:
        try:
            search_args["min_results"] = int(min_results)
        except Exception:
            pass

    if debug:
        search_args["debug"] = True

    try:
        search_data = _run_tool(registry, name="net.search", role=role, deps=deps, args=search_args)
    except Exception as e:
        return {
            "error": {"code": "SEARCH_FAILED", "message": str(e)},
            "query": query,
            "answered_at": time.time(),
            "elapsed_ms": int((time.time() - started_at) * 1000),
        }

    results = search_data.get("results", [])
    provider = search_data.get("provider")
    providers_tried = search_data.get("providers_tried")
    result_count = search_data.get("result_count")

    # pass through provider_debug if debug=True and it exists
    provider_debug = search_data.get("provider_debug") if debug else None

    degraded_search = bool(search_data.get("degraded", False)) or (provider == "mock-search") or _forced_offline()

    if strict_effective and degraded_search and not allow_degraded:
        err = {
            "code": "DEGRADED_RESULTS_BLOCKED",
            "message": "Search results were degraded/mock; refusing to answer in strict mode. Set allow_degraded=True to override explicitly.",
        }
        out = {
            "error": err,
            "query": query,
            "search": {
                "provider": provider,
                "providers_tried": providers_tried,
                "result_count": result_count,
                "degraded": True,
                "live_effective": live_effective,
                "strict_effective": strict_effective,
            },
            "answered_at": time.time(),
            "elapsed_ms": int((time.time() - started_at) * 1000),
        }
        if debug and provider_debug is not None:
            out["search"]["provider_debug"] = provider_debug
        return out

    if not isinstance(results, list) or not results:
        out = {
            "query": query,
            "answer": "",
            "answer_truncated": False,
            "sources": [],
            "citations": [],
            "degraded": degraded_search,
            "search": {
                "provider": provider,
                "providers_tried": providers_tried,
                "result_count": result_count,
                "degraded": degraded_search,
                "live_effective": live_effective,
                "strict_effective": strict_effective,
            },
            "note": "No search results",
            "answered_at": time.time(),
            "elapsed_ms": int((time.time() - started_at) * 1000),
        }
        if debug and provider_debug is not None:
            out["search"]["provider_debug"] = provider_debug
        return out

    sources: List[Dict[str, Any]] = []
    all_citations: List[Dict[str, Any]] = []
    docs_for_ranker: List[Dict[str, Any]] = []

    # Try up to top_k sources; tolerate failures
    for r in results[:top_k]:
        if not isinstance(r, dict):
            continue

        url = r.get("url")
        if not isinstance(url, str) or not url.strip():
            continue
        url = url.strip()

        title = r.get("title") if isinstance(r.get("title"), str) else ""
        snippet = r.get("snippet") if isinstance(r.get("snippet"), str) else ""
        retrieved_at = r.get("retrieved_at")
        try:
            retrieved_at_f = float(retrieved_at) if retrieved_at is not None else None
        except Exception:
            retrieved_at_f = None

        # 2) net.fetch
        try:
            fetch_data = _run_tool(
                registry,
                name="net.fetch",
                role=role,
                deps=deps,
                args={"url": url, "max_bytes": fetch_max_bytes, "timeout_s": int(timeout_s)},
            )
        except Exception:
            continue

        content_type = fetch_data.get("content_type", "text/plain")
        content = fetch_data.get("content", "")

        # 3) net.sanitize
        try:
            sanitize_data = _run_tool(
                registry,
                name="net.sanitize",
                role=role,
                deps=deps,
                args={
                    "url": url,
                    "content_type": content_type,
                    "content": content,
                    "max_bytes": fetch_max_bytes,
                },
            )
        except Exception:
            continue

        clean_text = sanitize_data.get("clean_text", "")
        if not isinstance(clean_text, str) or not clean_text.strip():
            continue

        docs_for_ranker.append({"url": url, "title": title, "clean_text": clean_text})

        # 4) net.cite (bounded)
        try:
            cite_data = _run_tool(
                registry,
                name="net.cite",
                role=role,
                deps=deps,
                args={
                    "url": url,
                    "clean_text": clean_text,
                    "max_quotes": max_quotes,
                    "quote_len": quote_len,
                },
            )
            citations = cite_data.get("citations", [])
            if isinstance(citations, list):
                all_citations.extend([c for c in citations if isinstance(c, dict)])
        except Exception:
            pass

        sources.append(
            {
                "url": url,
                "title": title,
                "snippet": snippet,
                "retrieved_at": retrieved_at_f,
                "search_provider": provider,
            }
        )

    # Deterministic sentence-ranked answer
    ranker_out = _rank_sentences(query, docs_for_ranker, max_answer_chars=max_answer_chars)
    answer_text = ranker_out["answer"]
    answer_truncated = bool(ranker_out["truncated"])

    # Citations: dedupe, then prefer those whose quote appears in answer
    citations_deduped = _dedupe_citations(all_citations)
    citations_final = _filter_citations_to_answer(
        answer_text,
        citations_deduped,
        max_total=max_quotes * max(1, len(docs_for_ranker)),
    )

    out = {
        "query": query,
        "answer": answer_text,
        "answer_truncated": answer_truncated,
        "sources": sources,
        "citations": citations_final,
        "degraded": bool(degraded_search),
        "search": {
            "provider": provider,
            "providers_tried": providers_tried,
            "result_count": result_count,
            "degraded": bool(degraded_search),
            "live_effective": live_effective,
            "strict_effective": strict_effective,
        },
        "answered_at": time.time(),
        "elapsed_ms": int((time.time() - started_at) * 1000),
        "note": "research.answer (Phase 7.3, composed, deterministic sentence-ranked, read-only)",
    }

    if debug and provider_debug is not None:
        out["search"]["provider_debug"] = provider_debug

    return out


RESEARCH_ANSWER_T = ToolSpec(
    name="research.answer",
    description="Answer a query using composed net.* pipeline (read-only, OWNER-only).",
    required_role="OWNER",
    allowed_roles=("OWNER",),
    state_changing=False,
    # Conservative: this wrapper triggers external-effect tools (net.search/net.fetch)
    external_effect=True,
    public=False,
    max_calls_per_minute=60,
    input_schema={
        "query": {"type": "string", "required": True, "description": "Question or research query"},
        "top_k": {"type": "integer", "required": False, "description": "Number of sources (1–5)"},
        "max_bytes": {"type": "integer", "required": False, "description": "Max bytes per fetch/sanitize (bounded)"},
        "timeout_s": {"type": "integer", "required": False, "description": "Timeout seconds (2–20)"},
        "max_quotes": {"type": "integer", "required": False, "description": "Max citations per source (1–10)"},
        "quote_len": {"type": "integer", "required": False, "description": "Citation quote length (80–600 chars)"},
        "max_answer_chars": {"type": "integer", "required": False, "description": "Max answer characters (200–2000)"},
        "live": {"type": "boolean", "required": False, "description": "Override net.search live mode (otherwise env decides)"},
        "strict": {"type": "boolean", "required": False, "description": "Override net.search strict mode (otherwise env decides)"},
        "allow_degraded": {"type": "boolean", "required": False, "description": "Allow degraded/mock results even in strict mode"},
        # Phase 7.3 pass-through and diagnostics
        "preferred_provider": {"type": "string", "required": False, "description": "Optional preferred net.search provider"},
        "min_results": {"type": "integer", "required": False, "description": "Try providers until at least this many raw results are collected"},
        "debug": {"type": "boolean", "required": False, "description": "Include provider_debug from net.search (diagnostics)"},
    },
    handler=research_answer_handler,
)
