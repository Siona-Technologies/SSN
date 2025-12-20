# ssn/tools/research_propose.py

from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from ssn.tools.contracts import ToolSpec


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

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


def _truncate(s: Any, n: int) -> str:
    if not isinstance(s, str):
        return ""
    return s[: max(0, n)]


def _tool_fail(step: str, tool_err: Any, fallback_code: str) -> Dict[str, Any]:
    if isinstance(tool_err, dict) and tool_err.get("code"):
        return {"error": {"step": step, **tool_err}}
    return {"error": {"step": step, "code": fallback_code, "message": f"{step} failed"}}


def _normalize_proposal_id(data: Any) -> Optional[str]:
    if isinstance(data, dict):
        for k in ("proposal_id", "proposalId", "id"):
            v = data.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        p = data.get("proposal")
        if isinstance(p, dict):
            v = p.get("id") or p.get("proposal_id")
            if isinstance(v, str) and v.strip():
                return v.strip()
    return None


def _env_on(name: str) -> bool:
    return os.getenv(name) == "1"


# ---------------------------------------------------------
# Question simplifier (helps strict live when OpenSearch/engines return nothing)
# ---------------------------------------------------------

_Q_LEAD = re.compile(r"^\s*(what|who|where|when|why|how)\b\s*(is|are|was|were|do|does|did|can|could|should|would)?\s*",
                     re.IGNORECASE)
_Q_TAIL = re.compile(r"\?\s*$")
_STOP = set((
    "the", "a", "an", "is", "are", "was", "were", "to", "of", "for", "and", "or", "in", "on", "at",
    "used", "use", "using", "about", "please", "explain", "tell", "me"
))

def _simplify_query(q: str) -> str:
    """
    Turn question-style query into keyword-style query:
      "What is Example Domain used for?" -> "Example Domain"
    Keep it short and stable.
    """
    s = (q or "").strip()
    s = _Q_TAIL.sub("", s)
    s = _Q_LEAD.sub("", s).strip()
    # collapse whitespace, strip punctuation-ish
    s = re.sub(r"[\"'`]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    if not s:
        return (q or "").strip()

    toks = [t for t in re.split(r"[^A-Za-z0-9]+", s) if t]
    if not toks:
        return s

    kept = [t for t in toks if t.lower() not in _STOP]
    if not kept:
        kept = toks

    # keep up to 6 tokens to avoid over-long queries
    return " ".join(kept[:6]).strip() or s


# ---------------------------------------------------------
# Fact extraction (robust against boilerplate/CSS)
# ---------------------------------------------------------

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WS = re.compile(r"\s+")
_TAGGY = re.compile(r"<[^>]+>")
_CTRL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

_BAD_PATTERNS = (
    r"\.is-hidden\b",
    r"\bdisplay\s*:\s*none\b",
    r"\bvar\(--",
    r"\b!important\b",
    r"\bclip:\s*rect\b",
    r"\bno-js\b",
    r"\blazyload\b",
    r"\bsvg\b",
    r"\bfunction\s*\(",
    r"\bwindow\.",
    r"\bdocument\.",
)

_BAD_RE = re.compile("|".join(_BAD_PATTERNS), re.IGNORECASE)


def _clean_text_minimally(text: str) -> str:
    if not isinstance(text, str):
        return ""
    t = _CTRL.sub(" ", text)
    t = _TAGGY.sub(" ", t)
    t = _WS.sub(" ", t).strip()
    return t


def _looks_like_boilerplate(s: str) -> bool:
    if not s:
        return True

    alpha = sum(1 for c in s if c.isalpha())
    if alpha < 20:
        return True

    if _BAD_RE.search(s):
        return True

    punct = sum(1 for c in s if c in "{}[];<>")
    if punct >= 6:
        return True

    lowered = s.lower()
    nav_needles = ("jump to content", "create account", "log in", "donate", "privacy policy", "cookie")
    if any(n in lowered for n in nav_needles):
        return True

    return False


def _keyword_set(query: str) -> List[str]:
    q = (query or "").lower()
    toks = [t for t in re.split(r"[^a-z0-9]+", q) if len(t) >= 4]
    anchors = ["siona", "samson", "sibona", "njaji", "owner", "law", "orchestrator", "brain", "memory", "tool"]
    out: List[str] = []
    seen = set()
    for t in anchors + toks:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out[:20]


def _score_sentence(s: str, keywords: List[str]) -> float:
    sl = s.lower()
    score = 0.0

    n = len(s)
    if 60 <= n <= 220:
        score += 2.0
    elif 40 <= n < 60:
        score += 1.0
    elif n > 320:
        score -= 1.5

    hits = 0
    for k in keywords:
        if k in sl:
            hits += 1
    score += min(3.0, hits * 0.6)

    if _looks_like_boilerplate(s):
        score -= 5.0

    return score


def _extract_fact_texts(text: str, *, query: str, max_facts: int, max_len: int) -> List[str]:
    t = _clean_text_minimally(text)
    if not t:
        return []

    parts = _SENT_SPLIT.split(t)
    if len(parts) < 3:
        parts = re.split(r"\s{2,}", t)

    keywords = _keyword_set(query)

    scored: List[Tuple[float, str]] = []
    for p in parts:
        s = p.strip()
        if not s:
            continue
        s = _truncate(s, max_len).strip()
        if not s:
            continue
        scored.append((_score_sentence(s, keywords), s))

    scored.sort(key=lambda x: x[0], reverse=True)

    out: List[str] = []
    seen = set()
    for score, s in scored:
        if score < -1.0:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
        if len(out) >= max_facts:
            break

    return out


def _fallback_fact_from_source(query: str, src_title: Optional[str], src_url: Optional[str], fact_len: int) -> str:
    title = (src_title or "").strip()
    url = (src_url or "").strip()
    base = f"Research was performed for query '{query}'."
    if title and url:
        base += f" Source reviewed: {title} ({url})."
    elif url:
        base += f" Source reviewed: {url}."
    return _truncate(base, fact_len).strip()


def _is_degraded_ingest(ingest_data: Dict[str, Any]) -> bool:
    try:
        search = ingest_data.get("search") or {}
        if isinstance(search, dict) and bool(search.get("degraded", False)):
            return True
    except Exception:
        pass

    try:
        selected = ingest_data.get("selected_source") or {}
        if isinstance(selected, dict):
            src = str(selected.get("source", "") or "").lower().strip()
            url = str(selected.get("url", "") or "").lower().strip()
            if src == "mock-search":
                return True
            if "example.com" in url:
                return True
    except Exception:
        pass

    return False


def _default_allow_degraded(*, offline: bool, live_search: bool) -> bool:
    if offline:
        return True
    if not live_search:
        return True
    return False


# ---------------------------------------------------------
# Handler
# ---------------------------------------------------------

def research_propose_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    tools = deps.get("tools")
    if tools is None:
        return {"error": {"code": "MISSING_DEPS", "message": "deps['tools'] is required"}}

    role = deps.get("role", "OWNER")

    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {"error": {"code": "INVALID_QUERY", "message": "Missing or invalid 'query'"}}
    query = query.strip()

    top_k = max(1, min(_safe_int(args.get("top_k"), 3), 5))
    max_bytes = max(1_000, min(_safe_int(args.get("max_bytes"), 50_000), 200_000))
    max_answer_chars = max(100, min(_safe_int(args.get("max_answer_chars"), 800), 3000))

    max_facts = max(1, min(_safe_int(args.get("max_facts"), 6), 12))
    fact_len = max(60, min(_safe_int(args.get("fact_len"), 180), 400))

    offline = _env_on("SSN_OFFLINE")

    # LIVE by default (production):
    # - if caller explicitly sets live_search/live, that wins
    # - else env SSN_LIVE_SEARCH decides
    if "live_search" in args:
        live_search = _safe_bool(args.get("live_search"), default=True)
    elif "live" in args:
        live_search = _safe_bool(args.get("live"), default=True)
    else:
        live_search = _env_on("SSN_LIVE_SEARCH")

    if offline:
        live_search = False

    # STRICT by default follows env unless caller overrides
    if "strict_live" in args:
        strict_live = _safe_bool(args.get("strict_live"), default=False)
    elif "strict" in args:
        strict_live = _safe_bool(args.get("strict"), default=False)
    else:
        strict_live = _env_on("SSN_LIVE_STRICT")

    if offline:
        strict_live = False

    allow_degraded = _safe_bool(
        args.get("allow_degraded"),
        default=_default_allow_degraded(offline=offline, live_search=live_search),
    )

    timeout_s = max(2, min(_safe_int(args.get("timeout_s"), 10), 20))

    # --------------------------
    # 1) research.ingest (attempt 1)
    # --------------------------
    ing = tools.run(
        name="research.ingest",
        role=role,
        deps=deps,
        args={
            "query": query,
            "top_k": top_k,
            "max_bytes": max_bytes,
            "max_answer_chars": max_answer_chars,
            "live_search": live_search,
            "strict_live": strict_live,
            "timeout_s": timeout_s,
            "disambiguate": args.get("disambiguate"),
        },
    )

    # If strict-live no-results, retry with simplified query (still strict)
    if not ing.ok:
        err = ing.error or {}
        if (
            isinstance(err, dict)
            and err.get("step") == "net.search"
            and err.get("code") in ("SEARCH_NO_RESULTS", "NO_RESULTS")
            and live_search
        ):
            simple_q = _simplify_query(query)
            if simple_q and simple_q.lower() != query.lower():
                ing = tools.run(
                    name="research.ingest",
                    role=role,
                    deps=deps,
                    args={
                        "query": simple_q,
                        "top_k": top_k,
                        "max_bytes": max_bytes,
                        "max_answer_chars": max_answer_chars,
                        "live_search": live_search,
                        "strict_live": strict_live,
                        "timeout_s": timeout_s,
                        "disambiguate": args.get("disambiguate"),
                    },
                )

    if not ing.ok:
        return _tool_fail("research.ingest", ing.error, "INGEST_FAILED")

    ingest_data = ing.data or {}
    degraded = _is_degraded_ingest(ingest_data)

    selected = ingest_data.get("selected_source") or {}
    src_url = selected.get("url") if isinstance(selected, dict) else None
    src_title = selected.get("title") if isinstance(selected, dict) else None
    src_provider = selected.get("source") if isinstance(selected, dict) else None

    if degraded and not allow_degraded:
        return {
            "error": {
                "step": "research.ingest",
                "code": "DEGRADED_RESULTS_BLOCKED",
                "message": "Search results were degraded/mock; refusing to create a memory proposal. Set allow_degraded=True to override explicitly.",
            }
        }

    # --------------------------
    # 2) Build text pool: prefer cite quotes, else answer
    # --------------------------
    answer_text = str(ingest_data.get("answer", "") or "")

    cite_bundle = ingest_data.get("cite") or {}
    cite_quotes: List[str] = []
    if isinstance(cite_bundle, dict):
        citations = cite_bundle.get("citations") or []
        if isinstance(citations, list):
            for c in citations[:8]:
                if isinstance(c, dict) and isinstance(c.get("quote"), str):
                    q = c["quote"].strip()
                    if q:
                        cite_quotes.append(q)

    text_pool = " ".join(cite_quotes).strip() or answer_text

    # --------------------------
    # 3) Extract facts
    # --------------------------
    fact_texts = _extract_fact_texts(
        text_pool,
        query=query,
        max_facts=max_facts,
        max_len=fact_len,
    )
    if not fact_texts:
        fact_texts = [_fallback_fact_from_source(query, src_title, src_url, fact_len)]

    base_conf = 0.55
    if degraded or (isinstance(src_provider, str) and src_provider.strip().lower() == "mock-search"):
        base_conf = 0.35

    facts_kv: List[Dict[str, Any]] = []
    for i, t in enumerate(fact_texts):
        obj: Dict[str, Any] = {
            "key": f"research_fact_{i+1}",
            "value": _truncate(t, fact_len).strip(),
            "confidence": float(base_conf),
        }
        if isinstance(src_url, str) and src_url.strip():
            obj["source_url"] = src_url.strip()
        if isinstance(src_title, str) and src_title.strip():
            obj["source_title"] = src_title.strip()
        facts_kv.append(obj)

    summary = _truncate(
        f"Research proposal: {query}. Source: {src_title or src_url or 'unknown'}",
        320,
    ).strip()

    # --------------------------
    # 4) memory.propose
    # --------------------------
    mem_args = {
        "summary": summary,

        "facts": facts_kv,
        "items": facts_kv,
        "entries": facts_kv,
        "proposals": facts_kv,
        "candidate_facts": facts_kv,

        "facts_text": [f.get("value", "") for f in facts_kv],
        "raw_facts": [f.get("value", "") for f in facts_kv],

        "source": {
            "type": "research",
            "query": query,
            "url": src_url,
            "title": src_title,
            "provider": src_provider,
            "degraded": bool(degraded),
            "offline": bool(offline),
        },
        "origin": "research.propose",
        "created_at": time.time(),
    }

    mem = tools.run(
        name="memory.propose",
        role=role,
        deps=deps,
        args=mem_args,
    )
    if not mem.ok:
        return _tool_fail("memory.propose", mem.error, "MEMORY_PROPOSE_FAILED")

    mem_data = mem.data or {}
    proposal_id = _normalize_proposal_id(mem_data)

    return {
        "query": query,
        "proposal_id": proposal_id,
        "proposal": mem_data,
        "facts": facts_kv,
        "facts_text": [f.get("value", "") for f in facts_kv],
        "ingest": ingest_data,
        "proposed_at": time.time(),
        "offline": bool(offline),
        "degraded": bool(degraded),
        "allow_degraded": bool(allow_degraded),
        "live_search": bool(live_search),
        "strict_live": bool(strict_live),
    }


# ---------------------------------------------------------
# ToolSpec
# ---------------------------------------------------------

RESEARCH_PROPOSE_T = ToolSpec(
    name="research.propose",
    description="Run research.ingest, extract facts, and create a memory proposal (OWNER approval required).",
    required_role="OWNER",
    allowed_roles=("OWNER",),
    state_changing=False,
    external_effect=True,
    public=False,
    max_calls_per_minute=20,
    input_schema={
        "query": {"type": "string", "required": True, "description": "Research query"},
        "top_k": {"type": "integer", "required": False, "description": "Search results to consider (1–5)"},
        "max_bytes": {"type": "integer", "required": False, "description": "Fetch cap (hard capped)"},
        "max_answer_chars": {"type": "integer", "required": False, "description": "Answer cap"},
        "max_facts": {"type": "integer", "required": False, "description": "Max candidate facts (1–12)"},
        "fact_len": {"type": "integer", "required": False, "description": "Max chars per fact (60–400)"},
        "timeout_s": {"type": "integer", "required": False, "description": "Network timeout seconds (2–20)"},

        # live controls (env-backed defaults)
        "live_search": {"type": "boolean", "required": False, "description": "Prefer live search (default from env SSN_LIVE_SEARCH)"},
        "strict_live": {"type": "boolean", "required": False, "description": "Strict live search (default from env SSN_LIVE_STRICT)"},
        "live": {"type": "boolean", "required": False, "description": "Alias for live_search"},
        "strict": {"type": "boolean", "required": False, "description": "Alias for strict_live"},

        "allow_degraded": {"type": "boolean", "required": False, "description": "Override: allow proposals even if net.search degrades to mock/fallback"},
        "disambiguate": {"type": "boolean", "required": False, "description": "Pass-through disambiguation setting to research.ingest"},
    },
    handler=research_propose_handler,
)
