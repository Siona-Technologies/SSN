"""
Compatibility adapters between legacy LLMProvider and ModelGateway.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ssn.cognition.model_gateway.contracts import (
    MessageRole,
    ModelCapabilities,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelUsage,
)
from ssn.core.llm_providers import (
    HttpLLMProvider,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LocalDummyLLMProvider,
)


class LegacyLLMProviderAdapter:
    """
    Wraps an existing LLMProvider (flat prompt) as a ModelProvider.

    Standalone LocalDummyLLMProvider / HttpLLMProvider behaviour is preserved
    at the legacy layer. Inside the ModelGateway, HTTP stub/fallback responses
    are marked unhealthy so the gateway can fall through to the next provider.
    """

    def __init__(self, legacy: LLMProvider) -> None:
        self._legacy = legacy
        self.name = getattr(legacy, "name", "legacy-llm-adapter")

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            chat=True,
            streaming=False,
            tools=False,
            structured_json=False,
            multimodal=False,
            context_window=4096,
            provider_name=self.name,
            metadata={"adapter": "LegacyLLMProviderAdapter"},
        )

    def health(self) -> Dict[str, Any]:
        return {"ok": True, "provider": self.name, "adapter": True}

    def generate(self, request: ModelRequest) -> ModelResponse:
        if len(request.messages) == 1 and not request.system:
            prompt = request.messages[0].content
        else:
            prompt = request.flat_prompt()

        legacy_req = LLMRequest(
            prompt=prompt,
            role=request.role or "GUEST",
            context=request.context or None,
        )
        legacy_resp: LLMResponse = self._legacy.generate(legacy_req)
        meta = dict(legacy_resp.meta or {})
        fallback_reason = str(meta.get("fallback_reason") or "")
        is_stub = bool(fallback_reason) or bool(meta.get("fallback_used"))

        # Gateway semantics: stub/fallback is not a healthy real-model result.
        # Legacy providers themselves remain unchanged for direct callers.
        return ModelResponse(
            text=legacy_resp.text,
            provider=self.name,
            messages=[ModelMessage(role=MessageRole.ASSISTANT, content=legacy_resp.text)],
            usage=ModelUsage(),
            finish_reason="error" if is_stub else "stop",
            healthy=not is_stub,
            fallback_used=is_stub,
            fallback_reason=fallback_reason,
            meta={
                **meta,
                "engine": meta.get("engine", self.name),
                "role": meta.get("role", request.role),
                "used_context": bool(meta.get("used_context", bool(request.context))),
                "gateway_marks_stub_unhealthy": is_stub,
            },
        )

class ModelGatewayAsLLMProvider:
    """
    Exposes a ModelGateway (or any ModelProvider) as a legacy LLMProvider
    so LanguageEngine.process(...) keeps working unchanged.
    """

    def __init__(
        self,
        provider: Any,
        *,
        name: Optional[str] = None,
        default_timeout_s: Optional[float] = None,
    ) -> None:
        self._provider = provider
        self.name = name or getattr(provider, "name", "model-gateway-llm-adapter")
        if default_timeout_s is None:
            self._default_timeout_s = None
        else:
            from ssn.cognition.model_gateway.local_provider import normalize_gateway_timeout

            self._default_timeout_s = normalize_gateway_timeout(default_timeout_s)

    def generate(self, request: LLMRequest) -> LLMResponse:
        model_req = ModelRequest.from_prompt(
            request.prompt,
            role=request.role or "GUEST",
            context=request.context,
        )
        if self._default_timeout_s is not None:
            # Keep gateway outer bound slightly above HTTP transport timeout.
            model_req.timeout_s = max(0.2, float(self._default_timeout_s))
        # Prefer gateway.complete if available (fallback chain)
        if hasattr(self._provider, "complete"):
            resp: ModelResponse = self._provider.complete(model_req)
        else:
            resp = self._provider.generate(model_req)

        meta = {
            **dict(resp.meta),
            "role": resp.meta.get("role", request.role or "GUEST"),
            "used_context": bool(resp.meta.get("used_context", bool(request.context))),
            "engine": resp.meta.get("engine", resp.provider or self.name),
            "fallback_used": resp.fallback_used,
            "fallback_reason": resp.fallback_reason,
            "provider_tool_call_count": len(resp.tool_calls),
            "provider_tool_calls_present": bool(resp.tool_calls),
            "prompt_tokens": int(resp.usage.prompt_tokens),
            "completion_tokens": int(resp.usage.completion_tokens),
            "total_tokens": int(resp.usage.total_tokens),
            "structured_present": resp.structured is not None,
        }
        return LLMResponse(text=resp.text, meta=meta)


def wrap_default_legacy_providers() -> Dict[str, LegacyLLMProviderAdapter]:
    """Factory for common legacy adapters (dummy + http)."""
    return {
        "dummy": LegacyLLMProviderAdapter(LocalDummyLLMProvider()),
        "http": LegacyLLMProviderAdapter(HttpLLMProvider()),
    }
