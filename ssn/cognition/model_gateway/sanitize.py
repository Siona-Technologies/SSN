"""
Canonical provider-boundary sanitization for ModelRequest.

Scrubs secrets from every field that may be serialized to a model transport.
Never logs or echoes removed secret values.
"""

from __future__ import annotations

import math
import os
import re
from copy import deepcopy
from dataclasses import replace
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ssn.cognition.model_gateway.contracts import MessageRole, ModelMessage, ModelRequest

REDACTED = "<redacted>"
DEFAULT_MAX_PROMPT_CHARS = 32_768
MAX_TOOL_DEFS = 32
MAX_TOOL_DEF_BYTES = 8_192
MAX_MESSAGE_META_KEYS = 8
MAX_DEPTH = 6
MAX_DICT_KEYS = 48
MAX_LIST = 32
MAX_STR = 2_000

MESSAGE_META_ALLOWLIST = frozenset(
    {
        "name",
        "tool_call_id",
        "role_hint",
        "format",
        "locale",
    }
)

_SECRET_KEYS_EXACT = frozenset(
    {
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
        "session_token",
        "id_token",
    }
)

_SECRET_KEY_PREFIXES = (
    "auth",
    "bearer",
    "token",
    "secret",
    "password",
    "private",
    "access_",
    "refresh_",
    "api_key",
    "master_key",
)

# High-confidence inline patterns. Capture groups hold secret material only.
_INLINE_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bmaster_key\s*[:=]\s*([^\s\"',;]+)"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*([^\s\"',;]+)"),
    re.compile(r"(?i)\bpassword\s*[:=]\s*([^\s\"',;]+)"),
    re.compile(r"(?i)\baccess[_-]?token\s*[:=]\s*([^\s\"',;]+)"),
    re.compile(r"(?i)\brefresh[_-]?token\s*[:=]\s*([^\s\"',;]+)"),
    re.compile(r"(?i)\bauthorization\s*:\s*bearer\s+([^\s\"',;]+)"),
    re.compile(r"(?i)\bbearer\s+([A-Za-z0-9\-._~+/]+=*)"),
    re.compile(
        r"(?i)-----BEGIN[^-]*PRIVATE KEY-----.*?-----END[^-]*PRIVATE KEY-----",
        re.DOTALL,
    ),
)


class SanitizationError(RuntimeError):
    def __init__(self, message: str = "sanitization_failed") -> None:
        super().__init__(message)
        self.category = "security"


def _is_secret_key(name: str) -> bool:
    k = (name or "").strip().lower().replace("-", "_")
    if not k:
        return False
    if k in _SECRET_KEYS_EXACT:
        return True
    return any(k.startswith(p) for p in _SECRET_KEY_PREFIXES)


def _configured_secret_values() -> List[str]:
    values: List[str] = []
    for env_name in ("SSN_MASTER_KEY", "SSN_API_KEY", "SSN_LOCAL_MODEL_API_KEY"):
        raw = (os.getenv(env_name) or "").strip()
        if raw and len(raw) >= 4:
            values.append(raw)
    return values


def _redact_text(text: str, *, exact_secrets: Sequence[str]) -> str:
    if not isinstance(text, str):
        return REDACTED
    out = text
    for secret in exact_secrets:
        if secret and secret in out:
            out = out.replace(secret, REDACTED)
    for pattern in _INLINE_PATTERNS:
        if pattern.groups == 0:
            out = pattern.sub(REDACTED, out)
        else:
            out = pattern.sub(lambda m: m.group(0).replace(m.group(1), REDACTED), out)
    if len(out) > MAX_STR * 4:
        out = out[: MAX_STR * 4 - 3] + "..."
    return out


def _sanitize_value(value: Any, *, exact_secrets: Sequence[str], depth: int = 0) -> Any:
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
                out[key] = REDACTED
            else:
                out[key] = _sanitize_value(v, exact_secrets=exact_secrets, depth=depth + 1)
        return out
    if isinstance(value, list):
        return [
            _sanitize_value(v, exact_secrets=exact_secrets, depth=depth + 1)
            for v in value[:MAX_LIST]
        ]
    if isinstance(value, str):
        return _redact_text(value, exact_secrets=exact_secrets)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _redact_text(str(value), exact_secrets=exact_secrets)[:MAX_STR]


def _sanitize_message_metadata(
    meta: Dict[str, Any], *, exact_secrets: Sequence[str]
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for i, (k, v) in enumerate((meta or {}).items()):
        if i >= MAX_MESSAGE_META_KEYS:
            break
        key = str(k)
        if key not in MESSAGE_META_ALLOWLIST:
            continue
        if _is_secret_key(key):
            out[key] = REDACTED
        else:
            out[key] = _sanitize_value(v, exact_secrets=exact_secrets)
    return out


def _sanitize_tools(
    tools: List[Dict[str, Any]], *, exact_secrets: Sequence[str]
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for tool in (tools or [])[:MAX_TOOL_DEFS]:
        if not isinstance(tool, dict):
            continue
        cleaned = _sanitize_value(tool, exact_secrets=exact_secrets)
        if not isinstance(cleaned, dict):
            continue
        # Bound serialized size
        import json

        raw = json.dumps(cleaned, default=str)
        if len(raw.encode("utf-8")) > MAX_TOOL_DEF_BYTES:
            cleaned = {"name": str(cleaned.get("name") or "")[:64], "truncated": True}
        out.append(cleaned)
    return out


def sanitize_model_request(
    request: ModelRequest,
    *,
    max_prompt_chars: int = DEFAULT_MAX_PROMPT_CHARS,
    include_tenant_session: bool = False,
) -> ModelRequest:
    """
    Return a sanitized copy of ``request`` safe for provider transport.

    Raises SanitizationError if the request cannot be processed safely.
    """
    try:
        exact = _configured_secret_values()
        # Also treat values already present under secret keys as exact secrets
        for key, val in dict(request.context or {}).items():
            if _is_secret_key(str(key)) and isinstance(val, str) and len(val) >= 4:
                exact.append(val)
        for key, val in dict(request.metadata or {}).items():
            if _is_secret_key(str(key)) and isinstance(val, str) and len(val) >= 4:
                exact.append(val)
        # Deduplicate while preserving order
        seen = set()
        exact_secrets: List[str] = []
        for s in exact:
            if s not in seen:
                seen.add(s)
                exact_secrets.append(s)

        system = _redact_text(request.system or "", exact_secrets=exact_secrets)
        messages: List[ModelMessage] = []
        for msg in request.messages or []:
            role = msg.role if isinstance(msg.role, MessageRole) else MessageRole(str(msg.role))
            content = _redact_text(msg.content or "", exact_secrets=exact_secrets)
            meta = _sanitize_message_metadata(dict(msg.metadata or {}), exact_secrets=exact_secrets)
            messages.append(
                ModelMessage(
                    role=role,
                    content=content,
                    name=str(msg.name or "")[:64],
                    tool_call_id=str(msg.tool_call_id or "")[:64],
                    metadata=meta,
                )
            )

        context = _sanitize_value(dict(request.context or {}), exact_secrets=exact_secrets)
        metadata = _sanitize_value(dict(request.metadata or {}), exact_secrets=exact_secrets)
        if not isinstance(context, dict) or not isinstance(metadata, dict):
            raise SanitizationError("sanitization_non_object")

        # Provider-bound diagnostics: drop secret keys entirely from metadata keys
        for banned in list(metadata.keys()):
            if _is_secret_key(str(banned)):
                metadata[str(banned)] = REDACTED

        tools = _sanitize_tools(list(request.tools or []), exact_secrets=exact_secrets)

        # Bound total prompt length
        prompt_budget = max(256, int(max_prompt_chars))
        used = len(system)
        bounded_messages: List[ModelMessage] = []
        for msg in messages:
            remaining = prompt_budget - used
            if remaining <= 0:
                break
            content = msg.content[:remaining]
            used += len(content)
            bounded_messages.append(
                ModelMessage(
                    role=msg.role,
                    content=content,
                    name=msg.name,
                    tool_call_id=msg.tool_call_id,
                    metadata=msg.metadata,
                )
            )
        if len(system) > prompt_budget:
            system = system[:prompt_budget]

        tenant_id = request.tenant_id if include_tenant_session else ""
        session_id = request.session_id if include_tenant_session else ""

        return ModelRequest(
            messages=bounded_messages,
            role=str(request.role or "GUEST"),
            system=system,
            temperature=float(request.temperature or 0.0),
            max_tokens=int(request.max_tokens or 0),
            response_format=str(request.response_format or "text"),
            tools=tools,
            multimodal=[],  # multimodal refs not forwarded by local transport in 3A
            timeout_s=float(request.timeout_s or 30.0),
            cancel_token=request.cancel_token,
            trace_id="",  # do not forward trace identifiers by default
            session_id=session_id,
            tenant_id=tenant_id,
            context=context,
            metadata=metadata,
        )
    except SanitizationError:
        raise
    except Exception as exc:
        raise SanitizationError(f"sanitization_failed:{type(exc).__name__}") from exc


def scrub_context_for_provider(context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Backward-compatible context scrubber."""
    exact = _configured_secret_values()
    cleaned = _sanitize_value(dict(context or {}), exact_secrets=exact)
    return cleaned if isinstance(cleaned, dict) else {}
