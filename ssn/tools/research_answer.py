# ssn/tools/research_answer.py

"""
Research Answer Tool — Phase 7.3 (Production Front Door + Deterministic Quality)

READ-ONLY
SAFE
OFFLINE-COMPATIBLE

Purpose:
- Single production entry point for "research" that composes:
  net.search -> net.fetch -> net.sanitize -> net.cite
- Returns a bounded, deterministic answer + citations + sources.

Access model:
- OWNER: allowed (default).
- GUEST: allowed ONLY when explicitly enabled by context/policy:
    allow_tools=True AND allow_research=True
  This prevents direct tool calls from bypassing FrontDoor gating.

Offline model:
- When offline is requested (env SSN_OFFLINE=1 OR deps.offline=True OR args.offline=True),
  net.search/net.fetch are expected to return deterministic simulated outputs for pipeline testing.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from ssn.tools.contracts import ToolSpec


# ---------------------------------------------------------
# Bounds
# ---------------------------------------------------------
DEFAULT_TOP_K = 3
HARD_TOP_K = 5

DEFAULT_FETCH_MAX_BYTES = 150_000
HARD_FETCH_MAX_BYTES = 200_000

DEFAULT_MAX_QUOTES = 3
HARD_MAX_QUOTES = 10

DEFAULT_QUOTE_LEN = 240
HARD_QUOTE_LEN = 600

DEFAULT_MAX_ANSWER_CHARS = 800
HARD_MAX_ANSWER_CHARS = 2000

DEFAULT_TIMEOUT_S = 10
HARD_TIMEOUT_S = 20

_MIN_SENT_LEN = 40
_MAX_SENT_LEN = 360
_MAX_SENTS_PER_SOURCE = 45
_MAX_CANDIDATE_SENTS = 220


# ---------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------
_RE_WS = re.compile(r"\s+")
_RE_SPLIT = re.compile(r"(?<=[\.\?\!])\s+|\n+")

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
    "please help clean up",
    "this article needs additional citations",
    "citation needed",
    "this article is in list format",
    "languages",
)

_CODE_NEEDLES = (
    "function(",
    "var ",
    "let ",
    "const ",
    "=>",
    "return ",
    "document.",
    "window.",
    "navigator.",
    "mw.config",
    "mw.loader",
    "client-js",
    "vector-feature",
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


def _env_flag(name: str) -> bool:
    return os.getenv(name) == "1"


def _offline_requested(deps: Dict[str, Any], args: Dict[str, Any]) -> bool:
    """
    Respect offline from:
      - env SSN_OFFLINE=1
      - args.offline=True
      - deps.offline=True
    """
    if os.getenv("SSN_OFFLINE") == "1":
        return True
    if isinstance(args, dict) and bool(args.get("offline", False)):
        return True
    if isinstance(deps, dict) and bool(deps.get("offline", False)):
        return True
    return False


def _extract_ctx(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Best-effort locate FrontDoor/context dict if it is available.
    """
    for k in ("context", "ctx", "frontdoor_context", "request_context"):
        v = deps.get(k)
        if isinstance(v, dict):
            return v
    v2 = args.get("context")
    if isinstance(v2, dict):
        return v2
    return {}


def _guest_research_allowed(role: str, deps: Dict[str, Any], args: Dict[str, Any]) -> bool:
    """
    OWNER always allowed.
    GUEST allowed only with explicit enablement (context/policy).
    """
    role_u = (role or "").strip().upper()
    if role_u == "OWNER":
        return True
    if role_u != "GUEST":
        return False

    if _safe_bool(args.get("allow_guest_research"), default=False):
        return True

    ctx = _extract_ctx(deps, args)
    allow_research = _safe_bool(ctx.get("allow_research"), default=False)
    allow_tools = _safe_bool(ctx.get("allow_tools"), default=False)
    return bool(allow_research and allow_tools)


def _effective_mode(deps: Dict[str, Any], args: Dict[str, Any]) -> Tuple[bool, bool]:
    """
    Returns (live_effective, strict_effective)
    - Offline forces live=False and strict=False
    - args override env (unless offline)
    """
    if _offline_requested(deps, args):
        return (False, False)

    live = _safe_bool(args.get("live"), default=_env_flag("SSN_LIVE_SEARCH")) if "live" in args else _env_flag("SSN_LIVE_SEARCH")
    strict = _safe_bool(args.get("strict"), default=_env_flag("SSN_LIVE_STRICT")) if "strict" in args else _env_flag("SSN_LIVE_STRICT")

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


def _is_code_like_sentence(sent: str) -> bool:
    if not isinstance(sent, str):
        return True
    s = sent.strip()
    if not s:
        return True
    low = s.lower()
    if any(n in low for n in _CODE_NEEDLES):
        return True
    punct = sum(1 for ch in s if ch in "{}[]();=<>|")
    if punct >= 8:
        return True
    if len(s) >= 120 and (punct / max(1, len(s))) >= 0.06:
        return True
    return False


def _is_boilerplate_sentence(sent: str) -> bool:
    if not isinstance(sent, str):
        return True
    s = sent.strip()
    if len(s) < _MIN_SENT_LEN or len(s) > _MAX_SENT_LEN:
        return True
    low = s.lower()
    if sum(ch.isdigit() for ch in low) > max(10, len(low) // 3):
        return True
    if _is_code_like_sentence(s):
        return True
    return any(n in low for n in _BOILERPLATE_NEEDLES)


def _rank_sentences(query: str, docs: List[Dict[str, Any]], *, max_answer_chars: int) -> Dict[str, Any]:
    qtok = _tokenize(query) or _tokenize(query.lower())

    candidates: List[Dict[str, Any]] = []
    for doc in docs:
        url = str(doc.get("url", "") or "")
        clean = doc.get("clean_text")
        if not isinstance(clean, str) or not clean.strip():
            continue

        sents = _split_sentences(clean)[:_MAX_SENTS_PER_SOURCE]
        for idx, sent in enumerate(sents):
            if _is_boilerplate_sentence(sent):
                continue

            low = sent.lower()
            overlap = sum(1 for t in qtok if t in low)
            overlap_score = (0.22 * overlap) if overlap > 0 else -0.25

            pos_bonus = 0.9 if idx < 3 else (0.4 if idx < 10 else 0.0)

            slen = len(sent)
            len_bonus = 0.45 if 90 <= slen <= 240 else (0.15 if 60 <= slen < 90 else 0.0)

            score = overlap_score + (0.10 * pos_bonus) + (0.05 * len_bonus)
            candidates.append({"url": url, "sent": sent, "sent_idx": idx, "score": float(score)})

            if len(candidates) >= _MAX_CANDIDATE_SENTS:
                break

        if len(candidates) >= _MAX_CANDIDATE_SENTS:
            break

    if not candidates:
        for doc in docs:
            clean = doc.get("clean_text")
            if not isinstance(clean, str) or not clean.strip():
                continue
            txt = _normalize_text(clean)
            low = txt.lower()
            if any(n in low for n in _BOILERPLATE_NEEDLES) and len(txt) < 650:
                continue
            excerpt = txt[:max_answer_chars].strip()
            return {"answer": excerpt, "truncated": len(txt) > max_answer_chars, "selected": []}
        return {"answer": "", "truncated": False, "selected": []}

    candidates.sort(key=lambda c: (-c["score"], c["url"], c["sent_idx"], c["sent"]))

    out_parts: List[str] = []
    selected: List[Dict[str, Any]] = []
    used_urls: Dict[str, int] = {}
    used_sent_hashes: set[str] = set()
    total_len = 0
    truncated = False

    distinct_urls_available = len({c["url"] for c in candidates if c["url"]}) >= 2

    for c in candidates:
        url = c["url"]
        sent = c["sent"]

        norm = re.sub(r"\W+", "", sent.lower())[:220]
        if not norm or norm in used_sent_hashes:
            continue

        if distinct_urls_available and len(used_urls) < 2 and url in used_urls:
            continue
        if used_urls.get(url, 0) >= 2:
            continue

        add_len = len(sent) + (1 if out_parts else 0)
        if total_len + add_len > max_answer_chars:
            truncated = True
            break

        used_sent_hashes.add(norm)
        used_urls[url] = used_urls.get(url, 0) + 1
        selected.append(c)
        out_parts.append(sent)
        total_len += add_len

        if total_len >= max_answer_chars:
            truncated = True
            break
        if len(out_parts) >= 8:
            break

    answer = " ".join(out_parts).strip()
    return {"answer": answer, "truncated": truncated, "selected": selected}


def _dedupe_citations(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for c in citations:
        if not isinstance(c, dict):
            continue
        url = str(c.get("url", "") or "")
        start = c.get("start")
        end = c.get("end")
        quote = str(c.get("quote", "") or "")
        key = (url, int(start) if isinstance(start, int) else start, int(end) if isinstance(end, int) else end, quote[:90])
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def _citation_relevance_score(answer: str, c: Dict[str, Any]) -> float:
    quote = str(c.get("quote", "") or "")
    if not quote:
        return -999.0
    atok = set(_tokenize(answer))
    qtok = set(_tokenize(quote))
    if not atok or not qtok:
        return -10.0
    overlap = len(atok.intersection(qtok))
    ln = len(quote)
    len_bonus = 0.5 if 90 <= ln <= 260 else (0.2 if 60 <= ln < 90 else 0.0)
    return float(overlap) + len_bonus


def _select_best_citations(
    answer: str,
    citations: List[Dict[str, Any]],
    *,
    max_total: int,
    prefer_urls: Optional[List[str]] = None,
    per_url_cap: int = 3,
) -> List[Dict[str, Any]]:
    if not isinstance(answer, str) or not answer.strip():
        return []

    prefer_set = set([u for u in (prefer_urls or []) if isinstance(u, str) and u.strip()])

    scored: List[Tuple[int, float, str, int, Dict[str, Any]]] = []
    for c in citations:
        if not isinstance(c, dict):
            continue
        url = str(c.get("url", "") or "")
        idx = int(c.get("idx", 0) or 0)
        rel = _citation_relevance_score(answer, c)
        pref = 1 if url in prefer_set else 0
        scored.append((pref, rel, url, idx, c))

    scored.sort(key=lambda x: (-x[0], -x[1], x[2], x[3]))

    out: List[Dict[str, Any]] = []
    per_url: Dict[str, int] = {}
    cap = max(1, int(per_url_cap))

    for pref, rel, url, idx, c in scored:
        if len(out) >= max_total:
            break
        if per_url.get(url, 0) >= cap:
            continue
        out.append(c)
        per_url[url] = per_url.get(url, 0) + 1

    return out[:max_total]


def _fetch_with_retry(
    registry: Any,
    *,
    role: str,
    deps: Dict[str, Any],
    url: str,
    max_bytes: int,
    timeout_s: int,
    offline: bool,
) -> Dict[str, Any]:
    args = {"url": url, "max_bytes": max_bytes, "timeout_s": timeout_s}
    if offline:
        args["offline"] = True

    fd = _run_tool(registry, name="net.fetch", role=role, deps=deps, args=args)

    if bool(fd.get("truncated", False)) and max_bytes < HARD_FETCH_MAX_BYTES:
        retry_bytes = min(HARD_FETCH_MAX_BYTES, max(max_bytes + 1, int(max_bytes * 2)))
        args2 = {"url": url, "max_bytes": retry_bytes, "timeout_s": timeout_s}
        if offline:
            args2["offline"] = True
        fd2 = _run_tool(registry, name="net.fetch", role=role, deps=deps, args=args2)
        return fd2

    return fd


# ---------------------------------------------------------
# Handler
# ---------------------------------------------------------
def research_answer_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {"error": {"code": "INVALID_QUERY", "message": "Missing or invalid 'query'"}}
    query = query.strip()

    # role MUST default to GUEST (never OWNER).
    role = deps.get("role")
    if not isinstance(role, str) or not role.strip():
        role = "GUEST"
    role = role.strip().upper()

    # Enforce GUEST gating inside the tool (defense in depth).
    if not _guest_research_allowed(role, deps, args):
        now = 0.0 if _offline_requested(deps, args) else time.time()
        return {
            "error": {
                "code": "NOT_AUTHORIZED",
                "message": "Research is not enabled for this role. For GUEST, require allow_tools=true AND allow_research=true in context/policy.",
            },
            "query": query,
            "answered_at": now,
        }

    offline = _offline_requested(deps, args)

    top_k = _clamp(_safe_int(args.get("top_k"), DEFAULT_TOP_K), 1, HARD_TOP_K)
    fetch_max_bytes = _clamp(_safe_int(args.get("max_bytes"), DEFAULT_FETCH_MAX_BYTES), 1000, HARD_FETCH_MAX_BYTES)

    max_quotes = _clamp(_safe_int(args.get("max_quotes"), DEFAULT_MAX_QUOTES), 1, HARD_MAX_QUOTES)
    quote_len = _clamp(_safe_int(args.get("quote_len"), DEFAULT_QUOTE_LEN), 80, HARD_QUOTE_LEN)

    max_answer_chars = _clamp(_safe_int(args.get("max_answer_chars"), DEFAULT_MAX_ANSWER_CHARS), 200, HARD_MAX_ANSWER_CHARS)

    timeout_s = float(_clamp(_safe_int(args.get("timeout_s"), DEFAULT_TIMEOUT_S), 2, HARD_TIMEOUT_S))
    allow_degraded = _safe_bool(args.get("allow_degraded"), default=False)

    preferred_provider = args.get("preferred_provider")
    min_results = args.get("min_results")
    debug = _safe_bool(args.get("debug"), default=False)

    live_effective, strict_effective = _effective_mode(deps, args)

    registry = _get_tool_runner(deps)
    started_at = time.time()

    # 1) net.search
    search_args: Dict[str, Any] = {
        "query": query,
        "top_k": top_k,
        "timeout_s": int(timeout_s),
        "live": bool(live_effective),
        "strict": bool(strict_effective),
    }
    if offline:
        search_args["offline"] = True

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
        now = 0.0 if offline else time.time()
        return {
            "error": {"code": "SEARCH_FAILED", "message": str(e)},
            "query": query,
            "answered_at": now,
            "elapsed_ms": 0 if offline else int((time.time() - started_at) * 1000),
        }

    results = search_data.get("results", [])
    provider = search_data.get("provider")
    providers_tried = search_data.get("providers_tried")
    result_count = search_data.get("result_count")
    provider_debug = search_data.get("provider_debug") if debug else None

    degraded_search = bool(search_data.get("degraded", False)) or (provider == "mock-search") or offline

    if strict_effective and degraded_search and not allow_degraded:
        now = 0.0 if offline else time.time()
        out = {
            "error": {
                "code": "DEGRADED_RESULTS_BLOCKED",
                "message": "Search results were degraded/mock; refusing to answer in strict mode. Set allow_degraded=True to override explicitly.",
            },
            "query": query,
            "search": {
                "provider": provider,
                "providers_tried": providers_tried,
                "result_count": result_count,
                "degraded": True,
                "live_effective": live_effective,
                "strict_effective": strict_effective,
                "offline": offline,
            },
            "answered_at": now,
            "elapsed_ms": 0 if offline else int((time.time() - started_at) * 1000),
        }
        if debug and provider_debug is not None:
            out["search"]["provider_debug"] = provider_debug
        return out

    if not isinstance(results, list) or not results:
        now = 0.0 if offline else time.time()
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
                "offline": offline,
            },
            "note": "No search results",
            "answered_at": now,
            "elapsed_ms": 0 if offline else int((time.time() - started_at) * 1000),
        }
        if debug and provider_debug is not None:
            out["search"]["provider_debug"] = provider_debug
        return out

    sources: List[Dict[str, Any]] = []
    all_citations: List[Dict[str, Any]] = []
    docs_for_ranker: List[Dict[str, Any]] = []

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
            fetch_data = _fetch_with_retry(
                registry,
                role=role,
                deps=deps,
                url=url,
                max_bytes=fetch_max_bytes,
                timeout_s=int(timeout_s),
                offline=offline,
            )
        except Exception:
            continue

        content_type = fetch_data.get("content_type", "text/plain")
        content = fetch_data.get("content", "")
        if not isinstance(content, str):
            continue

        # 3) net.sanitize (propagate offline)
        try:
            sanitize_args = {"url": url, "content_type": content_type, "content": content, "max_bytes": fetch_max_bytes}
            if offline:
                sanitize_args["offline"] = True
            sanitize_data = _run_tool(registry, name="net.sanitize", role=role, deps=deps, args=sanitize_args)
        except Exception:
            continue

        clean_text = sanitize_data.get("clean_text", "")
        if not isinstance(clean_text, str) or not clean_text.strip():
            continue

        docs_for_ranker.append({"url": url, "title": title, "clean_text": clean_text})

        # 4) net.cite (propagate offline for deterministic captured_at)
        try:
            cite_args: Dict[str, Any] = {
                "url": url,
                "clean_text": clean_text,
                "query": query,
                "title": title,
                "snippet": snippet,
                "content_type": "text/plain",
                "max_quotes": max_quotes,
                "quote_len": quote_len,
            }
            if offline:
                cite_args["offline"] = True
            if retrieved_at_f is not None:
                cite_args["retrieved_at"] = retrieved_at_f

            cite_data = _run_tool(registry, name="net.cite", role=role, deps=deps, args=cite_args)
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

    now = 0.0 if offline else time.time()

    if not docs_for_ranker:
        out = {
            "query": query,
            "answer": "",
            "answer_truncated": False,
            "sources": sources,
            "citations": [],
            "degraded": bool(degraded_search),
            "search": {
                "provider": provider,
                "providers_tried": providers_tried,
                "result_count": result_count,
                "degraded": bool(degraded_search),
                "live_effective": live_effective,
                "strict_effective": strict_effective,
                "offline": offline,
            },
            "note": "No usable fetched/sanitized documents",
            "answered_at": now,
            "elapsed_ms": 0 if offline else int((time.time() - started_at) * 1000),
        }
        if debug and provider_debug is not None:
            out["search"]["provider_debug"] = provider_debug
        return out

    ranker_out = _rank_sentences(query, docs_for_ranker, max_answer_chars=max_answer_chars)
    answer_text = str(ranker_out.get("answer") or "").strip()
    answer_truncated = bool(ranker_out.get("truncated", False))

    if not answer_text and docs_for_ranker:
        txt = _normalize_text(str(docs_for_ranker[0].get("clean_text") or ""))
        answer_text = txt[:max_answer_chars].strip()
        answer_truncated = len(txt) > max_answer_chars

    citations_deduped = _dedupe_citations(all_citations)

    selected = ranker_out.get("selected", [])
    prefer_urls: List[str] = []
    if isinstance(selected, list):
        prefer_urls = [str(s.get("url") or "") for s in selected if isinstance(s, dict) and s.get("url")]

    max_total_cites = min(30, max_quotes * max(1, len(sources)))
    citations_final = _select_best_citations(
        answer_text,
        citations_deduped,
        max_total=max_total_cites,
        prefer_urls=prefer_urls,
        per_url_cap=3,
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
            "offline": offline,
        },
        "answered_at": now,
        "elapsed_ms": 0 if offline else int((time.time() - started_at) * 1000),
        "note": "research.answer (Phase 7.3, composed, deterministic sentence-ranked + citation relevance, read-only)",
    }

    if debug and provider_debug is not None:
        out["search"]["provider_debug"] = provider_debug
    if debug:
        out["selected_sentences"] = selected

    return out


RESEARCH_ANSWER_T = ToolSpec(
    name="research.answer",
    description="Answer a query using composed net.* pipeline (read-only, deterministic, safe).",
    required_role="GUEST",
    allowed_roles=("OWNER", "GUEST"),
    state_changing=False,
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
        "preferred_provider": {"type": "string", "required": False, "description": "Optional preferred net.search provider"},
        "min_results": {"type": "integer", "required": False, "description": "Try providers until at least this many raw results are collected"},
        "debug": {"type": "boolean", "required": False, "description": "Include provider_debug (and selected_sentences) for diagnostics"},
        "offline": {"type": "boolean", "required": False, "description": "Force deterministic offline simulation (tests/FrontDoor)"},
        "allow_guest_research": {"type": "boolean", "required": False, "description": "Internal override for direct tool tests"},
        "context": {"type": "object", "required": False, "description": "Optional context passthrough (allow_tools/allow_research)"},
    },
    handler=research_answer_handler,
)


def register_research_tools(registry: Any) -> None:
    registry.register(RESEARCH_ANSWER_T)
