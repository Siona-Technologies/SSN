"""
Network tools — Phase 7.2.1+ (Production-resilient)

READ-ONLY
SAFE
OFFLINE-COMPATIBLE

Behavior:
- Default: offline-safe deterministic mock (keeps tests stable)
- Live mode (optional): multi-provider search with bounded HTTP and fallback:
    0) Brave Search API (reliable; requires SSN_BRAVE_API_KEY)
    1) DuckDuckGo HTML (scrape)
    2) DuckDuckGo Lite (scrape)
    3) Wikipedia OpenSearch API (reliable, no key)
    4) Mock fallback (unless strict live is enabled)

Enable live search:
- args {"live": True} OR env SSN_LIVE_SEARCH=1

Force offline:
- env SSN_OFFLINE=1  (always mock)

Strict live (no fallback to mock):
- args {"strict": True} OR env SSN_LIVE_STRICT=1

Brave Search API:
- env SSN_BRAVE_API_KEY=<token>
- optional: SSN_BRAVE_COUNTRY=KE / US / GB ...
- optional: SSN_BRAVE_LANG=en / en-US / sw ...

IMPORTANT:
- If args explicitly set live/strict, args override env.
"""

from __future__ import annotations

import html as _html
import json
import os
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

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


def _sanitize_text(text: str, *, max_len: int = 500) -> str:
    if not isinstance(text, str):
        return ""
    text = text.replace("\n", " ").replace("\r", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:max_len]


_RE_TAGS = re.compile(r"<[^>]+>", re.IGNORECASE)


def _strip_tags(s: str) -> str:
    return _RE_TAGS.sub(" ", s)


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
    """
    Heuristic block/captcha detection (for scraped providers).
    """
    if not isinstance(html_text, str) or not html_text:
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
    )
    return any(n in lowered for n in needles)


def _http_get_text(url: str, *, timeout_s: float, max_bytes: int, headers: Dict[str, str]) -> str:
    req = Request(url, headers=headers, method="GET")
    with urlopen(req, timeout=timeout_s) as resp:
        data = resp.read(max_bytes + 1)
        data = data[:max_bytes]
        return data.decode("utf-8", errors="replace")


def _clip_query(q: str, max_len: int = 240) -> str:
    q = (q or "").strip()
    q = re.sub(r"\s+", " ", q)
    return q[:max_len]


def _wiki_normalize_query(q: str) -> str:
    """
    Wikipedia OpenSearch is not a full boolean search engine.
    Remove quotes and '-' excludes; keep it short and simple.
    """
    q = (q or "").strip()
    # remove minus terms like -word or -"two words"
    q = re.sub(r'-"[^"]+"', " ", q)
    q = re.sub(r"-\S+", " ", q)
    # remove quotes
    q = q.replace('"', " ")
    q = re.sub(r"\s+", " ", q).strip()
    return _clip_query(q, 120)


def _env_str(name: str) -> Optional[str]:
    v = os.getenv(name)
    if isinstance(v, str):
        v = v.strip()
        if v:
            return v
    return None


# ---------------------------------------------------------
# Provider 0: Brave Search API (reliable; requires key)
# ---------------------------------------------------------

def _brave_search(query: str, *, top_k: int, timeout_s: float) -> List[Dict[str, Any]]:
    """
    Brave Search API:
      GET https://api.search.brave.com/res/v1/web/search?q=...

    Requires:
      SSN_BRAVE_API_KEY

    Optional:
      SSN_BRAVE_COUNTRY (e.g., "KE", "US")
      SSN_BRAVE_LANG (e.g., "en", "en-US", "sw")
    """
    key = _env_str("SSN_BRAVE_API_KEY")
    if not key:
        return []

    q = quote_plus(_clip_query(query, 240))
    country = _env_str("SSN_BRAVE_COUNTRY")
    lang = _env_str("SSN_BRAVE_LANG")

    url = f"https://api.search.brave.com/res/v1/web/search?q={q}&count={min(top_k, 10)}"
    if country:
        url += f"&country={quote_plus(country)}"
    if lang:
        url += f"&search_lang={quote_plus(lang)}"

    text = _http_get_text(
        url,
        timeout_s=timeout_s,
        max_bytes=220_000,
        headers={
            "User-Agent": "SIONA/1.0 (SSN research; safe search)",
            "Accept": "application/json",
            "X-Subscription-Token": key,
        },
    )

    try:
        data = json.loads(text)
    except Exception:
        return []

    web = data.get("web") if isinstance(data, dict) else None
    results = (web.get("results") if isinstance(web, dict) else None) or []
    if not isinstance(results, list) or not results:
        return []

    out: List[Dict[str, Any]] = []
    for r in results[:top_k]:
        if not isinstance(r, dict):
            continue
        title = _sanitize_text(str(r.get("title", "") or ""), max_len=140)
        urlv = str(r.get("url", "") or "").strip()
        desc = r.get("description") or r.get("snippet") or r.get("meta_description") or ""
        snippet = _sanitize_text(str(desc or ""), max_len=300)
        if not urlv:
            continue
        out.append(
            {
                "title": title,
                "url": urlv,
                "snippet": snippet,
                "source": "brave-search",
                "retrieved_at": time.time(),
            }
        )

    return out


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
    q = quote_plus(_clip_query(query, 240))
    url = f"https://duckduckgo.com/html/?q={q}"

    html_text = _http_get_text(
        url,
        timeout_s=timeout_s,
        max_bytes=220_000,
        headers={
            "User-Agent": "SIONA/1.0 (SSN research; safe search)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )

    if _looks_like_block_page(html_text):
        return []

    anchors = _RE_RESULT_A.findall(html_text)
    if not anchors:
        return []

    snippet_matches = _RE_SNIPPET.findall(html_text)
    snippets: List[str] = []
    for a, b in snippet_matches:
        raw = a or b or ""
        raw = _strip_tags(raw)
        raw = _html.unescape(raw)
        snippets.append(_sanitize_text(raw, max_len=300))

    out: List[Dict[str, Any]] = []
    for i, (href, title_html) in enumerate(anchors[:top_k]):
        title = _sanitize_text(_html.unescape(_strip_tags(title_html)), max_len=140)
        u = _decode_ddg_redirect(_html.unescape(href.strip()))
        snippet = snippets[i] if i < len(snippets) else ""
        out.append(
            {
                "title": title,
                "url": u,
                "snippet": snippet,
                "source": "duckduckgo-html",
                "retrieved_at": time.time(),
            }
        )
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
    q = quote_plus(_clip_query(query, 240))
    url = f"https://lite.duckduckgo.com/lite/?q={q}"

    html_text = _http_get_text(
        url,
        timeout_s=timeout_s,
        max_bytes=220_000,
        headers={
            "User-Agent": "SIONA/1.0 (SSN research; safe search)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )

    if _looks_like_block_page(html_text):
        return []

    links = _RE_LITE_LINK.findall(html_text)
    if not links:
        return []

    snippets_raw = _RE_LITE_SNIPPET.findall(html_text)
    snippets: List[str] = []
    for s in snippets_raw:
        snippets.append(_sanitize_text(_html.unescape(_strip_tags(s)), max_len=300))

    out: List[Dict[str, Any]] = []
    for i, (href, title_html) in enumerate(links[:top_k]):
        title = _sanitize_text(_html.unescape(_strip_tags(title_html)), max_len=140)
        u = _decode_ddg_redirect(_html.unescape(href.strip()))
        snippet = snippets[i] if i < len(snippets) else ""
        out.append(
            {
                "title": title,
                "url": u,
                "snippet": snippet,
                "source": "duckduckgo-lite",
                "retrieved_at": time.time(),
            }
        )
    return out


# ---------------------------------------------------------
# Provider 3: Wikipedia OpenSearch (reliable, no key)
# ---------------------------------------------------------

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
            "User-Agent": "SIONA/1.0 (SSN research; safe search)",
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
        title = _sanitize_text(str(titles[i]), max_len=140)
        snippet = _sanitize_text(str(descs[i]) if i < len(descs) else "", max_len=300)
        out.append(
            {
                "title": title,
                "url": str(urls[i]),
                "snippet": snippet,
                "source": "wikipedia-opensearch",
                "retrieved_at": time.time(),
            }
        )
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

    top_k = _safe_int(args.get("top_k"), 5)
    top_k = max(1, min(top_k, 10))

    forced_offline = os.getenv("SSN_OFFLINE") == "1"

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
        return {
            "query": query,
            "provider": "mock-search",
            "providers_tried": ["mock-search"],
            "result_count": len(results),
            "results": results,
            "note": "Simulated net.search (offline-safe; set live=True or SSN_LIVE_SEARCH=1 for real search)",
        }

    providers_tried: List[str] = []

    def _try(fn, name: str) -> List[Dict[str, Any]]:
        providers_tried.append(name)
        try:
            return fn(query, top_k=top_k, timeout_s=timeout_s)
        except HTTPError:
            return []
        except URLError:
            return []
        except Exception:
            return []

    # Provider 0: Brave Search API (only works if SSN_BRAVE_API_KEY is set)
    if _env_str("SSN_BRAVE_API_KEY"):
        results = _try(_brave_search, "brave-search")
        if results:
            return {
                "query": query,
                "provider": "brave-search",
                "providers_tried": providers_tried,
                "result_count": len(results),
                "results": results,
                "note": "Live net.search (Brave Search API, bounded)",
            }
    else:
        providers_tried.append("brave-search (missing SSN_BRAVE_API_KEY)")

    results = _try(_ddg_html_search, "duckduckgo-html")
    if results:
        return {
            "query": query,
            "provider": "duckduckgo-html",
            "providers_tried": providers_tried,
            "result_count": len(results),
            "results": results,
            "note": "Live net.search (DuckDuckGo HTML, bounded)",
        }

    results = _try(_ddg_lite_search, "duckduckgo-lite")
    if results:
        return {
            "query": query,
            "provider": "duckduckgo-lite",
            "providers_tried": providers_tried,
            "result_count": len(results),
            "results": results,
            "note": "Live net.search (DuckDuckGo LITE fallback, bounded)",
        }

    results = _try(_wiki_opensearch, "wikipedia-opensearch")
    if results:
        return {
            "query": query,
            "provider": "wikipedia-opensearch",
            "providers_tried": providers_tried,
            "result_count": len(results),
            "results": results,
            "note": "Live net.search (Wikipedia OpenSearch fallback, bounded)",
        }

    if strict_live:
        return {
            "error": {
                "code": "SEARCH_NO_RESULTS",
                "message": f"No results parsed from providers. tried={providers_tried}",
            }
        }

    mock = _mock_results(query, top_k=top_k)
    return {
        "query": query,
        "provider": "mock-search",
        "providers_tried": providers_tried + ["mock-search"],
        "result_count": len(mock),
        "results": mock,
        "degraded": True,
        "note": f"Live net.search unavailable (providers blocked/empty). FELL BACK to mock. tried={providers_tried}",
    }


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
        "live": {"type": "boolean", "required": False, "description": "Enable live search (default env or False)"},
        "timeout_s": {"type": "integer", "required": False, "description": "Timeout seconds (2–20)"},
        "strict": {"type": "boolean", "required": False, "description": "Strict live: fail if live providers blocked/empty"},
    },
    handler=net_search_handler,
)


def register_net_tools(registry: Any) -> None:
    """
    builtin_tools.py expects this symbol.

    Register all network tools into the given ToolRegistry.
    """
    registry.register(NET_SEARCH_T)
