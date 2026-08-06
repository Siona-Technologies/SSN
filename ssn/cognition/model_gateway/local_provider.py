"""
Optional local open-weight ModelProvider (Phase 3A/3B).

Disabled by default. Talks to a user-controlled local HTTP model service.
Does not download weights, launch runtimes, or execute tools.
HTTP redirects are rejected by default.

Phase 3B adds an optional ``openai_chat`` API dialect for llama.cpp /
OpenAI-compatible servers. Default dialect remains ``siona_generate`` for
deterministic Phase 3A mock compatibility.
"""

from __future__ import annotations

import ipaddress
import json
import math
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from ssn.cognition.model_gateway.contracts import (
    MessageRole,
    ModelCapabilities,
    ModelRequest,
    ModelResponse,
    ModelUsage,
    ToolCallProposal,
)
from ssn.cognition.model_gateway.sanitize import (
    SanitizationError,
    sanitize_model_request,
    scrub_context_for_provider,
)

ENV_PROVIDER = "SSN_MODEL_PROVIDER"
ENV_ENDPOINT = "SSN_LOCAL_MODEL_ENDPOINT"
ENV_MODEL_ID = "SSN_LOCAL_MODEL_ID"
ENV_ALLOW_REMOTE = "SSN_LOCAL_MODEL_ALLOW_REMOTE"
ENV_TIMEOUT = "SSN_LOCAL_MODEL_TIMEOUT_S"
ENV_MAX_BYTES = "SSN_LOCAL_MODEL_MAX_RESPONSE_BYTES"
ENV_LEGACY_ENDPOINT = "SSN_LLM_ENDPOINT"
ENV_API_DIALECT = "SSN_LOCAL_MODEL_API_DIALECT"
ENV_VERIFY_MODEL_ID = "SSN_LOCAL_MODEL_VERIFY_MODEL_ID"
ENV_MAX_TOKENS_CAP = "SSN_LOCAL_MODEL_MAX_TOKENS_CAP"

DIALECT_SIONA_GENERATE = "siona_generate"
DIALECT_OPENAI_CHAT = "openai_chat"
ALLOWED_API_DIALECTS = frozenset({DIALECT_SIONA_GENERATE, DIALECT_OPENAI_CHAT})

DEFAULT_MAX_RESPONSE_BYTES = 1_048_576
DEFAULT_TIMEOUT_S = 20.0
MIN_TRANSPORT_TIMEOUT_S = 0.1
MAX_TRANSPORT_TIMEOUT_S = 119.0
MAX_GATEWAY_TIMEOUT_S = 120.0
GATEWAY_TIMEOUT_MARGIN_S = 1.0
DEFAULT_OPENAI_MAX_TOKENS_CAP = 512
MAX_TOKENS_CAP_HARD_MAX = 8192
MAX_MODEL_ID_CHARS = 256
MAX_HEALTH_META_CHARS = 128
MIN_TCP_PORT = 1
MAX_TCP_PORT = 65535
OPENAI_TEMPERATURE_MIN = 0.0
OPENAI_TEMPERATURE_MAX = 2.0
DEFAULT_MAX_TEXT_CHARS = 262_144
DEFAULT_MAX_TOOL_PROPOSALS = 16
DEFAULT_MAX_TOOL_NAME = 128
DEFAULT_MAX_TOOL_CALL_ID = 128
DEFAULT_MAX_TOOL_REASON = 512
DEFAULT_MAX_ARG_DEPTH = 4
DEFAULT_MAX_ARG_KEYS = 32
DEFAULT_MAX_ARG_BYTES = 8_192
DEFAULT_MAX_USAGE_TOKENS = 100_000_000
ALLOWED_FINISH_REASONS = frozenset(
    {"stop", "length", "tool_calls", "cancelled", "error", "content_filter", "unknown"}
)


class LocalProviderError(RuntimeError):
    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category


def local_provider_enabled() -> bool:
    return (os.getenv(ENV_PROVIDER) or "").strip().lower() in {
        "local",
        "local_open_weight",
        "open_weight",
    }


def _is_finite_number(value: Any) -> bool:
    try:
        number = float(value)
    except Exception:
        return False
    return math.isfinite(number)


def normalize_transport_timeout(value: Any, *, explicit: bool) -> float:
    """
    Normalize a transport timeout.

    - Environment / soft path (explicit=False): invalid values revert to default.
    - Constructor path (explicit=True): invalid/non-finite/non-positive fail closed.
    """
    if value is None or (isinstance(value, str) and not str(value).strip()):
        if explicit:
            raise LocalProviderError("config", "invalid_timeout:empty")
        return DEFAULT_TIMEOUT_S
    try:
        number = float(value)
    except Exception as exc:
        if explicit:
            raise LocalProviderError("config", f"invalid_timeout:{exc}") from exc
        return DEFAULT_TIMEOUT_S
    if not math.isfinite(number):
        if explicit:
            raise LocalProviderError("config", "invalid_timeout:non_finite")
        return DEFAULT_TIMEOUT_S
    if number <= 0.0:
        if explicit:
            raise LocalProviderError("config", "invalid_timeout:non_positive")
        return DEFAULT_TIMEOUT_S
    if number < MIN_TRANSPORT_TIMEOUT_S:
        if explicit:
            raise LocalProviderError("config", "invalid_timeout:below_minimum")
        return DEFAULT_TIMEOUT_S
    if number > MAX_TRANSPORT_TIMEOUT_S:
        if explicit:
            raise LocalProviderError("config", "invalid_timeout:above_maximum")
        return DEFAULT_TIMEOUT_S
    return float(number)


def _parse_timeout() -> float:
    raw = (os.getenv(ENV_TIMEOUT) or "").strip()
    if not raw:
        return DEFAULT_TIMEOUT_S
    return normalize_transport_timeout(raw, explicit=False)


def compute_gateway_timeout_s(transport_timeout_s: float) -> float:
    transport = normalize_transport_timeout(transport_timeout_s, explicit=True)
    return min(MAX_GATEWAY_TIMEOUT_S, float(transport) + float(GATEWAY_TIMEOUT_MARGIN_S))


def normalize_gateway_timeout(value: Any) -> float:
    """Validate an explicitly supplied ModelGatewayAsLLMProvider timeout."""
    try:
        number = float(value)
    except Exception as exc:
        raise LocalProviderError("config", f"invalid_gateway_timeout:{exc}") from exc
    if not math.isfinite(number):
        raise LocalProviderError("config", "invalid_gateway_timeout:non_finite")
    minimum = MIN_TRANSPORT_TIMEOUT_S + GATEWAY_TIMEOUT_MARGIN_S
    if number < minimum or number > MAX_GATEWAY_TIMEOUT_S:
        raise LocalProviderError("config", "invalid_gateway_timeout:out_of_bounds")
    return float(number)


def validate_model_id_value(model_id: str, *, configured: bool = True) -> str:
    value = str(model_id or "").strip()
    if not value:
        raise LocalProviderError("config" if configured else "malformed", "model_id_invalid")
    if len(value) > MAX_MODEL_ID_CHARS:
        raise LocalProviderError("config" if configured else "malformed", "model_id_invalid")
    return value


def validate_openai_temperature(value: Any) -> float:
    try:
        number = float(value)
    except Exception as exc:
        raise LocalProviderError("request", f"invalid_temperature:{exc}") from exc
    if not math.isfinite(number):
        raise LocalProviderError("request", "invalid_temperature:non_finite")
    if number < OPENAI_TEMPERATURE_MIN or number > OPENAI_TEMPERATURE_MAX:
        raise LocalProviderError("request", "invalid_temperature:out_of_range")
    return float(number)


def bound_health_meta_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if len(text) > MAX_HEALTH_META_CHARS:
        return text[:MAX_HEALTH_META_CHARS]
    return text


def extract_health_raw(obj: Dict[str, Any]) -> Dict[str, Any]:
    raw: Dict[str, Any] = {}
    if obj.get("ok") is True or obj.get("ok") is False:
        raw["ok"] = bool(obj.get("ok"))
    status = bound_health_meta_string(obj.get("status"))
    if status is not None:
        raw["status"] = status
    service = bound_health_meta_string(obj.get("service"))
    if service is not None:
        raw["service"] = service
    return raw

def _parse_max_bytes() -> int:
    raw = (os.getenv(ENV_MAX_BYTES) or "").strip()
    try:
        return max(1024, int(raw)) if raw else DEFAULT_MAX_RESPONSE_BYTES
    except Exception:
        return DEFAULT_MAX_RESPONSE_BYTES


def allow_remote_endpoints() -> bool:
    return (os.getenv(ENV_ALLOW_REMOTE) or "").strip().lower() in {"1", "true", "yes", "on"}


def resolve_endpoint(explicit: Optional[str] = None) -> str:
    return (explicit or os.getenv(ENV_ENDPOINT) or os.getenv(ENV_LEGACY_ENDPOINT) or "").strip()


def resolve_model_id(explicit: Optional[str] = None) -> str:
    """Return configured model ID or empty string when missing (never 'unconfigured')."""
    if explicit is not None:
        return str(explicit).strip()
    return (os.getenv(ENV_MODEL_ID) or "").strip()


def parse_env_bool(raw: Optional[str], *, default: bool) -> bool:
    if raw is None:
        return default
    value = str(raw).strip().lower()
    if value == "":
        return default
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def resolve_api_dialect(explicit: Optional[str] = None) -> str:
    raw = (explicit if explicit is not None else (os.getenv(ENV_API_DIALECT) or "")).strip().lower()
    if not raw:
        return DIALECT_SIONA_GENERATE
    if raw not in ALLOWED_API_DIALECTS:
        raise LocalProviderError("config", f"unknown_api_dialect:{raw}")
    return raw


def resolve_verify_model_id(dialect: str, explicit: Optional[bool] = None) -> bool:
    if explicit is not None:
        return bool(explicit)
    default = dialect == DIALECT_OPENAI_CHAT
    return parse_env_bool(os.getenv(ENV_VERIFY_MODEL_ID), default=default)


def resolve_max_tokens_cap(dialect: str, explicit: Optional[int] = None) -> Optional[int]:
    """Return positive token cap. None means no transport cap (siona_generate default)."""
    if explicit is not None:
        try:
            value = int(explicit)
        except Exception as exc:
            raise LocalProviderError("config", f"invalid_max_tokens_cap:{exc}") from exc
        if value <= 0:
            raise LocalProviderError("config", "invalid_max_tokens_cap:non_positive")
        return min(value, MAX_TOKENS_CAP_HARD_MAX)
    raw = (os.getenv(ENV_MAX_TOKENS_CAP) or "").strip()
    if raw:
        try:
            value = int(raw)
        except Exception:
            value = DEFAULT_OPENAI_MAX_TOKENS_CAP if dialect == DIALECT_OPENAI_CHAT else 0
            if dialect != DIALECT_OPENAI_CHAT:
                return None
            return min(max(1, value), MAX_TOKENS_CAP_HARD_MAX)
        if value <= 0:
            if dialect == DIALECT_OPENAI_CHAT:
                return DEFAULT_OPENAI_MAX_TOKENS_CAP
            return None
        return min(value, MAX_TOKENS_CAP_HARD_MAX)
    if dialect == DIALECT_OPENAI_CHAT:
        return DEFAULT_OPENAI_MAX_TOKENS_CAP
    return None


def interpret_health_payload(obj: Dict[str, Any]) -> Tuple[bool, str]:
    """Fail-closed health interpretation for mock and llama.cpp payloads."""
    if not isinstance(obj, dict):
        return False, "health_contract_unrecognized"
    if obj.get("ok") is True:
        return True, ""
    if obj.get("status") == "ok":
        return True, ""
    return False, "health_contract_unrecognized"


def _validated_port(parsed: urllib_parse.ParseResult) -> Optional[int]:
    """Return validated TCP port or None when absent. Fail closed on malformed ports."""
    try:
        port = parsed.port
    except ValueError as exc:
        raise LocalProviderError("config", f"invalid_port:{exc}") from exc
    except Exception as exc:
        raise LocalProviderError("config", f"invalid_port:{exc}") from exc
    if port is None:
        # Catch non-numeric port text that urlparse may not always raise for.
        netloc = parsed.netloc or ""
        if "@" in netloc:
            netloc = netloc.rsplit("@", 1)[-1]
        if netloc.startswith("["):
            if "]" in netloc:
                rest = netloc.split("]", 1)[1]
                if rest.startswith(":"):
                    raw_port = rest[1:]
                    if raw_port and not raw_port.isdigit():
                        raise LocalProviderError("config", "invalid_port:non_numeric")
                    if raw_port.isdigit():
                        port = int(raw_port)
        elif ":" in netloc:
            raw_port = netloc.rsplit(":", 1)[-1]
            if raw_port and not raw_port.isdigit():
                raise LocalProviderError("config", "invalid_port:non_numeric")
            if raw_port.isdigit():
                port = int(raw_port)
    if port is None:
        return None
    if not isinstance(port, int) or port < MIN_TCP_PORT or port > MAX_TCP_PORT:
        raise LocalProviderError("config", "invalid_port:out_of_range")
    return port


def _origin_hostport(parsed: urllib_parse.ParseResult) -> str:
    host = parsed.hostname or ""
    port = _validated_port(parsed)
    if port is not None:
        if ":" in host:
            return f"[{host}]:{port}"
        return f"{host}:{port}"
    return f"[{host}]" if ":" in host else host

def resolve_openai_chat_endpoints(url: str) -> Tuple[str, str, str]:
    """
    Derive chat/health/models URLs for openai_chat dialect.

    Accepts only a base origin (http://host:port[/]) or the exact chat path
    /v1/chat/completions. Ambiguous paths fail closed.
    """
    try:
        parsed = urllib_parse.urlparse(url)
    except Exception as exc:
        raise LocalProviderError("config", f"malformed_url:{exc}") from exc
    if parsed.query:
        raise LocalProviderError("config", "openai_chat_query_rejected")
    path = parsed.path or ""
    normalized = path.rstrip("/")
    if normalized in {"",}:
        chat_path = "/v1/chat/completions"
    elif normalized == "/v1/chat/completions":
        chat_path = "/v1/chat/completions"
    else:
        raise LocalProviderError(
            "config",
            f"openai_chat_ambiguous_path:{path or '/'}",
        )
    hostport = _origin_hostport(parsed)
    chat = urllib_parse.urlunparse((parsed.scheme, hostport, chat_path, "", "", ""))
    health = urllib_parse.urlunparse((parsed.scheme, hostport, "/health", "", "", ""))
    models = urllib_parse.urlunparse((parsed.scheme, hostport, "/v1/models", "", "", ""))
    return chat, health, models


def _is_loopback_host(host: str) -> bool:
    h = (host or "").lower().strip("[]")
    if h in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(h).is_loopback
    except ValueError:
        return False


def classify_endpoint_host(host: str) -> str:
    if _is_loopback_host(host):
        return "loopback"
    return "remote"


def safe_endpoint_summary(url: str) -> Dict[str, Any]:
    """Summarize endpoint without exposing sensitive query material."""
    try:
        parsed = urllib_parse.urlparse(url)
        host = (parsed.hostname or "").strip("[]")
        classification = classify_endpoint_host(host) if host else "invalid"
        try:
            port = _validated_port(parsed)
        except LocalProviderError:
            return {"classification": "invalid"}
        return {
            "scheme": parsed.scheme,
            "host": host,
            "port": port,
            "path": parsed.path,
            "classification": classification,
            "has_query": bool(parsed.query),
            "has_fragment": bool(parsed.fragment),
            "has_userinfo": bool(parsed.username or parsed.password),
        }
    except Exception:
        return {"classification": "invalid"}


def validate_endpoint_url(url: str, *, allow_remote: bool = False) -> str:
    """
    Validate scheme, host, credentials, fragments, and loopback policy.
    Raises LocalProviderError on rejection.
    """
    if not url or not str(url).strip():
        raise LocalProviderError("config", "local model endpoint is not configured")
    try:
        parsed = urllib_parse.urlparse(url)
    except Exception as exc:
        raise LocalProviderError("config", f"malformed_url:{exc}") from exc

    if parsed.scheme not in {"http", "https"}:
        raise LocalProviderError("config", f"unsupported endpoint scheme: {parsed.scheme!r}")
    if parsed.username is not None or parsed.password is not None:
        raise LocalProviderError("security", "embedded_credentials_rejected")
    if parsed.fragment:
        raise LocalProviderError("security", "url_fragment_rejected")

    host = parsed.hostname
    if not host:
        raise LocalProviderError("config", "endpoint missing hostname")

    # Fail closed on malformed / out-of-range ports before any derivation.
    _validated_port(parsed)

    # Reject malformed IPv6 literals that urlparse might partially accept
    raw_netloc = parsed.netloc or ""
    if raw_netloc.startswith("["):
        if "]" not in raw_netloc:
            raise LocalProviderError("config", "malformed_ipv6")
        try:
            ipaddress.IPv6Address(host)
        except Exception as exc:
            raise LocalProviderError("config", f"malformed_ipv6:{exc}") from exc

    classification = classify_endpoint_host(host)
    if classification == "loopback":
        return url
    if not allow_remote:
        raise LocalProviderError(
            "security",
            f"non-loopback endpoint rejected ({host}); set {ENV_ALLOW_REMOTE}=1 to allow",
        )
    return url


class _RejectRedirectHandler(urllib_request.HTTPRedirectHandler):
    """Reject all HTTP redirects (Phase 3A default)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        raise LocalProviderError(
            "redirect",
            f"redirect_rejected:{code}:{newurl}",
        )


def _opener_no_redirects() -> urllib_request.OpenerDirector:
    return urllib_request.build_opener(_RejectRedirectHandler)


class LocalHttpTransport:
    """
    Thin transport adapter — maps ModelRequest to HTTP JSON and back.

    Redirects are disabled by default. Response bodies are size-bounded and
    semantically validated. Supports ``siona_generate`` (Phase 3A mock) and
    ``openai_chat`` (llama.cpp OpenAI-compatible) dialects.
    """

    def __init__(
        self,
        endpoint: str,
        *,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        allow_remote: bool = False,
        capture_last_request: bool = False,
        api_dialect: str = DIALECT_SIONA_GENERATE,
        max_tokens_cap: Optional[int] = None,
        verify_model_id: bool = False,
        health_endpoint: Optional[str] = None,
        models_endpoint: Optional[str] = None,
    ) -> None:
        self.endpoint = endpoint
        self.timeout_s = timeout_s
        self.max_response_bytes = max_response_bytes
        self.allow_remote = allow_remote
        self.capture_last_request = capture_last_request
        self.api_dialect = api_dialect
        self.max_tokens_cap = max_tokens_cap
        self.verify_model_id = bool(verify_model_id)
        self._health_endpoint = health_endpoint
        self._models_endpoint = models_endpoint
        self.last_request_body: Optional[bytes] = None
        self.last_request_url: Optional[str] = None
        self._opener = _opener_no_redirects()

    def health_url(self) -> str:
        if self._health_endpoint:
            return self._health_endpoint
        parsed = urllib_parse.urlparse(self.endpoint)
        path = parsed.path or ""
        if path.endswith("/generate"):
            health_path = path[: -len("/generate")] + "/health"
        elif path.endswith("/v1/generate"):
            health_path = path[: -len("/v1/generate")] + "/health"
        else:
            health_path = "/health"
        hostport = _origin_hostport(parsed)
        return urllib_parse.urlunparse((parsed.scheme, hostport, health_path, "", "", ""))

    def models_url(self) -> str:
        if self._models_endpoint:
            return self._models_endpoint
        parsed = urllib_parse.urlparse(self.endpoint)
        hostport = _origin_hostport(parsed)
        return urllib_parse.urlunparse((parsed.scheme, hostport, "/v1/models", "", "", ""))

    def _open(self, req: urllib_request.Request):
        try:
            return self._opener.open(req, timeout=self.timeout_s)
        except LocalProviderError:
            raise
        except TimeoutError as exc:
            raise LocalProviderError("timeout", "provider_timeout") from exc
        except urllib_error.HTTPError as exc:
            if exc.code in {301, 302, 303, 307, 308}:
                loc = exc.headers.get("Location", "")
                raise LocalProviderError("redirect", f"redirect_rejected:{exc.code}:{loc}") from exc
            raise LocalProviderError("http", f"http_status:{exc.code}") from exc
        except urllib_error.URLError as exc:
            reason = str(exc.reason if hasattr(exc, "reason") else exc)
            if "timed out" in reason.lower() or "timeout" in reason.lower():
                raise LocalProviderError("timeout", "provider_timeout") from exc
            if isinstance(exc.reason, LocalProviderError):
                raise exc.reason
            raise LocalProviderError("http", f"http_error:{exc}") from exc
        except Exception as exc:
            if isinstance(exc, LocalProviderError):
                raise
            msg = str(exc).lower()
            if "timed out" in msg or "timeout" in msg:
                raise LocalProviderError("timeout", "provider_timeout") from exc
            raise LocalProviderError("http", f"http_exception:{exc}") from exc

    def post_json(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        validate_endpoint_url(url, allow_remote=self.allow_remote)
        data = json.dumps(payload).encode("utf-8")
        if self.capture_last_request:
            self.last_request_body = data
            self.last_request_url = url
        req = urllib_request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with self._open(req) as resp:
            raw = resp.read(self.max_response_bytes + 1)
        if len(raw) > self.max_response_bytes:
            raise LocalProviderError("size", "response_too_large")
        try:
            obj = json.loads(raw.decode("utf-8", errors="replace"))
        except Exception as exc:
            raise LocalProviderError("malformed", f"json_decode:{exc}") from exc
        if not isinstance(obj, dict):
            raise LocalProviderError("malformed", "response_not_object")
        return obj

    def get_json(self, url: str) -> Dict[str, Any]:
        validate_endpoint_url(url, allow_remote=self.allow_remote)
        req = urllib_request.Request(url, method="GET")
        with self._open(req) as resp:
            raw = resp.read(self.max_response_bytes + 1)
        if len(raw) > self.max_response_bytes:
            raise LocalProviderError("size", "health_response_too_large")
        try:
            obj = json.loads(raw.decode("utf-8", errors="replace"))
        except Exception as exc:
            raise LocalProviderError("malformed", f"health_json:{exc}") from exc
        if not isinstance(obj, dict):
            raise LocalProviderError("malformed", "health_not_object")
        return obj

    def build_generate_payload(self, request: ModelRequest, *, model_id: str) -> Dict[str, Any]:
        if self.api_dialect == DIALECT_OPENAI_CHAT:
            return self._build_openai_chat_payload(request, model_id=model_id)
        return self._build_siona_generate_payload(request, model_id=model_id)

    def _apply_max_tokens_cap(self, requested: int) -> int:
        try:
            value = int(requested)
        except Exception:
            value = 1
        if value <= 0:
            value = 1
        if self.max_tokens_cap is not None:
            return min(value, int(self.max_tokens_cap))
        return value

    def _build_siona_generate_payload(self, request: ModelRequest, *, model_id: str) -> Dict[str, Any]:
        sanitized = sanitize_model_request(request, include_tenant_session=False)
        prompt_parts = []
        for m in sanitized.messages:
            role = m.role.value if isinstance(m.role, MessageRole) else m.role
            prompt_parts.append(f"{role}: {m.content}")
        if sanitized.system:
            prompt_parts.insert(0, f"system: {sanitized.system}")
        prompt = "\n".join(prompt_parts) if prompt_parts else ""
        return {
            "prompt": prompt,
            "role": sanitized.role,
            "context": dict(sanitized.context or {}),
            "model": model_id,
            "response_format": sanitized.response_format,
            "temperature": sanitized.temperature,
            "max_tokens": self._apply_max_tokens_cap(sanitized.max_tokens),
            "tools": list(sanitized.tools or []),
            "system": sanitized.system,
            "messages": [m.to_dict() for m in sanitized.messages],
            "metadata": dict(sanitized.metadata or {}),
        }

    def _openai_role(self, role: Any) -> Optional[str]:
        value = role.value if isinstance(role, MessageRole) else str(role or "")
        value = value.strip().lower()
        if value in {"system", "user", "assistant"}:
            return value
        if value == "tool":
            return None
        return "user"

    def _build_openai_chat_payload(self, request: ModelRequest, *, model_id: str) -> Dict[str, Any]:
        sanitized = sanitize_model_request(request, include_tenant_session=False)
        messages: List[Dict[str, str]] = []
        if sanitized.system and str(sanitized.system).strip():
            messages.append({"role": "system", "content": str(sanitized.system)})
        for m in sanitized.messages:
            mapped = self._openai_role(m.role)
            if mapped is None:
                continue
            messages.append({"role": mapped, "content": str(m.content or "")})
        # Fail closed: do not manufacture an empty user message.
        if not messages or not any(str(item.get("content") or "").strip() for item in messages):
            raise LocalProviderError("request", "empty_messages")
        temperature = validate_openai_temperature(sanitized.temperature)
        payload: Dict[str, Any] = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self._apply_max_tokens_cap(sanitized.max_tokens),
            "stream": False,
        }
        if str(sanitized.response_format or "").strip().lower() == "json":
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _bound_arguments(self, args: Any, *, depth: int = 0) -> Dict[str, Any]:
        if not isinstance(args, dict):
            return {}
        if depth > DEFAULT_MAX_ARG_DEPTH:
            return {"__truncated_depth__": True}
        out: Dict[str, Any] = {}
        for i, (k, v) in enumerate(args.items()):
            if i >= DEFAULT_MAX_ARG_KEYS:
                out["__truncated__"] = True
                break
            key = str(k)[:64]
            if isinstance(v, dict):
                out[key] = self._bound_arguments(v, depth=depth + 1)
            elif isinstance(v, list):
                out[key] = v[:16]
            elif isinstance(v, str):
                out[key] = v[:512]
            elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                continue
            elif isinstance(v, (int, float, bool)) or v is None:
                out[key] = v
            else:
                out[key] = str(v)[:256]
        raw = json.dumps(out, default=str).encode("utf-8")
        if len(raw) > DEFAULT_MAX_ARG_BYTES:
            return {"__truncated_size__": True}
        return out

    def _parse_confidence(self, raw: Any) -> Optional[float]:
        try:
            conf = float(raw)
        except Exception:
            return None
        if not math.isfinite(conf):
            return None
        if conf < 0.0 or conf > 1.0:
            return None
        return conf

    def _parse_usage(self, usage_raw: Any) -> ModelUsage:
        if not isinstance(usage_raw, dict):
            return ModelUsage()

        def _tok(name: str) -> int:
            try:
                v = int(usage_raw.get(name) or 0)
            except Exception as exc:
                raise LocalProviderError("malformed", f"invalid_usage:{name}") from exc
            if v < 0 or v > DEFAULT_MAX_USAGE_TOKENS:
                raise LocalProviderError("malformed", f"usage_out_of_bounds:{name}")
            return v

        try:
            latency = float(usage_raw.get("latency_ms") or 0.0)
        except Exception as exc:
            raise LocalProviderError("malformed", "invalid_usage_latency") from exc
        if not math.isfinite(latency) or latency < 0.0:
            raise LocalProviderError("malformed", "invalid_usage_latency")
        return ModelUsage(
            prompt_tokens=_tok("prompt_tokens"),
            completion_tokens=_tok("completion_tokens"),
            total_tokens=_tok("total_tokens"),
            latency_ms=latency,
        )

    def parse_generate_response(self, obj: Dict[str, Any], *, provider_name: str) -> ModelResponse:
        if self.api_dialect == DIALECT_OPENAI_CHAT:
            return self._parse_openai_chat_response(obj, provider_name=provider_name)
        return self._parse_siona_generate_response(obj, provider_name=provider_name)

    def _parse_openai_chat_response(self, obj: Dict[str, Any], *, provider_name: str) -> ModelResponse:
        choices = obj.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LocalProviderError("malformed", "missing_choices")
        first = choices[0]
        if not isinstance(first, dict):
            raise LocalProviderError("malformed", "choice_not_object")
        message = first.get("message")
        if not isinstance(message, dict):
            raise LocalProviderError("malformed", "missing_message")
        text = message.get("content")
        if not isinstance(text, str):
            raise LocalProviderError("malformed", "missing_text")
        if text == "":
            raise LocalProviderError("malformed", "empty_content")
        if len(text) > DEFAULT_MAX_TEXT_CHARS:
            raise LocalProviderError("size", "text_too_large")

        finish = str(first.get("finish_reason") or "stop")
        if finish not in ALLOWED_FINISH_REASONS:
            finish = "unknown"

        usage_raw = obj.get("usage")
        if isinstance(usage_raw, dict):
            usage = self._parse_usage(usage_raw)
            provider_usage_reported = True
        else:
            usage = ModelUsage()
            provider_usage_reported = False

        raw_tool_calls = message.get("tool_calls")
        if raw_tool_calls is None:
            raw_tool_calls = first.get("tool_calls")
        if not isinstance(raw_tool_calls, list):
            raw_tool_calls = []
        observed_tool_count = len(raw_tool_calls)
        ignored_tools = observed_tool_count > 0
        structured = None
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                parsed_obj = json.loads(stripped)
                if isinstance(parsed_obj, dict):
                    structured = parsed_obj
            except Exception:
                structured = None

        return ModelResponse(
            text=text,
            provider=provider_name,
            tool_calls=[],
            structured=structured,
            usage=usage,
            finish_reason=finish,
            healthy=True,
            meta={
                "engine": provider_name,
                "local_open_weight": True,
                "api_dialect": DIALECT_OPENAI_CHAT,
                "openai_tool_calls_ignored": ignored_tools,
                "provider_tool_calls_observed_count": observed_tool_count,
                "provider_tool_calls_observed": observed_tool_count > 0,
                "provider_tool_calls_ignored": ignored_tools,
                "provider_usage_reported": provider_usage_reported,
            },
        )

    def verify_listed_model_id(self, model_id: str) -> None:
        obj = self.get_json(self.models_url())
        data = obj.get("data")
        if not isinstance(data, list):
            raise LocalProviderError("model_mismatch", "models_list_unrecognized")
        ids: List[str] = []
        for item in data[:256]:
            if not isinstance(item, dict):
                raise LocalProviderError("malformed", "models_list_unrecognized")
            mid = item.get("id")
            if not isinstance(mid, str) or not mid.strip():
                raise LocalProviderError("malformed", "model_id_invalid")
            if len(mid.strip()) > MAX_MODEL_ID_CHARS:
                raise LocalProviderError("malformed", "model_id_invalid")
            ids.append(mid.strip())
        if model_id not in ids:
            # Do not echo the full configured ID (may be long); stable reason only.
            raise LocalProviderError("model_mismatch", "model_id_not_listed")

    def _parse_siona_generate_response(self, obj: Dict[str, Any], *, provider_name: str) -> ModelResponse:
        text = obj.get("text")
        if not isinstance(text, str):
            raise LocalProviderError("malformed", "missing_text")
        if len(text) > DEFAULT_MAX_TEXT_CHARS:
            raise LocalProviderError("size", "text_too_large")

        meta = obj.get("meta") if isinstance(obj.get("meta"), dict) else {}
        meta = {str(k)[:64]: meta[k] for i, k in enumerate(meta) if i < 32}

        structured = obj.get("structured")
        if structured is not None:
            if not isinstance(structured, dict):
                raise LocalProviderError("malformed", "structured_not_object")
            if len(json.dumps(structured, default=str)) > DEFAULT_MAX_ARG_BYTES:
                raise LocalProviderError("size", "structured_too_large")

        tool_calls: List[ToolCallProposal] = []
        raw_tools = obj.get("tool_calls")
        if raw_tools is not None and not isinstance(raw_tools, list):
            raise LocalProviderError("malformed", "tool_calls_not_list")
        if isinstance(raw_tools, list):
            if len(raw_tools) > DEFAULT_MAX_TOOL_PROPOSALS:
                raise LocalProviderError("size", "tool_proposals_too_many")
            for item in raw_tools:
                if not isinstance(item, dict):
                    raise LocalProviderError("malformed", "tool_proposal_not_object")
                name = str(item.get("name") or "")
                if not name:
                    raise LocalProviderError("malformed", "tool_proposal_empty_name")
                if len(name) > DEFAULT_MAX_TOOL_NAME:
                    raise LocalProviderError("size", "tool_name_too_long")
                call_id = str(item.get("call_id") or "")
                if len(call_id) > DEFAULT_MAX_TOOL_CALL_ID:
                    raise LocalProviderError("size", "tool_call_id_too_long")
                reason = str(item.get("reason") or "")
                if len(reason) > DEFAULT_MAX_TOOL_REASON:
                    raise LocalProviderError("size", "tool_reason_too_long")
                conf = self._parse_confidence(item.get("confidence", 0.5))
                if conf is None:
                    raise LocalProviderError("malformed", "invalid_tool_confidence")
                args = self._bound_arguments(item.get("arguments") or {})
                tool_calls.append(
                    ToolCallProposal(
                        name=name,
                        arguments=args,
                        call_id=call_id,
                        confidence=conf,
                        reason=reason,
                    )
                )

        usage = self._parse_usage(obj.get("usage"))
        finish = str(obj.get("finish_reason") or "stop")
        if finish not in ALLOWED_FINISH_REASONS:
            finish = "unknown"

        return ModelResponse(
            text=text,
            provider=provider_name,
            tool_calls=tool_calls,
            structured=structured if isinstance(structured, dict) else None,
            usage=usage,
            finish_reason=finish,
            healthy=True,
            meta={
                **meta,
                "engine": provider_name,
                "local_open_weight": True,
                "api_dialect": DIALECT_SIONA_GENERATE,
            },
        )


class LocalOpenWeightProvider:
    """
    Canonical ModelProvider for optional local open-weight inference.

    Activation requires SSN_MODEL_PROVIDER=local plus endpoint and model ID.
    """

    name = "siona-local-open-weight-v1"

    def __init__(
        self,
        *,
        endpoint: Optional[str] = None,
        model_id: Optional[str] = None,
        allow_remote: Optional[bool] = None,
        timeout_s: Optional[float] = None,
        max_response_bytes: Optional[int] = None,
        transport: Optional[LocalHttpTransport] = None,
        registry_entry: Optional[Any] = None,
        capture_last_request: bool = False,
        api_dialect: Optional[str] = None,
        verify_model_id: Optional[bool] = None,
        max_tokens_cap: Optional[int] = None,
    ) -> None:
        self._allow_remote = allow_remote_endpoints() if allow_remote is None else bool(allow_remote)
        self._registry_entry = registry_entry
        self._capture_last_request = capture_last_request
        self._config_error: Optional[str] = None
        self._endpoint = ""
        self._endpoint_classification = "unconfigured"
        self._health_endpoint: Optional[str] = None
        self._models_endpoint: Optional[str] = None
        self._api_dialect = DIALECT_SIONA_GENERATE
        self._verify_model_id = False
        self._max_tokens_cap: Optional[int] = None
        self.model_id = ""
        self._timeout_s = DEFAULT_TIMEOUT_S
        self._max_bytes = DEFAULT_MAX_RESPONSE_BYTES

        try:
            self._timeout_s = (
                normalize_transport_timeout(timeout_s, explicit=True)
                if timeout_s is not None
                else _parse_timeout()
            )
            self._max_bytes = (
                int(max_response_bytes) if max_response_bytes is not None else _parse_max_bytes()
            )
            self._api_dialect = resolve_api_dialect(api_dialect)
            self._verify_model_id = resolve_verify_model_id(
                self._api_dialect, explicit=verify_model_id
            )
            self._max_tokens_cap = resolve_max_tokens_cap(
                self._api_dialect, explicit=max_tokens_cap
            )
            raw_model = resolve_model_id(model_id)
            if raw_model:
                self.model_id = validate_model_id_value(raw_model, configured=True)
            else:
                self.model_id = ""
        except LocalProviderError as exc:
            self._config_error = f"{exc.category}:{exc}"

        raw_endpoint = resolve_endpoint(endpoint)
        if not self.model_id:
            self._config_error = self._config_error or "config:model_id_required"
        if not raw_endpoint:
            if self._config_error and "model_id" in str(self._config_error):
                self._config_error = "config:endpoint_and_model_id_required"
            else:
                self._config_error = self._config_error or "config:endpoint_unconfigured"
        elif not self._config_error:
            try:
                validated = validate_endpoint_url(raw_endpoint, allow_remote=self._allow_remote)
                if self._api_dialect == DIALECT_OPENAI_CHAT:
                    chat, health, models = resolve_openai_chat_endpoints(validated)
                    # Re-validate derived URLs under the same security policy.
                    self._endpoint = validate_endpoint_url(chat, allow_remote=self._allow_remote)
                    self._health_endpoint = validate_endpoint_url(
                        health, allow_remote=self._allow_remote
                    )
                    self._models_endpoint = validate_endpoint_url(
                        models, allow_remote=self._allow_remote
                    )
                else:
                    self._endpoint = validated
                summary = safe_endpoint_summary(self._endpoint)
                self._endpoint_classification = str(summary.get("classification") or "unknown")
            except LocalProviderError as exc:
                self._config_error = f"{exc.category}:{exc}"
                self._endpoint = ""
                self._endpoint_classification = "unconfigured"

        can_build_transport = bool(self._endpoint) and self._endpoint_classification in {
            "loopback",
            "remote",
        }
        self.transport = transport or (
            LocalHttpTransport(
                self._endpoint,
                timeout_s=self._timeout_s,
                max_response_bytes=self._max_bytes,
                allow_remote=self._allow_remote,
                capture_last_request=capture_last_request,
                api_dialect=self._api_dialect,
                max_tokens_cap=self._max_tokens_cap,
                verify_model_id=self._verify_model_id,
                health_endpoint=self._health_endpoint,
                models_endpoint=self._models_endpoint,
            )
            if can_build_transport
            else None
        )
        if self.transport and capture_last_request:
            self.transport.capture_last_request = True

    @property
    def api_dialect(self) -> str:
        return self._api_dialect

    @property
    def timeout_s(self) -> float:
        return self._timeout_s

    @property
    def gateway_timeout_s(self) -> float:
        """Outer ModelGateway timeout: transport timeout + bounded margin."""
        return compute_gateway_timeout_s(self._timeout_s)

    def _artifact_verification_status(self) -> str:
        entry = self._registry_entry
        if entry is None:
            return "unverified"
        status = (
            getattr(entry, "artifact_verification_status", None)
            or getattr(entry, "verification_status", None)
            or "unverified"
        )
        if getattr(entry, "mock", False) and status not in {"mock", "unverified"}:
            return "mock"
        return str(status)

    def _capability_verification_status(self) -> str:
        entry = self._registry_entry
        if entry is None:
            return "unverified"
        status = getattr(entry, "capability_verification_status", None) or "unverified"
        if getattr(entry, "mock", False) and status == "verified":
            return "unverified"
        return str(status)

    def _verification_status(self) -> str:
        """Legacy alias → artefact verification status."""
        return self._artifact_verification_status()

    def capabilities(self) -> ModelCapabilities:
        """
        Conservative capabilities until an explicit verified capabilities object exists.

        Distinguishes transport vs configured-model vs verified-model claims
        inside metadata. Behavioural flags are enabled only when
        capability_verification_status == "verified" and fields are explicit.
        """
        art_status = self._artifact_verification_status()
        cap_status = self._capability_verification_status()
        mock = bool(getattr(self._registry_entry, "mock", False)) if self._registry_entry else False
        caps_obj = getattr(self._registry_entry, "capabilities", None) if self._registry_entry else None
        if not isinstance(caps_obj, dict):
            caps_obj = {}

        transport_caps = {
            "chat": True,
            "streaming": False,
            # openai_chat ignores tool calls; siona_generate may carry proposals.
            "tools_proposals": self._api_dialect != DIALECT_OPENAI_CHAT,
            "structured_json_transport": True,
            "api_dialect": self._api_dialect,
        }

        model_chat = True
        model_tools = False
        model_structured = False
        model_streaming = False
        model_multimodal = False
        context_window = 0

        if cap_status == "verified" and caps_obj:
            model_chat = bool(caps_obj.get("chat", False))
            model_tools = bool(caps_obj.get("tools", False))
            model_structured = bool(caps_obj.get("structured_json", False))
            model_streaming = bool(caps_obj.get("streaming", False))
            model_multimodal = bool(caps_obj.get("multimodal", False))
            ctx = caps_obj.get("context_window")
            if isinstance(ctx, int) and ctx > 0:
                context_window = ctx

        return ModelCapabilities(
            chat=model_chat if cap_status == "verified" else True,
            streaming=model_streaming,
            tools=model_tools,
            structured_json=model_structured,
            multimodal=model_multimodal,
            context_window=context_window,
            provider_name=self.name,
            metadata={
                "model_id": self.model_id or None,
                "local": self._endpoint_classification == "loopback",
                "endpoint_classification": self._endpoint_classification,
                "trained_siona_native": False,
                "open_weight": True,
                "simulated": False,
                "optional": True,
                "api_dialect": self._api_dialect,
                "artifact_verification_status": art_status,
                "capability_verification_status": cap_status,
                "verification_status": art_status,
                "transport_capabilities": transport_caps,
                "configured_model_capabilities": {
                    "chat": model_chat if cap_status == "verified" else None,
                    "tools": model_tools if cap_status == "verified" else False,
                    "structured_json": model_structured if cap_status == "verified" else False,
                    "streaming": model_streaming if cap_status == "verified" else False,
                    "multimodal": model_multimodal if cap_status == "verified" else False,
                    "context_window": context_window if context_window > 0 else None,
                },
                "verified_model_capabilities": {
                    "chat": model_chat if cap_status == "verified" else False,
                    "tools": model_tools if cap_status == "verified" else False,
                    "structured_json": model_structured if cap_status == "verified" else False,
                    "streaming": model_streaming if cap_status == "verified" else False,
                    "multimodal": model_multimodal if cap_status == "verified" else False,
                    "context_window": context_window if cap_status == "verified" and context_window > 0 else None,
                },
                "mock_registry": mock,
                "sync_mid_request_cancellation": False,
                "mid_request_cancellation_deferred": "async_provider_transport",
            },
        )

    def health(self) -> Dict[str, Any]:
        base = {
            "provider": self.name,
            "model_id": self.model_id or None,
            "endpoint_classification": self._endpoint_classification,
            "endpoint_loopback": self._endpoint_classification == "loopback",
            "artifact_verification_status": self._artifact_verification_status(),
            "capability_verification_status": self._capability_verification_status(),
            "verification_status": self._artifact_verification_status(),
            "endpoint_summary": safe_endpoint_summary(self._endpoint) if self._endpoint else None,
            "trained_siona_native": False,
            "api_dialect": self._api_dialect,
        }
        if self._config_error:
            return {**base, "ok": False, "error": self._config_error}
        if not self.transport:
            return {**base, "ok": False, "error": "config:endpoint_unconfigured"}
        try:
            obj = self.transport.get_json(self.transport.health_url())
            ok, err = interpret_health_payload(obj)
            result = {
                **base,
                "ok": ok,
                "raw": extract_health_raw(obj),
            }
            if not ok:
                result["error"] = err
            return result
        except LocalProviderError as exc:
            return {**base, "ok": False, "error": f"{exc.category}:{exc}"}

    def generate(self, request: ModelRequest) -> ModelResponse:
        t0 = time.time()
        if self._config_error or not self.transport or not self.model_id or not self._endpoint:
            return ModelResponse(
                text="",
                provider=self.name,
                healthy=False,
                finish_reason="error",
                meta={
                    "error": self._config_error or "config:incomplete",
                    "error_category": "config",
                    "model_id": self.model_id or None,
                    "local_open_weight": True,
                    "endpoint_classification": self._endpoint_classification,
                    "api_dialect": self._api_dialect,
                },
            )
        if request.cancel_token is not None:
            cancelled = bool(getattr(request.cancel_token, "cancelled", False))
            if not cancelled and callable(getattr(request.cancel_token, "is_cancelled", None)):
                try:
                    cancelled = bool(request.cancel_token.is_cancelled())
                except Exception:
                    cancelled = False
            if cancelled:
                return ModelResponse(
                    text="",
                    provider=self.name,
                    healthy=False,
                    finish_reason="cancelled",
                    meta={"error": "cancelled", "model_id": self.model_id},
                )
        try:
            if self.transport.verify_model_id:
                self.transport.verify_listed_model_id(self.model_id)
            payload = self.transport.build_generate_payload(request, model_id=self.model_id)
            obj = self.transport.post_json(self._endpoint, payload)
            resp = self.transport.parse_generate_response(obj, provider_name=self.name)
            latency = max(0.0, (time.time() - t0) * 1000.0)
            usage = ModelUsage(
                prompt_tokens=resp.usage.prompt_tokens,
                completion_tokens=resp.usage.completion_tokens,
                total_tokens=resp.usage.total_tokens,
                latency_ms=latency,
            )
            meta = dict(resp.meta)
            meta["model_id"] = self.model_id
            meta["latency_ms"] = latency
            meta["provider_latency_ms"] = resp.usage.latency_ms
            meta["wall_latency_ms"] = latency
            meta["endpoint_classification"] = self._endpoint_classification
            meta["api_dialect"] = self._api_dialect
            return ModelResponse(
                text=resp.text,
                provider=self.name,
                messages=list(resp.messages),
                tool_calls=list(resp.tool_calls),
                structured=resp.structured,
                usage=usage,
                finish_reason=resp.finish_reason,
                healthy=True,
                meta=meta,
            )
        except SanitizationError as exc:
            return ModelResponse(
                text="",
                provider=self.name,
                healthy=False,
                finish_reason="error",
                meta={
                    "error": str(exc),
                    "error_category": "security",
                    "model_id": self.model_id,
                    "latency_ms": max(0.0, (time.time() - t0) * 1000.0),
                    "api_dialect": self._api_dialect,
                },
            )
        except LocalProviderError as exc:
            return ModelResponse(
                text="",
                provider=self.name,
                healthy=False,
                finish_reason="error",
                meta={
                    "error": str(exc),
                    "error_category": exc.category,
                    "model_id": self.model_id,
                    "latency_ms": max(0.0, (time.time() - t0) * 1000.0),
                    "api_dialect": self._api_dialect,
                },
            )


def build_local_provider_from_env() -> Optional[LocalOpenWeightProvider]:
    if not local_provider_enabled():
        return None
    return LocalOpenWeightProvider()
