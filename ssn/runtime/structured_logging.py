"""
Structured JSON logging for production deployments (Phase 6).

Emits one JSON object per line to stdout for log aggregation (systemd/journald,
CloudWatch, etc.). Secrets are scrubbed before emit.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, Iterable, Optional

_SECRET_KEYS_EXACT = {
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
    "api_key",
    "access_",
    "refresh_",
)


def structured_logging_enabled() -> bool:
    if os.getenv("SSN_STRUCTURED_LOG") == "1":
        return True
    if os.getenv("SSN_HTTP_STRUCTURED_LOG") == "1":
        return True
    return False


def _key_is_secret(key: str) -> bool:
    k = (key or "").lower().strip()
    if k in _SECRET_KEYS_EXACT:
        return True
    return any(k.startswith(p) for p in _SECRET_PREFIXES)


def scrub_value(obj: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "<depth_limit>"
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if _key_is_secret(str(k)):
                out[str(k)] = "<redacted>"
            else:
                out[str(k)] = scrub_value(v, depth=depth + 1)
        return out
    if isinstance(obj, list):
        return [scrub_value(x, depth=depth + 1) for x in obj[:50]]
    if isinstance(obj, tuple):
        return [scrub_value(x, depth=depth + 1) for x in obj[:50]]
    if isinstance(obj, str) and len(obj) > 4000:
        return obj[:4000] + "…"
    return obj


def emit_log(event: str, **fields: Any) -> None:
    if not structured_logging_enabled():
        return
    payload: Dict[str, Any] = {
        "ts": round(time.time(), 3),
        "event": event,
        "service": "siona",
    }
    payload.update(scrub_value(fields) if fields else {})
    line = json.dumps(payload, ensure_ascii=False, default=str)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def emit_http_access(
    *,
    method: str,
    path: str,
    status: int,
    duration_ms: float,
    tenant_id: Optional[str] = None,
    session_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    fields: Dict[str, Any] = {
        "method": method,
        "path": path,
        "status": int(status),
        "duration_ms": round(duration_ms, 3),
    }
    if tenant_id:
        fields["tenant_id"] = tenant_id
    if session_id:
        fields["session_id"] = session_id
    if extra:
        fields.update(extra)
    emit_log("http.access", **fields)


def emit_audit(
    *,
    action: str,
    ok: bool,
    role: Optional[str] = None,
    tenant_id: Optional[str] = None,
    session_id: Optional[str] = None,
    turn_id: Optional[int] = None,
    tool_name: Optional[str] = None,
    degraded: Optional[bool] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    fields: Dict[str, Any] = {
        "action": action,
        "ok": bool(ok),
    }
    if role:
        fields["role"] = role
    if tenant_id:
        fields["tenant_id"] = tenant_id
    if session_id:
        fields["session_id"] = session_id
    if turn_id is not None:
        fields["turn_id"] = turn_id
    if tool_name:
        fields["tool_name"] = tool_name
    if degraded is not None:
        fields["degraded"] = bool(degraded)
    if extra:
        fields.update(extra)
    emit_log("audit", **fields)
