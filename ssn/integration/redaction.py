"""
Sensitive-data redaction for cognitive event payloads.

Never include master keys, credentials, or raw auth headers in events/logs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

_SECRET_KEYS_EXACT: Set[str] = {
    "master_key",
    "ssn_master_key",
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "bearer",
    "secret",
    "password",
    "passwd",
    "private_key",
    "privatekey",
    "client_secret",
}
_SECRET_PREFIXES = (
    "auth",
    "bearer",
    "token",
    "secret",
    "password",
    "private",
    "access_",
    "refresh_",
    "api_key",
)

MAX_STR = 500
MAX_LIST = 32
MAX_DICT_KEYS = 48
MAX_DEPTH = 6


def _is_secret_key(name: str) -> bool:
    k = (name or "").strip().lower()
    if not k:
        return False
    if k in _SECRET_KEYS_EXACT:
        return True
    return any(k.startswith(p) for p in _SECRET_PREFIXES)


def redact(value: Any, *, depth: int = 0) -> Any:
    if depth > MAX_DEPTH:
        return "<truncated_depth>"
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for i, (k, v) in enumerate(value.items()):
            if i >= MAX_DICT_KEYS:
                out["__truncated__"] = True
                break
            key = str(k)
            if _is_secret_key(key):
                out[key] = "<redacted>"
            else:
                out[key] = redact(v, depth=depth + 1)
        return out
    if isinstance(value, list):
        return [redact(v, depth=depth + 1) for v in value[:MAX_LIST]]
    if isinstance(value, str):
        return value if len(value) <= MAX_STR else (value[: MAX_STR - 3] + "...")
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:MAX_STR]


def bounded_summary(text: str, *, max_chars: int = 120) -> Dict[str, Any]:
    t = text or ""
    return {
        "length": len(t),
        "preview": t[:max_chars],
        "hash8": _stable_hash8(t),
    }


def _stable_hash8(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:8]
