"""
Optional local open-weight ModelProvider (Phase 3A).

Disabled by default. Talks to a user-controlled local HTTP model service.
Does not download weights, launch runtimes, or execute tools.
"""

from __future__ import annotations

import ipaddress
import json
import os
import socket
import time
from typing import Any, Dict, Optional
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from ssn.cognition.model_gateway.contracts import (
    MessageRole,
    ModelCapabilities,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelUsage,
    ToolCallProposal,
)

# Import redact lazily inside scrub_context_for_provider to avoid circular
# imports through ssn.integration.__init__.

ENV_PROVIDER = "SSN_MODEL_PROVIDER"
ENV_ENDPOINT = "SSN_LOCAL_MODEL_ENDPOINT"
ENV_MODEL_ID = "SSN_LOCAL_MODEL_ID"
ENV_ALLOW_REMOTE = "SSN_LOCAL_MODEL_ALLOW_REMOTE"
ENV_TIMEOUT = "SSN_LOCAL_MODEL_TIMEOUT_S"
ENV_MAX_BYTES = "SSN_LOCAL_MODEL_MAX_RESPONSE_BYTES"

# Also honour legacy HTTP endpoint naming when provider=local and local endpoint unset.
ENV_LEGACY_ENDPOINT = "SSN_LLM_ENDPOINT"

DEFAULT_MAX_RESPONSE_BYTES = 1_048_576
DEFAULT_TIMEOUT_S = 20.0


class LocalProviderError(RuntimeError):
    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category


def local_provider_enabled() -> bool:
    return (os.getenv(ENV_PROVIDER) or "").strip().lower() in {"local", "local_open_weight", "open_weight"}


def _parse_timeout() -> float:
    raw = (os.getenv(ENV_TIMEOUT) or "").strip()
    try:
        return max(0.1, float(raw)) if raw else DEFAULT_TIMEOUT_S
    except Exception:
        return DEFAULT_TIMEOUT_S


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
    return (explicit or os.getenv(ENV_MODEL_ID) or "unconfigured").strip() or "unconfigured"


def validate_endpoint_url(url: str, *, allow_remote: bool = False) -> str:
    """
    Validate scheme and host. Default: loopback only.
    Raises LocalProviderError on rejection.
    """
    if not url:
        raise LocalProviderError("config", "local model endpoint is not configured")
    parsed = urllib_parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise LocalProviderError("config", f"unsupported endpoint scheme: {parsed.scheme!r}")
    host = parsed.hostname
    if not host:
        raise LocalProviderError("config", "endpoint missing hostname")
    if host.lower() in {"localhost", "127.0.0.1", "::1"}:
        return url
    # Literal IP?
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_loopback:
            return url
    except ValueError:
        pass
    if not allow_remote:
        raise LocalProviderError(
            "security",
            f"non-loopback endpoint rejected ({host}); set {ENV_ALLOW_REMOTE}=1 to allow",
        )
    return url


def _is_loopback_host(host: str) -> bool:
    h = (host or "").lower()
    if h in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(h).is_loopback
    except ValueError:
        return False


def scrub_context_for_provider(context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Strip secrets / credentials before any network send."""
    from ssn.integration.redaction import redact

    return redact(dict(context or {}))


class LocalHttpTransport:
    """
    Thin transport adapter — maps ModelRequest to HTTP JSON and back.

    Default mapping matches the existing mock_llm_server / HttpLLMProvider shape
    so future Ollama/llama.cpp adapters can replace mapping without rewriting
    ModelGateway.
    """

    def __init__(
        self,
        endpoint: str,
        *,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ) -> None:
        self.endpoint = endpoint
        self.timeout_s = timeout_s
        self.max_response_bytes = max_response_bytes

    def health_url(self) -> str:
        parsed = urllib_parse.urlparse(self.endpoint)
        # /generate → /health ; otherwise append sibling /health
        path = parsed.path or ""
        if path.endswith("/generate"):
            health_path = path[: -len("/generate")] + "/health"
        elif path.endswith("/v1/generate"):
            health_path = path[: -len("/v1/generate")] + "/health"
        else:
            health_path = "/health"
        return urllib_parse.urlunparse(
            (parsed.scheme, parsed.netloc, health_path, "", "", "")
        )

    def post_json(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib_request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read(self.max_response_bytes + 1)
        except TimeoutError as exc:
            raise LocalProviderError("timeout", "provider_timeout") from exc
        except urllib_error.URLError as exc:
            reason = str(exc.reason if hasattr(exc, "reason") else exc)
            if "timed out" in reason.lower() or "timeout" in reason.lower():
                raise LocalProviderError("timeout", "provider_timeout") from exc
            raise LocalProviderError("http", f"http_error:{exc}") from exc
        except Exception as exc:
            msg = str(exc).lower()
            if "timed out" in msg or "timeout" in msg:
                raise LocalProviderError("timeout", "provider_timeout") from exc
            raise LocalProviderError("http", f"http_exception:{exc}") from exc
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
        req = urllib_request.Request(url, method="GET")
        try:
            with urllib_request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read(self.max_response_bytes + 1)
        except Exception as exc:
            raise LocalProviderError("health", f"health_unavailable:{exc}") from exc
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
        prompt_parts = []
        for m in request.messages:
            prompt_parts.append(f"{m.role.value if isinstance(m.role, MessageRole) else m.role}: {m.content}")
        if request.system:
            prompt_parts.insert(0, f"system: {request.system}")
        prompt = "\n".join(prompt_parts) if prompt_parts else ""
        return {
            "prompt": prompt,
            "role": request.role,
            "context": scrub_context_for_provider(request.context),
            "model": model_id,
            "response_format": request.response_format,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

    def parse_generate_response(self, obj: Dict[str, Any], *, provider_name: str) -> ModelResponse:
        text = obj.get("text")
        if not isinstance(text, str):
            raise LocalProviderError("malformed", "missing_text")
        meta = obj.get("meta") if isinstance(obj.get("meta"), dict) else {}
        structured = obj.get("structured") if isinstance(obj.get("structured"), dict) else None
        tool_calls = []
        raw_tools = obj.get("tool_calls")
        if isinstance(raw_tools, list):
            for item in raw_tools:
                if isinstance(item, dict) and item.get("name"):
                    tool_calls.append(
                        ToolCallProposal(
                            name=str(item.get("name")),
                            arguments=dict(item.get("arguments") or {})
                            if isinstance(item.get("arguments"), dict)
                            else {},
                            call_id=str(item.get("call_id") or ""),
                            confidence=float(item.get("confidence") or 0.5),
                            reason=str(item.get("reason") or ""),
                        )
                    )
        usage_raw = obj.get("usage") if isinstance(obj.get("usage"), dict) else {}
        usage = ModelUsage(
            prompt_tokens=int(usage_raw.get("prompt_tokens") or 0),
            completion_tokens=int(usage_raw.get("completion_tokens") or 0),
            total_tokens=int(usage_raw.get("total_tokens") or 0),
            latency_ms=float(usage_raw.get("latency_ms") or 0.0),
        )
        return ModelResponse(
            text=text,
            provider=provider_name,
            tool_calls=tool_calls,
            structured=structured,
            usage=usage,
            finish_reason=str(obj.get("finish_reason") or "stop"),
            healthy=True,
            meta={**meta, "engine": provider_name, "local_open_weight": True},
        )


class LocalOpenWeightProvider:
    """
    Canonical ModelProvider for optional local open-weight inference.

    Activation requires SSN_MODEL_PROVIDER=local (and a configured endpoint).
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
    ) -> None:
        self.model_id = resolve_model_id(model_id)
        self._allow_remote = allow_remote_endpoints() if allow_remote is None else bool(allow_remote)
        self._timeout_s = float(timeout_s) if timeout_s is not None else _parse_timeout()
        self._max_bytes = int(max_response_bytes) if max_response_bytes is not None else _parse_max_bytes()
        raw_endpoint = resolve_endpoint(endpoint)
        self._endpoint = ""
        self._config_error: Optional[str] = None
        try:
            if raw_endpoint:
                self._endpoint = validate_endpoint_url(raw_endpoint, allow_remote=self._allow_remote)
        except LocalProviderError as exc:
            self._config_error = f"{exc.category}:{exc}"
        self.transport = transport or (
            LocalHttpTransport(
                self._endpoint,
                timeout_s=self._timeout_s,
                max_response_bytes=self._max_bytes,
            )
            if self._endpoint
            else None
        )

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            chat=True,
            streaming=False,
            tools=True,
            structured_json=True,
            multimodal=False,
            context_window=4096,
            provider_name=self.name,
            metadata={
                "model_id": self.model_id,
                "local": True,
                "trained_siona_native": False,
                "open_weight": True,
                "simulated": False,
                "optional": True,
            },
        )

    def health(self) -> Dict[str, Any]:
        if self._config_error:
            return {"ok": False, "error": self._config_error, "provider": self.name}
        if not self.transport:
            return {"ok": False, "error": "endpoint_unconfigured", "provider": self.name}
        try:
            obj = self.transport.get_json(self.transport.health_url())
            return {
                "ok": bool(obj.get("ok", True)),
                "provider": self.name,
                "model_id": self.model_id,
                "endpoint_loopback": True,
                "raw": {k: obj.get(k) for k in ("ok", "service") if k in obj},
            }
        except LocalProviderError as exc:
            return {"ok": False, "error": f"{exc.category}:{exc}", "provider": self.name}

    def generate(self, request: ModelRequest) -> ModelResponse:
        t0 = time.time()
        if self._config_error or not self.transport:
            return ModelResponse(
                text="",
                provider=self.name,
                healthy=False,
                finish_reason="error",
                meta={
                    "error": self._config_error or "endpoint_unconfigured",
                    "model_id": self.model_id,
                    "local_open_weight": True,
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
            payload = self.transport.build_generate_payload(request, model_id=self.model_id)
            obj = self.transport.post_json(self._endpoint, payload)
            resp = self.transport.parse_generate_response(obj, provider_name=self.name)
            latency = max(0.0, (time.time() - t0) * 1000.0)
            usage = ModelUsage(
                prompt_tokens=resp.usage.prompt_tokens,
                completion_tokens=resp.usage.completion_tokens,
                total_tokens=resp.usage.total_tokens,
                latency_ms=latency or resp.usage.latency_ms,
            )
            meta = dict(resp.meta)
            meta["model_id"] = self.model_id
            meta["latency_ms"] = latency
            # Tool proposals only — never execute
            for tc in resp.tool_calls:
                if isinstance(tc, ToolCallProposal):
                    pass
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
                },
            )


def build_local_provider_from_env() -> Optional[LocalOpenWeightProvider]:
    if not local_provider_enabled():
        return None
    return LocalOpenWeightProvider()
