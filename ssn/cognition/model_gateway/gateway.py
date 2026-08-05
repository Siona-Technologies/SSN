"""
Model gateway with timeout, cancellation hooks, usage accounting, and fallback.
"""

from __future__ import annotations

import logging
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


class ModelGateway:
    """
    Vendor-neutral model entry point.

    - primary provider with ordered fallbacks
    - timeouts (best-effort for sync providers)
    - usage accounting
    - health aggregation
    - streaming when the selected provider supports it
    """

    def __init__(
        self,
        providers: Optional[Sequence[ModelProvider]] = None,
        *,
        metrics: Optional[CognitionMetrics] = None,
        name: str = "siona-model-gateway-v1",
    ) -> None:
        self.name = name
        self._providers: List[ModelProvider] = list(providers) if providers else [DeterministicModelProvider()]
        self.metrics = metrics or CognitionMetrics()

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
                reports.append({"ok": False, "provider": getattr(p, "name", "?"), "error": str(exc)})
        ok = any(bool(r.get("ok")) for r in reports) if reports else False
        return {"ok": ok, "gateway": self.name, "providers": reports}

    def complete(self, request: ModelRequest) -> ModelResponse:
        """Generate with provider fallback."""
        self.metrics.model_requests += 1
        errors: List[str] = []
        started = time.monotonic()

        # Cancellation hook (cooperative)
        if request.cancel_token is not None and getattr(request.cancel_token, "cancelled", False):
            self.metrics.model_failures += 1
            return ModelResponse(
                text="",
                provider=self.name,
                finish_reason="cancelled",
                healthy=False,
                meta={"error": "cancelled"},
            )

        for idx, provider in enumerate(self._providers):
            try:
                # Soft timeout: record intent; sync providers may ignore.
                resp = provider.generate(request)
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
                    healthy=resp.healthy,
                    fallback_used=fallback_used or resp.fallback_used,
                    fallback_reason=(
                        "; ".join(errors)
                        if fallback_used
                        else resp.fallback_reason
                    ),
                    meta={
                        **dict(resp.meta),
                        "gateway": self.name,
                        "provider_index": idx,
                    },
                )
            except Exception as exc:
                errors.append(f"{getattr(provider, 'name', 'provider')}: {exc}")
                logger.warning("model provider failed: %s", exc)
                continue

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
        """Stream from the first provider that supports stream(); else chunk complete()."""
        for provider in self._providers:
            stream_fn = getattr(provider, "stream", None)
            if callable(stream_fn):
                try:
                    self.metrics.model_requests += 1
                    yield from stream_fn(request)
                    return
                except Exception as exc:
                    logger.warning("stream provider failed: %s", exc)
                    continue
        resp = self.complete(request)
        yield resp.text

    @classmethod
    def for_tests(cls) -> "ModelGateway":
        return cls(providers=[DeterministicModelProvider()])
