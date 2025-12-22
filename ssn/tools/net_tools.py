"""
Network tools — Phase 7.3 (Hardening)

READ-ONLY
SAFE
OFFLINE-COMPATIBLE

Behavior:
- Default: offline-safe deterministic mock (keeps tests stable)
- Live mode (optional): multi-provider search with bounded HTTP and fallback:
    0) Brave Search API (reliable; requires SSN_BRAVE_API_KEY)
    1) DuckDuckGo HTML (scrape; often blocked)
    2) DuckDuckGo Lite (scrape; often blocked)
    3) Wikipedia OpenSearch API (reliable, no key)
    4) Mock fallback (ONLY if strict_live is False)

Hardening additions (Phase 7.3):
- args: preferred_provider (optional), min_results (optional)
- always include provider_debug when debug=True (even if provider succeeds)
- Brave: bounded retry/backoff for transient HTTP (429/5xx), deadline-capped
- DDG: improved block detection, graceful skip with reason="blocked"
- Deterministic ranking/merge across providers (no LLM)

Enable live search:
- args {"live": True} OR env SSN_LIVE_SEARCH=1

Force offline:
- env SSN_OFFLINE=1  (always mock)

Strict live:
- args {"strict": True} OR env SSN_LIVE_STRICT=1
- Meaning: NO mock fallback (but Wikipedia fallback is still allowed)

Brave Search API:
- env SSN_BRAVE_API_KEY=<token>
- optional: SSN_BRAVE_COUNTRY=KE / US / GB ...
- optional: SSN_BRAVE_LANG=en / en-US / sw ...

Debug:
- args {"debug": True} -> includes provider_debug with failure reasons
"""

from __future__ import annotations

import html as _html
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from ssn.tools.contracts import ToolSpec


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

_MAX_QUERY_LEN = 240
_MAX_HTTP_BYTES = 220_000

_RE_TAGS = re.compile(r"<[^>]+>", re.IGNORECASE)
_RE_WS = re.compile(r"\s+")

_TRANSIENT_HTTP = {429, 500, 502, 503, 504}

_PROVIDER_WEIGHT = {
    "brave-search": 3.0,
    "wikipedia-opensearch": 2.0,
    "duckduckgo-html": 1.0,
    "duckduckgo-lite": 0.8,
    "mock-search": 0.0,
}


class ProviderBlocked(Exception):
    """Provider returned a bot wall/captcha/blocked page."""


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


def _env_str(name: str) -> Optional[str]:
    v = os.getenv(name)
    if isinstance(v, str):
        v = v.strip()
        if v:
            return v
    return None


def _clip_query(q: str, max_len: int = _MAX_QUERY_LEN) -> str:
    q = (q or "").strip()
    q = _RE_WS.sub(" ", q)
    return q[:max_len]


def _sanitize_text(text: str, *, max_len: int = 500) -> str:
    if not isinstance(text, str):
        return ""
    text = text.replace("\n", " ").replace("\r", " ").strip()
    text = _RE_WS.sub(" ", text)
    return text[:max_len]


def _strip_tags(s: str) -> str:
    if not isinstance(s, str):
        return ""
    return _RE_TAGS.sub(" ", s)


def _is_http_url(u: str) -> bool:
    try:
        p = urlparse(u)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def _decode_ddg_redirect(url: str) -> str:
    """
    DuckDuckGo sometimes returns redirect links like:
      https://duckduckgo.com/l/?uddg=<ENCODED_URL>
    Decode uddg when present.
    """
    try:
        p = urlparse(url)
        qs = parse_qs(p.query)
        if "uddg" in qs and qs["uddg"]:
            return unquote(qs["uddg"][0])
    except Exception:
        pass
    return url


def _looks_like_block_page(html_text: str) -> bool:
    if not isinstance(html_text, str) or not html_text.strip():
        return True

    lowered = html_text.lower()
    needles = (
        "captcha",
        "verify you are a human",
        "unusual traffic",
        "temporarily unavailable",
        "access denied",
        "robot",
        "blocked",
        "too many requests",
        "rate limit",
        "cloudflare",
        "/cdn-cgi/",
        "cf-chl",
        "attention required",
        "checking your browser",
        "please enable cookies",
        "press and hold",
    )
    return any(n in lowered for n in needles)


def _http_get_text(
    url: str,
    *,
    timeout_s: float,
    max_bytes: int,
    headers: Dict[str, str],
) -> str:
    # Keep headers minimal; avoid Accept-Encoding to prevent gzip surprises in urllib.
    req = Request(url, headers=headers, method="GET")
    with urlopen(req, timeout=timeout_s) as resp:
        data = resp.read(max_bytes + 1)
        data = data[:max_bytes]
        return data.decode("utf-8", errors="replace")


def _normalize_result(title: str, url: str, snippet: str, source: str) -> Optional[Dict[str, Any]]:
    url = (url or "").strip()
    if not url or not _is_http_url(url):
        return None
    return {
        "title": _sanitize_text(title or "", max_len=140),
        "url": url,
        "snippet": _sanitize_text(snippet or "", max_len=300),
        "source": source,
        "retrieved_at": time.time(),
    }


def _norm_url_for_dedupe(u: str) -> str:
    try:
        p = urlparse((u or "").strip())
        if p.scheme not in ("http", "https"):
            return ""
        host = (p.netloc or "").lower()
        path = p.path or "/"
        # drop fragment, keep query (some sites encode identity in query)
        return f"{p.scheme.lower()}://{host}{path}?{p.query}"
    except Exception:
        return ""


def _tokenize(s: str) -> List[str]:
    s = (s or "").lower()
    toks = re.split(r"[^a-z0-9]+", s)
    return [t for t in toks if len(t) >= 3]


def _score_result(query: str, r: Dict[str, Any], rank_in_provider: int) -> float:
    qtok = _tokenize(query)
    hay = f"{r.get('title','')} {r.get('snippet','')}".lower()
    overlap = sum(1 for t in qtok if t in hay)

    snippet_len = len(r.get("snippet") or "")
    snippet_quality = 1.0 if 80 <= snippet_len <= 300 else 0.0

    source = str(r.get("source") or "")
    w = float(_PROVIDER_WEIGHT.get(source, 0.5))

    # deterministic penalties
    rank_penalty = 0.10 * float(rank_in_provider)
    return w + 0.15 * float(overlap) + 0.10 * float(snippet_quality) - rank_penalty


def _merge_rank_results(
    query: str,
    provider_batches: List[List[Dict[str, Any]]],
    max_out: int,
) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    scored: List[Tuple[float, str, Dict[str, Any]]] = []

    for batch in provider_batches:
        for idx, r in enumerate(batch):
            if not isinstance(r, dict):
                continue
            u = str(r.get("url", "") or "")
            key = _norm_url_for_dedupe(u)
            if not key or key in seen:
                continue
            seen.add(key)
            s = _score_result(query, r, idx)
            scored.append((s, key, r))

    scored.sort(key=lambda x: (-x[0], x[1]))  # deterministic tie-breaker by URL key
    return [r for _, _, r in scored[:max_out]]


# ---------------------------------------------------------
# Provider 0: Brave Search API (reliable; requires key)
# ---------------------------------------------------------

def _brave_search(query: str, *, top_k: int, timeout_s: float) -> List[Dict[str, Any]]:
    key = _env_str("SSN_BRAVE_API_KEY")
    if not key:
        return []

    # Cap Brave provider time to keep overall tool bounded even with retries
    provider_deadline = time.time() + min(4.0, float(timeout_s))

    q = quote_plus(_clip_query(query, _MAX_QUERY_LEN))
    country = _env_str("SSN_BRAVE_COUNTRY")
    lang = _env_str("SSN_BRAVE_LANG")

    url = f"https://api.search.brave.com/res/v1/web/search?q={q}&count={min(top_k, 10)}"
    if country:
        url += f"&country={quote_plus(country)}"
    if lang:
        url += f"&search_lang={quote_plus(lang)}"

    backoffs = (0.25, 0.75)  # deterministic, bounded (total attempts = 3)

    for attempt in range(1 + len(backoffs)):
        remaining = provider_deadline - time.time()
        if remaining <= 0:
            break

        try:
            text = _http_get_text(
                url,
                timeout_s=max(0.5, remaining),
                max_bytes=_MAX_HTTP_BYTES,
                headers={
                    "User-Agent": "SSN/1.0",
                    "Accept": "application/json",
                    "X-Subscription-Token": key,
                },
            )
            data = json.loads(text)

            web = data.get("web") if isinstance(data, dict) else None
            results = (web.get("results") if isinstance(web, dict) else None) or []
            if not isinstance(results, list) or not results:
                return []

            out: List[Dict[str, Any]] = []
            for r in results[:top_k]:
                if not isinstance(r, dict):
                    continue
                title = str(r.get("title", "") or "")
                urlv = str(r.get("url", "") or "")
                desc = r.get("description") or r.get("snippet") or r.get("meta_description") or ""
                snippet = str(desc or "")
                nr = _normalize_result(title, urlv, snippet, "brave-search")
                if nr:
                    out.append(nr)
            return out

        except HTTPError as e:
            code = getattr(e, "code", None)
            if isinstance(code, int) and code in _TRANSIENT_HTTP and attempt < len(backoffs):
                time.sleep(backoffs[attempt])
                continue
            return []
        except (URLError, json.JSONDecodeError):
            return []
        except Exception:
            return []

    return []


# ---------------------------------------------------------
# Provider 1: DuckDuckGo HTML parsing
# ---------------------------------------------------------

_RE_RESULT_A = re.compile(
    r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_RE_SNIPPET = re.compile(
    r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>|<div[^>]+class="result__snippet"[^>]*>(.*?)</div>',
    re.IGNORECASE | re.DOTALL,
)


def _ddg_html_search(query: str, *, top_k: int, timeout_s: float) -> List[Dict[str, Any]]:
    q = quote_plus(_clip_query(query, _MAX_QUERY_LEN))
    url = f"https://duckduckgo.com/html/?q={q}"

    html_text = _http_get_text(
        url,
        timeout_s=timeout_s,
        max_bytes=_MAX_HTTP_BYTES,
        headers={
            "User-Agent": "SSN/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )

    if _looks_like_block_page(html_text):
        raise ProviderBlocked("ddg_html_blocked")

    anchors = _RE_RESULT_A.findall(html_text)
    if not anchors:
        return []

    snippet_matches = _RE_SNIPPET.findall(html_text)
    snippets: List[str] = []
    for a, b in snippet_matches:
        raw = a or b or ""
        raw = _html.unescape(_strip_tags(raw))
        snippets.append(_sanitize_text(raw, max_len=300))

    out: List[Dict[str, Any]] = []
    for i, (href, title_html) in enumerate(anchors[:top_k]):
        title = _html.unescape(_strip_tags(title_html))
        u = _decode_ddg_redirect(_html.unescape((href or "").strip()))
        snippet = snippets[i] if i < len(snippets) else ""
        nr = _normalize_result(title, u, snippet, "duckduckgo-html")
        if nr:
            out.append(nr)
    return out


# ---------------------------------------------------------
# Provider 2: DuckDuckGo Lite parsing (fallback)
# ---------------------------------------------------------

_RE_LITE_LINK = re.compile(
    r'<a[^>]+class="result-link"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_RE_LITE_SNIPPET = re.compile(
    r'<td[^>]+class="result-snippet"[^>]*>(.*?)</td>',
    re.IGNORECASE | re.DOTALL,
)


def _ddg_lite_search(query: str, *, top_k: int, timeout_s: float) -> List[Dict[str, Any]]:
    q = quote_plus(_clip_query(query, _MAX_QUERY_LEN))
    url = f"https://lite.duckduckgo.com/lite/?q={q}"

    html_text = _http_get_text(
        url,
        timeout_s=timeout_s,
        max_bytes=_MAX_HTTP_BYTES,
        headers={
            "User-Agent": "SSN/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )

    if _looks_like_block_page(html_text):
        raise ProviderBlocked("ddg_lite_blocked")

    links = _RE_LITE_LINK.findall(html_text)
    if not links:
        return []

    snippets_raw = _RE_LITE_SNIPPET.findall(html_text)
    snippets: List[str] = []
    for s in snippets_raw:
        snippets.append(_sanitize_text(_html.unescape(_strip_tags(s)), max_len=300))

    out: List[Dict[str, Any]] = []
    for i, (href, title_html) in enumerate(links[:top_k]):
        title = _html.unescape(_strip_tags(title_html))
        u = _decode_ddg_redirect(_html.unescape((href or "").strip()))
        snippet = snippets[i] if i < len(snippets) else ""
        nr = _normalize_result(title, u, snippet, "duckduckgo-lite")
        if nr:
            out.append(nr)
    return out


# ---------------------------------------------------------
# Provider 3: Wikipedia OpenSearch (reliable, no key)
# ---------------------------------------------------------

def _wiki_normalize_query(q: str) -> str:
    q = (q or "").strip()
    q = re.sub(r'-"[^"]+"', " ", q)
    q = re.sub(r"-\S+", " ", q)
    q = q.replace('"', " ")
    q = _RE_WS.sub(" ", q).strip()
    return _clip_query(q, 120)


def _wiki_opensearch(query: str, *, top_k: int, timeout_s: float) -> List[Dict[str, Any]]:
    qn = _wiki_normalize_query(query)
    if not qn:
        return []

    q = quote_plus(qn)
    url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={q}&limit={top_k}&namespace=0&format=json"

    text = _http_get_text(
        url,
        timeout_s=timeout_s,
        max_bytes=200_000,
        headers={
            "User-Agent": "SSN/1.0",
            "Accept": "application/json,text/plain;q=0.9,*/*;q=0.8",
        },
    )

    try:
        data = json.loads(text)
        titles = data[1] if len(data) > 1 else []
        descs = data[2] if len(data) > 2 else []
        urls = data[3] if len(data) > 3 else []
    except Exception:
        return []

    out: List[Dict[str, Any]] = []
    for i in range(min(top_k, len(titles), len(urls))):
        title = str(titles[i])
        snippet = str(descs[i]) if i < len(descs) else ""
        urlv = str(urls[i])
        nr = _normalize_result(title, urlv, snippet, "wikipedia-opensearch")
        if nr:
            out.append(nr)
    return out


# ---------------------------------------------------------
# Mock fallback (deterministic + stable URL)
# ---------------------------------------------------------

def _mock_results(query: str, *, top_k: int) -> List[Dict[str, Any]]:
    stable_url = "https://example.com/"
    results: List[Dict[str, Any]] = []
    for i in range(top_k):
        results.append(
            {
                "title": _sanitize_text(f"Simulated search result {i + 1} for '{query}'", max_len=140),
                "url": stable_url,
                "snippet": _sanitize_text(
                    "This is a simulated search result used for safe pipeline testing.",
                    max_len=300,
                ),
                "source": "mock-search",
                "retrieved_at": time.time(),
            }
        )
    return results


# ---------------------------------------------------------
# net.search handler
# ---------------------------------------------------------

def net_search_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {"error": {"code": "INVALID_QUERY", "message": "Missing or invalid 'query' string"}}
    query = query.strip()

    top_k = max(1, min(_safe_int(args.get("top_k"), 5), 10))

    # Phase 7.3 hardening args
    preferred = args.get("preferred_provider")
    preferred_provider = str(preferred).strip().lower() if isinstance(preferred, str) and preferred.strip() else None

    min_results = _safe_int(args.get("min_results"), min(5, top_k))
    min_results = max(1, min(min_results, top_k))

    forced_offline = os.getenv("SSN_OFFLINE") == "1"
    debug = _safe_bool(args.get("debug"), default=False)

    # live: args overrides env if explicitly provided
    env_live = os.getenv("SSN_LIVE_SEARCH") == "1"
    if "live" in args:
        live = _safe_bool(args.get("live"), default=False) and not forced_offline
    else:
        live = env_live and not forced_offline

    # strict: args overrides env if explicitly provided
    env_strict = os.getenv("SSN_LIVE_STRICT") == "1"
    if "strict" in args:
        strict_live = _safe_bool(args.get("strict"), default=False)
    else:
        strict_live = env_strict

    timeout_s = float(_safe_int(args.get("timeout_s"), 10))
    timeout_s = max(2.0, min(timeout_s, 20.0))

    if not live:
        results = _mock_results(query, top_k=top_k)
        out = {
            "query": query,
            "provider": "mock-search",
            "providers_tried": ["mock-search"],
            "result_count": len(results),
            "results": results,
            "degraded": True,
            "note": "Simulated net.search (offline-safe; set live=True or SSN_LIVE_SEARCH=1 for real search)",
        }
        # Debug in offline mode can still be helpful/consistent
        if debug:
            out["provider_debug"] = [{"provider": "mock-search", "ok": True, "reason": None, "result_count": len(results)}]
        return out

    providers_tried: List[str] = []
    provider_debug: List[Dict[str, Any]] = []

    def _try(fn, name: str) -> List[Dict[str, Any]]:
        providers_tried.append(name)
        t0 = time.time()
        try:
            res = fn(query, top_k=top_k, timeout_s=timeout_s)
            provider_debug.append(
                {
                    "provider": name,
                    "ok": bool(res),
                    "reason": None if res else "empty",
                    "result_count": len(res) if res else 0,
                    "elapsed_ms": int((time.time() - t0) * 1000),
                }
            )
            return res
        except ProviderBlocked:
            provider_debug.append(
                {
                    "provider": name,
                    "ok": False,
                    "reason": "blocked",
                    "result_count": 0,
                    "elapsed_ms": int((time.time() - t0) * 1000),
                }
            )
            return []
        except HTTPError as e:
            code = getattr(e, "code", None)
            provider_debug.append(
                {
                    "provider": name,
                    "ok": False,
                    "reason": f"http_{code}" if code is not None else "http_error",
                    "result_count": 0,
                    "elapsed_ms": int((time.time() - t0) * 1000),
                }
            )
            return []
        except URLError:
            provider_debug.append(
                {
                    "provider": name,
                    "ok": False,
                    "reason": "url_error",
                    "result_count": 0,
                    "elapsed_ms": int((time.time() - t0) * 1000),
                }
            )
            return []
        except Exception:
            provider_debug.append(
                {
                    "provider": name,
                    "ok": False,
                    "reason": "exception",
                    "result_count": 0,
                    "elapsed_ms": int((time.time() - t0) * 1000),
                }
            )
            return []

    providers: List[Tuple[str, Any]] = [
        ("brave-search", _brave_search),
        ("duckduckgo-html", _ddg_html_search),
        ("duckduckgo-lite", _ddg_lite_search),
        ("wikipedia-opensearch", _wiki_opensearch),
    ]

    if preferred_provider:
        providers = sorted(providers, key=lambda x: (0 if x[0] == preferred_provider else 1))

    batches: List[List[Dict[str, Any]]] = []

    for name, fn in providers:
        if name == "brave-search" and not _env_str("SSN_BRAVE_API_KEY"):
            providers_tried.append("brave-search (missing SSN_BRAVE_API_KEY)")
            provider_debug.append({"provider": "brave-search", "ok": False, "reason": "missing_api_key", "result_count": 0})
            continue

        res = _try(fn, name)
        if res:
            batches.append(res)
            if sum(len(b) for b in batches) >= min_results:
                break

    if batches:
        ranked = _merge_rank_results(query, batches, max_out=top_k)
        out = {
            "query": query,
            "provider": "ranked-aggregate",
            "providers_tried": providers_tried,
            "result_count": len(ranked),
            "results": ranked,
            "degraded": False,
            "note": "Live net.search (ranked aggregate, bounded)",
        }
        if debug:
            out["provider_debug"] = provider_debug
        return out

    # STRICT means: do NOT fall back to mock
    if strict_live:
        err = {
            "code": "SEARCH_NO_RESULTS",
            "message": f"No results parsed from providers. tried={providers_tried}",
            "providers_tried": providers_tried,
        }
        if debug:
            err["provider_debug"] = provider_debug
        return {"error": err}

    mock = _mock_results(query, top_k=top_k)
    out = {
        "query": query,
        "provider": "mock-search",
        "providers_tried": providers_tried + ["mock-search"],
        "result_count": len(mock),
        "results": mock,
        "degraded": True,
        "note": f"Live net.search unavailable (providers blocked/empty). FELL BACK to mock. tried={providers_tried}",
    }
    if debug:
        out["provider_debug"] = provider_debug + [{"provider": "mock-search", "ok": True, "reason": None, "result_count": len(mock)}]
    return out


# ---------------------------------------------------------
# ToolSpec registration
# ---------------------------------------------------------

NET_SEARCH_T = ToolSpec(
    name="net.search",
    description="Read-only network search (safe, bounded, offline-compatible; live optional with fallback).",
    required_role="OWNER",
    allowed_roles=("OWNER",),
    state_changing=False,
    external_effect=True,
    public=False,
    max_calls_per_minute=60,
    input_schema={
        "query": {"type": "string", "required": True, "description": "Search query"},
        "top_k": {"type": "integer", "required": False, "description": "Number of results (1–10)"},
        "min_results": {"type": "integer", "required": False, "description": "Try providers until at least this many raw results are collected (1–top_k)"},
        "preferred_provider": {"type": "string", "required": False, "description": "Optional preferred provider: brave-search | duckduckgo-html | duckduckgo-lite | wikipedia-opensearch"},
        "live": {"type": "boolean", "required": False, "description": "Enable live search (default env or False)"},
        "timeout_s": {"type": "integer", "required": False, "description": "Timeout seconds (2–20)"},
        "strict": {"type": "boolean", "required": False, "description": "Strict live: no mock fallback"},
        "debug": {"type": "boolean", "required": False, "description": "Include provider_debug diagnostics"},
    },
    handler=net_search_handler,
)


def register_net_tools(registry: Any) -> None:
    registry.register(NET_SEARCH_T)
