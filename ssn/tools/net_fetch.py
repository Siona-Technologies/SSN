# ssn/tools/net_fetch.py
"""
Network fetch tool — Phase 7.3 (Hardened)

READ-ONLY
SAFE
OFFLINE-COMPATIBLE

Purpose:
- Fetch bounded web content (text/html/json/xml), SSRF-protected, redirect-validated.
- Offline mode returns deterministic simulated content (for stable tests).

Access:
- OWNER: allowed
- GUEST: allowed ONLY when context.allow_tools=True AND context.allow_research=True
  (defense-in-depth; FrontDoor/Policy should also gate)

Offline rules:
- SSN_OFFLINE=1 OR args.offline=True OR deps.offline=True -> simulated deterministic content
- mock-search URLs (example.com) -> simulated deterministic content
"""

from __future__ import annotations

import ipaddress
import os
import socket
import time
import zlib
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, unquote_plus, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ssn.tools.contracts import ToolSpec


# ---------------------------------------------------------
# Allowlists / bounds
# ---------------------------------------------------------

_ALLOWED_CT_PREFIXES = (
    "text/",
    "application/json",
    "application/xml",
    "text/xml",
    "application/xhtml+xml",
)

_ALLOWED_CONTENT_ENCODINGS = ("", "identity", "gzip", "x-gzip", "deflate")

_HARD_MAX_BYTES = 200_000
_HARD_COMPRESSED_CAP = 600_000
_HARD_DECOMPRESS_SLACK = 16_384


# ---------------------------------------------------------
# Small utils
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


def _truncate_bytes(data: bytes, max_bytes: int) -> Tuple[bytes, bool]:
    if len(data) <= max_bytes:
        return data, False
    return data[:max_bytes], True


def _extract_ctx(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    for k in ("context", "ctx", "frontdoor_context", "request_context"):
        v = deps.get(k)
        if isinstance(v, dict):
            return v
    v2 = args.get("context")
    if isinstance(v2, dict):
        return v2
    return {}


def _guest_allowed(deps: Dict[str, Any], args: Dict[str, Any], role: str) -> bool:
    r = (role or "").strip().upper()
    if r == "OWNER":
        return True
    if r != "GUEST":
        return False
    ctx = _extract_ctx(deps, args)
    allow_tools = _safe_bool(ctx.get("allow_tools"), default=False)
    allow_research = _safe_bool(ctx.get("allow_research"), default=False)
    return bool(allow_tools and allow_research)


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

        seen = set()
        out: list[str] = []
        for ip in ips:
            if ip not in seen:
                seen.add(ip)
                out.append(ip)
        return out
    except Exception:
        return []


def _validate_url_safe(url: str, *, resolve_dns: bool = True) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    SSRF-safe URL validation (fail-closed).

    resolve_dns=False is used for OFFLINE/mock paths (no network fetch performed).
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

    if p.username or p.password:
        return False, {"code": "UNSAFE_URL", "message": "Credentials in URL are not allowed"}

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

    if not resolve_dns:
        return True, None

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
    c = ct.strip().lower()
    if not c:
        return False
    return any(c.startswith(p) for p in _ALLOWED_CT_PREFIXES)


def _gzip_magic(raw: bytes) -> bool:
    return isinstance(raw, (bytes, bytearray)) and len(raw) >= 2 and raw[0] == 0x1F and raw[1] == 0x8B


def _zlib_magic(raw: bytes) -> bool:
    return (
        isinstance(raw, (bytes, bytearray))
        and len(raw) >= 2
        and raw[0] == 0x78
        and raw[1] in (0x01, 0x9C, 0xDA)
    )


def _safe_decompress_gzip(raw: bytes, *, max_out: int) -> bytes:
    dobj = zlib.decompressobj(16 + zlib.MAX_WBITS)
    out = bytearray()
    chunk_size = 32_768
    for i in range(0, len(raw), chunk_size):
        piece = raw[i : i + chunk_size]
        out.extend(dobj.decompress(piece, max_out - len(out) + _HARD_DECOMPRESS_SLACK))
        if len(out) >= max_out:
            break
    if len(out) < max_out:
        out.extend(dobj.flush(max_out - len(out) + _HARD_DECOMPRESS_SLACK))
    return bytes(out[:max_out])


def _safe_decompress_deflate(raw: bytes, *, max_out: int) -> Tuple[bytes, str]:
    def _stream(wbits: int) -> bytes:
        dobj = zlib.decompressobj(wbits)
        out = bytearray()
        chunk_size = 32_768
        for i in range(0, len(raw), chunk_size):
            piece = raw[i : i + chunk_size]
            out.extend(dobj.decompress(piece, max_out - len(out) + _HARD_DECOMPRESS_SLACK))
            if len(out) >= max_out:
                break
        if len(out) < max_out:
            out.extend(dobj.flush(max_out - len(out) + _HARD_DECOMPRESS_SLACK))
        return bytes(out[:max_out])

    try:
        return _stream(zlib.MAX_WBITS), "deflate(zlib)"
    except Exception:
        return _stream(-zlib.MAX_WBITS), "deflate(raw)"


def _decode_content_encoding(raw: bytes, content_encoding: str, *, max_out: int) -> Tuple[bytes, str]:
    enc = (content_encoding or "").strip().lower()

    if enc in ("", "identity"):
        return raw[:max_out], "identity"

    if enc in ("gzip", "x-gzip"):
        return _safe_decompress_gzip(raw, max_out=max_out), "gzip"

    if enc == "deflate":
        data, which = _safe_decompress_deflate(raw, max_out=max_out)
        return data, which

    raise ValueError(f"Unsupported content-encoding: {enc}")


def _looks_like_binary(text: str) -> bool:
    if not isinstance(text, str) or not text:
        return False

    rep = text.count("\ufffd")
    if rep > max(8, len(text) // 40):  # >2.5%
        return True

    bad_ctrl = 0
    for ch in text:
        o = ord(ch)
        if o < 32 and ch not in ("\n", "\t", "\r"):
            bad_ctrl += 1
    if bad_ctrl > max(10, len(text) // 80):  # >1.25%
        return True

    return False


def _offline_requested(deps: Dict[str, Any], args: Dict[str, Any]) -> bool:
    if os.getenv("SSN_OFFLINE") == "1":
        return True
    if isinstance(args, dict) and _safe_bool(args.get("offline", False), default=False):
        return True
    if isinstance(deps, dict) and _safe_bool(deps.get("offline", False), default=False):
        return True
    return False


def _is_mock_url(url: str) -> bool:
    try:
        p = urlparse(url)
        host = (p.hostname or "").lower().strip()
        return host == "example.com"
    except Exception:
        return False


def _simulated_content_for(url: str) -> str:
    q = ""
    try:
        p = urlparse(url)
        qs = parse_qs(p.query or "")
        if "q" in qs and qs["q"]:
            q = unquote_plus(str(qs["q"][0] or "")).strip()
        if not q and "q=" in (p.query or ""):
            q = unquote_plus((p.query.split("q=", 1)[1] or "").split("&", 1)[0]).strip()
    except Exception:
        q = ""

    topic = (q or "offline mock document").strip().lower()

    if "speed of light" in topic or topic == "speed of light":
        return (
            "Speed of light (c): In vacuum, the speed of light is exactly 299,792,458 metres per second (m/s). "
            "This value is fixed by definition in the International System of Units, where the metre is defined "
            "as the distance light travels in vacuum during 1/299,792,458 of a second."
        )

    return (
        "This is simulated fetched content for offline testing.\n"
        f"URL: {url}\n"
        f"Topic: {q or 'N/A'}\n"
        "The purpose of this document is to provide stable, deterministic text so that the "
        "net.sanitize -> net.cite -> research.answer pipeline can be exercised without live network access."
    )


class _SSRFRedirectBlocked(Exception):
    pass


class _SafeRedirectHandler(HTTPRedirectHandler):
    """
    Validate every redirect target BEFORE following it.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            target = urljoin(req.full_url, newurl)
        except Exception:
            target = newurl

        ok, err = _validate_url_safe(target, resolve_dns=True)
        if not ok:
            raise _SSRFRedirectBlocked(f"{err}")

        return super().redirect_request(req, fp, code, msg, headers, target)


# ---------------------------------------------------------
# net.fetch handler
# ---------------------------------------------------------

def net_fetch_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    url = args.get("url")
    if not isinstance(url, str) or not url.strip():
        return {"error": {"code": "INVALID_URL", "message": "Missing or invalid 'url'"}}
    url = url.strip()

    role = str(deps.get("role") or "GUEST").strip().upper()
    if not _guest_allowed(deps, args, role):
        return {
            "error": {
                "code": "NOT_AUTHORIZED",
                "message": "net.fetch requires OWNER, or (GUEST with context.allow_tools=true AND context.allow_research=true).",
            }
        }

    max_bytes = _safe_int(args.get("max_bytes"), 50_000)
    max_bytes = max(1_000, min(max_bytes, _HARD_MAX_BYTES))

    timeout_s = float(_safe_int(args.get("timeout_s"), 10))
    timeout_s = max(2.0, min(timeout_s, 20.0))

    offline_or_mock = _offline_requested(deps, args) or _is_mock_url(url)

    ok, err = _validate_url_safe(url, resolve_dns=(not offline_or_mock))
    if not ok:
        return {"error": err}

    # OFFLINE or MOCK deterministic path
    if offline_or_mock:
        simulated = _simulated_content_for(url)
        data = simulated.encode("utf-8", errors="replace")
        data, truncated = _truncate_bytes(data, max_bytes)
        text = _decode_text(data, "utf-8")
        return {
            "url": url,
            "final_url": url,
            "status": 200,
            "content_type": "text/plain",
            "raw_content_type": "text/plain; charset=utf-8",
            "content_encoding": "identity",
            "decoded_from": "identity",
            "content_bytes": len(data),
            "content": text,
            "fetched_at": 0.0,
            "truncated": bool(truncated),
            "degraded": True,
            "note": "Simulated net.fetch (offline/mock URL; bounded, deterministic; DNS skipped offline).",
        }

    req = Request(
        url,
        headers={
            "User-Agent": "SIONA/1.0 (SSN research; safe fetch)",
            "Accept": "text/html,text/plain,application/xhtml+xml,application/json,application/xml,text/xml;q=0.9,*/*;q=0.1",
            "Accept-Encoding": "gzip, deflate, identity",
        },
        method="GET",
    )

    opener = build_opener(_SafeRedirectHandler())

    final_url = url
    status = 0
    raw_ct = "application/octet-stream"
    ct = "application/octet-stream"
    ce = "identity"
    decoded_from = "identity"
    decoded_bytes: bytes = b""
    truncated = False

    try:
        with opener.open(req, timeout=timeout_s) as resp:
            status = int(getattr(resp, "status", 200) or 200)
            final_url = str(getattr(resp, "geturl", lambda: url)() or url)

            ok2, _err2 = _validate_url_safe(final_url, resolve_dns=True)
            if not ok2:
                return {"error": {"code": "SSRF_BLOCKED", "message": f"Redirected to unsafe URL: {final_url}"}}

            raw_ct = resp.headers.get("Content-Type") or "application/octet-stream"
            ct = raw_ct.split(";", 1)[0].strip().lower() if isinstance(raw_ct, str) else "application/octet-stream"
            if not ct:
                ct = "application/octet-stream"

            if not _is_allowed_content_type(ct):
                return {"error": {"code": "CONTENT_TYPE_NOT_ALLOWED", "message": f"Blocked content_type={ct}"}}

            raw_ce = resp.headers.get("Content-Encoding") or ""
            ce = (raw_ce or "").strip().lower()

            if ce not in _ALLOWED_CONTENT_ENCODINGS:
                return {
                    "error": {
                        "code": "CONTENT_ENCODING_NOT_ALLOWED",
                        "message": f"Blocked content_encoding={ce or '(empty)'}",
                    }
                }

            compressed_cap = min(_HARD_COMPRESSED_CAP, max(max_bytes * 3, 50_000))
            raw = resp.read(compressed_cap + 1)
            raw, raw_truncated = _truncate_bytes(raw, compressed_cap)

            decoded_bytes, decoded_from = _decode_content_encoding(raw, ce, max_out=max_bytes)

            # sniff-only fallback if server lied about encoding
            if decoded_from == "identity":
                if _gzip_magic(raw):
                    decoded_bytes = _safe_decompress_gzip(raw, max_out=max_bytes)
                    decoded_from = "gzip(sniff)"
                elif _zlib_magic(raw):
                    decoded_bytes, which = _safe_decompress_deflate(raw, max_out=max_bytes)
                    decoded_from = f"{which}(sniff)"

            truncated = bool(raw_truncated) or (len(decoded_bytes) >= max_bytes)

    except _SSRFRedirectBlocked as e:
        return {"error": {"code": "SSRF_BLOCKED", "message": f"Redirect blocked: {e}"}}
    except HTTPError as e:
        code = getattr(e, "code", None)
        return {"error": {"code": "HTTP_ERROR", "message": f"HTTP error: {code if code is not None else 'unknown'}"}}
    except URLError as e:
        return {"error": {"code": "FETCH_FAILED", "message": f"Network error: {getattr(e, 'reason', str(e))}"}}
    except Exception as e:
        return {"error": {"code": "FETCH_FAILED", "message": f"Fetch failed: {e}"}}

    text = _decode_text(decoded_bytes, _infer_charset(raw_ct))

    if _looks_like_binary(text):
        return {
            "error": {
                "code": "BINARY_JUNK_DETECTED",
                "message": "Decoded content looks like binary/junk (high replacement/control density).",
            }
        }

    return {
        "url": url,
        "final_url": final_url,
        "status": status,
        "content_type": ct,
        "raw_content_type": raw_ct,
        "content_encoding": ce or "identity",
        "decoded_from": decoded_from,
        "content_bytes": len(decoded_bytes),
        "content": text,
        "fetched_at": time.time(),
        "truncated": bool(truncated),
        "degraded": False,
        "note": (
            "Live net.fetch (urllib, SSRF-protected, bounded, redirect-validated, "
            "content-type allowlist, safe streaming decode + sniff fallback)."
        ),
    }


# ---------------------------------------------------------
# ToolSpec
# ---------------------------------------------------------

NET_FETCH_T = ToolSpec(
    name="net.fetch",
    description="Read-only content fetch (bounded, SSRF-protected, offline-capable; allowlisted content-types).",
    required_role="GUEST",
    allowed_roles=("OWNER", "GUEST"),
    state_changing=False,
    external_effect=True,
    public=False,
    max_calls_per_minute=120,
    input_schema={
        "url": {"type": "string", "required": True, "description": "URL to fetch content from (http/https only)"},
        "max_bytes": {"type": "integer", "required": False, "description": "Maximum decoded bytes to read (1k–200k)"},
        "timeout_s": {"type": "integer", "required": False, "description": "Timeout seconds (2–20)"},
        "offline": {"type": "boolean", "required": False, "description": "Force deterministic offline simulation (tests)"},
        "context": {"type": "object", "required": False, "description": "Optional context passthrough (allow_tools/allow_research)"},
    },
    handler=net_fetch_handler,
)


def register_net_fetch_tools(registry: Any) -> None:
    registry.register(NET_FETCH_T)
