"""
Model gateway with timeout, cancellation hooks, usage accounting, and fallback.

Timeout enforcement for synchronous providers uses a bounded shared thread pool.
Limitation: after a timeout, the underlying synchronous call may continue until
its transport terminates; we do not kill arbitrary threads mid-call.
"""

from __future__ import annotations

import concurrent.futures
import logging
import threading
import time
from typing import Any, Dict, Iterator, List, Optional, Sequence

from ssn.cognition.metrics import CognitionMetrics
from ssn.cognition.model_gateway.contracts import (
    ModelCapabilities,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    ModelUsage,
)
from ssn.cognition.model_gateway.deterministic import DeterministicModelProvider

logger = logging.getLogger(__name__)

# Bounded shared pool — avoid unbounded thread growth across gateways.
_PROVIDER_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix="siona-model-gw",
)
_EXECUTOR_LOCK = threading.Lock()


def _cancel_requested(request: ModelRequest) -> bool:
    token = request.cancel_token
    if token is None:
        return False
    if getattr(token, "cancelled", False):
        return True
    if callable(getattr(token, "is_cancelled", None)):
        try:
            return bool(token.is_cancelled())
        except Exception:
            return False
    return False


def _response_usable(resp: ModelResponse, request: ModelRequest) -> tuple[bool, str]:
    """
    Decide whether a provider response is usable or should fall through.
    """
    if resp is None:
        return False, "null_response"
    if not resp.healthy:
        return False, "unhealthy"
    if str(resp.finish_reason or "").lower() == "error":
        return False, "finish_reason_error"
    if resp.fallback_used and resp.fallback_reason:
        # Explicit stub/fallback from provider adapter — treat as unusable for gateway.
        return False, f"provider_fallback_stub:{resp.fallback_reason}"
    text = resp.text if isinstance(resp.text, str) else ""
    if request.response_format == "json":
        if not isinstance(resp.structured, dict):
            # Allow JSON string body without structured field only if parseable-looking.
            if not text.strip().startswith("{"):
                return False, "missing_structured_json"
    else:
        if not text.strip() and not resp.tool_calls:
            return False, "empty_content"
    return True, ""


class ModelGateway:
    """
    Vendor-neutral model entry point.

    - primary provider with ordered fallbacks
    - enforced timeouts for sync providers (bounded executor)
    - cancellation checks before/between attempts and during stream
    - usage accounting / health aggregation
    """

    def __init__(
        self,
        providers: Optional[Sequence[ModelProvider]] = None,
        *,
        metrics: Optional[CognitionMetrics] = None,
        name: str = "siona-model-gateway-v1",
        executor: Optional[concurrent.futures.Executor] = None,
    ) -> None:
        self.name = name
        self._providers: List[ModelProvider] = (
            list(providers) if providers else [DeterministicModelProvider()]
        )
        self.metrics = metrics or CognitionMetrics()
        self._executor = executor or _PROVIDER_EXECUTOR

    @property
    def providers(self) -> List[ModelProvider]:
        return list(self._providers)

    def capabilities(self) -> ModelCapabilities:
        if not self._providers:
            return ModelCapabilities(provider_name=self.name)
        return self._providers[0].capabilities()

    def health(self) -> Dict[str, Any]:
        reports = []
        for p in self._providers:
            try:
                reports.append(p.health())
            except Exception as exc:
                reports.append(
                    {"ok": False, "provider": getattr(p, "name", "?"), "error": str(exc)}
                )
        ok = any(bool(r.get("ok")) for r in reports) if reports else False
        return {"ok": ok, "gateway": self.name, "providers": reports}

    def _cancelled_response(self) -> ModelResponse:
        self.metrics.model_failures += 1
        return ModelResponse(
            text="",
            provider=self.name,
            finish_reason="cancelled",
            healthy=False,
            meta={"error": "cancelled"},
        )

    def _run_provider_sync(
        self,
        provider: ModelProvider,
        request: ModelRequest,
    ) -> ModelResponse:
        """
        Execute provider.generate with a timeout boundary.

        Limitation: on timeout the worker may still run until the underlying
        transport/call returns; we abandon waiting but do not forcibly kill it.
        """
        timeout_s = float(request.timeout_s or 0.0)
        if timeout_s <= 0:
            return provider.generate(request)

        future = self._executor.submit(provider.generate, request)
        try:
            return future.result(timeout=timeout_s)
        except concurrent.futures.TimeoutError as exc:
            self.metrics.model_timeouts += 1
            # Best-effort cancel; running threads cannot be interrupted safely.
            future.cancel()
            raise TimeoutError(
                f"provider_timeout:{getattr(provider, 'name', 'provider')}:{timeout_s}s"
            ) from exc

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Generate with provider fallback and timeout/cancel boundaries."""
        self.metrics.model_requests += 1
        errors: List[str] = []
        started = time.monotonic()

        if _cancel_requested(request):
            return self._cancelled_response()

        for idx, provider in enumerate(self._providers):
            if _cancel_requested(request):
                return self._cancelled_response()

            try:
                resp = self._run_provider_sync(provider, request)
            except TimeoutError as exc:
                errors.append(str(exc))
                logger.warning("model provider timeout: %s", exc)
                continue
            except Exception as exc:
                errors.append(f"{getattr(provider, 'name', 'provider')}: {exc}")
                logger.warning("model provider failed: %s", exc)
                continue

            usable, reason = _response_usable(resp, request)
            if not usable:
                errors.append(
                    f"{getattr(provider, 'name', 'provider')}: unusable:{reason}"
                )
                logger.warning(
                    "model provider response unusable (%s): %s",
                    getattr(provider, "name", "provider"),
                    reason,
                )
                continue

            elapsed_ms = (time.monotonic() - started) * 1000.0
            usage = resp.usage
            if usage.latency_ms <= 0:
                usage = ModelUsage(
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                    latency_ms=elapsed_ms,
                )
            self.metrics.model_tokens_in += usage.prompt_tokens
            self.metrics.model_tokens_out += usage.completion_tokens
            fallback_used = idx > 0
            if fallback_used:
                self.metrics.model_fallbacks += 1
            return ModelResponse(
                text=resp.text,
                provider=resp.provider or getattr(provider, "name", self.name),
                messages=list(resp.messages),
                tool_calls=list(resp.tool_calls),
                structured=resp.structured,
                usage=usage,
                finish_reason=resp.finish_reason,
                healthy=True,
                fallback_used=fallback_used,
                fallback_reason=("; ".join(errors) if fallback_used else ""),
                meta={
                    **dict(resp.meta),
                    "gateway": self.name,
                    "provider_index": idx,
                },
            )

        self.metrics.model_failures += 1
        return ModelResponse(
            text="[SIONA ModelGateway] all providers failed",
            provider=self.name,
            finish_reason="error",
            healthy=False,
            fallback_used=True,
            fallback_reason="; ".join(errors) or "no_providers",
            meta={"errors": errors, "gateway": self.name},
        )

    def stream(self, request: ModelRequest) -> Iterator[str]:
        """Stream from first usable streaming provider; check cancel between chunks."""
        if _cancel_requested(request):
            return
        for provider in self._providers:
            if _cancel_requested(request):
                return
            stream_fn = getattr(provider, "stream", None)
            if not callable(stream_fn):
                continue
            try:
                self.metrics.model_requests += 1
                for chunk in stream_fn(request):
                    if _cancel_requested(request):
                        return
                    yield chunk
                return
            except Exception as exc:
                logger.warning("stream provider failed: %s", exc)
                continue
        resp = self.complete(request)
        if resp.healthy and resp.text:
            yield resp.text

    @classmethod
    def for_tests(cls) -> "ModelGateway":
        return cls(providers=[DeterministicModelProvider()])
