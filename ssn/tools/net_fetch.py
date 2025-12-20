# ssn/tools/net_fetch.py

from __future__ import annotations

import base64
import ipaddress
import os
import socket
import time
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ssn.tools.contracts import ToolSpec


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

_ALLOWED_CT_PREFIXES = (
    "text/",
    "application/json",
    "application/xml",
    "text/xml",
)


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _truncate_bytes(data: bytes, max_bytes: int) -> Tuple[bytes, bool]:
    if len(data) <= max_bytes:
        return data, False
    return data[:max_bytes], True


def _is_private_or_local_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_multicast
            or addr.is_reserved
            or addr.is_unspecified
        )
    except Exception:
        return True  # fail-closed


def _resolve_host_ips(hostname: str, port: Optional[int]) -> list[str]:
    try:
        infos = socket.getaddrinfo(hostname, port or 443, type=socket.SOCK_STREAM)
        ips: list[str] = []
        for fam, _, _, _, sockaddr in infos:
            if fam in (socket.AF_INET, socket.AF_INET6):
                ips.append(sockaddr[0])

        # de-dupe while preserving order
        seen = set()
        out: list[str] = []
        for ip in ips:
            if ip not in seen:
                seen.add(ip)
                out.append(ip)
        return out
    except Exception:
        return []


def _validate_url_safe(url: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    SSRF-safe URL validation (fail-closed).

    Blocks:
    - non-http(s) schemes
    - localhost / .local
    - cloud metadata IP
    - private/link-local/reserved IPs (including resolved DNS targets)
    """
    try:
        p = urlparse(url)
    except Exception:
        return False, {"code": "INVALID_URL", "message": "URL parsing failed"}

    scheme = (p.scheme or "").lower()
    if scheme not in ("http", "https"):
        return False, {"code": "UNSAFE_URL", "message": "Only http/https URLs are allowed"}

    if not p.netloc:
        return False, {"code": "INVALID_URL", "message": "URL missing host"}

    host = (p.hostname or "").strip()
    if not host:
        return False, {"code": "INVALID_URL", "message": "URL missing hostname"}

    host_l = host.lower()
    if host_l == "localhost":
        return False, {"code": "SSRF_BLOCKED", "message": "localhost is blocked"}
    if host_l.endswith(".local"):
        return False, {"code": "SSRF_BLOCKED", "message": "*.local hostnames are blocked"}

    # IP literal
    try:
        ipaddress.ip_address(host)
        if host == "169.254.169.254":
            return False, {"code": "SSRF_BLOCKED", "message": "Cloud metadata IP is blocked"}
        if _is_private_or_local_ip(host):
            return False, {"code": "SSRF_BLOCKED", "message": "Private/local IPs are blocked"}
        return True, None
    except Exception:
        pass

    # DNS resolve
    ips = _resolve_host_ips(host, p.port)
    if not ips:
        return False, {"code": "DNS_FAILED", "message": "Hostname could not be resolved (blocked)"}

    for ip in ips:
        if ip == "169.254.169.254":
            return False, {"code": "SSRF_BLOCKED", "message": "Resolved to cloud metadata IP (blocked)"}
        if _is_private_or_local_ip(ip):
            return False, {"code": "SSRF_BLOCKED", "message": f"Resolved to blocked IP: {ip}"}

    return True, None


def _infer_charset(content_type: str) -> Optional[str]:
    if not isinstance(content_type, str):
        return None
    parts = [p.strip() for p in content_type.split(";")]
    for p in parts[1:]:
        if p.lower().startswith("charset="):
            return p.split("=", 1)[1].strip().strip('"').strip("'") or None
    return None


def _decode_text(data: bytes, charset: Optional[str]) -> str:
    if not data:
        return ""
    if charset:
        try:
            return data.decode(charset, errors="replace")
        except Exception:
            pass
    return data.decode("utf-8", errors="replace")


def _is_allowed_content_type(ct: str) -> bool:
    if not isinstance(ct, str):
        return False
    ct = ct.strip().lower()
    if not ct:
        return False
    for p in _ALLOWED_CT_PREFIXES:
        if ct.startswith(p):
            return True
    return False


# ---------------------------------------------------------
# net.fetch handler
# ---------------------------------------------------------

def net_fetch_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    net.fetch (Phase 7.2)

    READ-ONLY content fetch tool.

    Rules:
    - http/https only
    - SSRF protection (block localhost/private/reserved targets)
    - bounded max_bytes (hard capped)
    - strict timeout
    - content-type allowlist (default text/*, json, xml)
    - no JS execution
    - no file writes
    - no memory writes

    Offline:
    - If SSN_OFFLINE=1, return deterministic simulated text content (still SSRF-validates the URL).
    """

    url = args.get("url")
    if not isinstance(url, str) or not url.strip():
        return {"error": {"code": "INVALID_URL", "message": "Missing or invalid 'url'"}}
    url = url.strip()

    max_bytes = _safe_int(args.get("max_bytes"), 50_000)
    max_bytes = max(1_000, min(max_bytes, 200_000))

    timeout_s = float(_safe_int(args.get("timeout_s"), 10))
    timeout_s = max(2.0, min(timeout_s, 20.0))

    ok, err = _validate_url_safe(url)
    if not ok:
        return {"error": err}

    # OFFLINE deterministic path
    if os.getenv("SSN_OFFLINE") == "1":
        simulated = (
            "This is simulated fetched content.\n"
            "It represents the body of a web page or document.\n"
            "Used for pipeline testing before real network fetch.\n"
        )
        data = simulated.encode("utf-8", errors="replace")
        data, truncated = _truncate_bytes(data, max_bytes)
        text = _decode_text(data, "utf-8")
        return {
            "url": url,
            "final_url": url,
            "status": 200,
            "content_type": "text/plain",
            "raw_content_type": "text/plain; charset=utf-8",
            "content_bytes": len(data),
            "content": text,
            "fetched_at": time.time(),
            "truncated": bool(truncated),
            "degraded": True,
            "note": "Simulated net.fetch (SSN_OFFLINE=1, SSRF-validated, bounded)",
        }

    req = Request(
        url,
        headers={
            "User-Agent": "SIONA/1.0 (SSN research; safe fetch)",
            "Accept": "text/html,text/plain,application/json,application/xml,text/xml;q=0.9,*/*;q=0.1",
        },
        method="GET",
    )

    try:
        with urlopen(req, timeout=timeout_s) as resp:
            status = int(getattr(resp, "status", 200) or 200)
            final_url = str(getattr(resp, "geturl", lambda: url)() or url)

            # Re-validate the FINAL URL (redirect SSRF defense)
            ok2, err2 = _validate_url_safe(final_url)
            if not ok2:
                return {"error": {"code": "SSRF_BLOCKED", "message": f"Redirected to unsafe URL: {final_url}"}}

            raw_ct = resp.headers.get("Content-Type") or "application/octet-stream"
            ct = raw_ct.split(";", 1)[0].strip().lower() if isinstance(raw_ct, str) else "application/octet-stream"
            if not ct:
                ct = "application/octet-stream"

            # Hard block non-allowlisted content types
            if not _is_allowed_content_type(ct):
                return {
                    "error": {
                        "code": "CONTENT_TYPE_NOT_ALLOWED",
                        "message": f"Blocked content_type={ct}",
                    }
                }

            charset = _infer_charset(raw_ct)
            data = resp.read(max_bytes + 1)
            data, truncated = _truncate_bytes(data, max_bytes)

    except HTTPError as e:
        code = getattr(e, "code", None)
        return {"error": {"code": "HTTP_ERROR", "message": f"HTTP error: {code if code is not None else 'unknown'}"}}
    except URLError as e:
        return {"error": {"code": "FETCH_FAILED", "message": f"Network error: {getattr(e, 'reason', str(e))}"}}
    except Exception as e:
        return {"error": {"code": "FETCH_FAILED", "message": f"Fetch failed: {e}"}}

    text = _decode_text(data, charset)

    return {
        "url": url,
        "final_url": final_url,
        "status": status,
        "content_type": ct,
        "raw_content_type": raw_ct,
        "content_bytes": len(data),
        "content": text,
        "fetched_at": time.time(),
        "truncated": bool(truncated),
        "note": "Live net.fetch (urllib, SSRF-protected, bounded, content-type allowlist)",
    }


# ---------------------------------------------------------
# ToolSpec
# ---------------------------------------------------------

NET_FETCH_T = ToolSpec(
    name="net.fetch",
    description="Read-only content fetch (bounded, SSRF-protected, offline-capable; allowlisted content-types).",
    required_role="OWNER",
    allowed_roles=("OWNER",),
    state_changing=False,
    external_effect=True,
    public=False,
    max_calls_per_minute=120,
    input_schema={
        "url": {"type": "string", "required": True, "description": "URL to fetch content from (http/https only)"},
        "max_bytes": {"type": "integer", "required": False, "description": "Maximum bytes to read (1k–200k hard cap)"},
        "timeout_s": {"type": "integer", "required": False, "description": "Timeout seconds (2–20)"},
    },
    handler=net_fetch_handler,
)


def register_net_fetch_tools(registry: Any) -> None:
    """
    Optional helper if you want to register net.fetch explicitly.
    (If you already register it elsewhere, you can ignore this.)
    """
    registry.register(NET_FETCH_T)
