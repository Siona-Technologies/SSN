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
    Preserves LocalDummyLLMProvider / HttpLLMProvider behaviour.
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
        prompt = request.flat_prompt() if len(request.messages) != 1 else request.messages[0].content
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
        return ModelResponse(
            text=legacy_resp.text,
            provider=self.name,
            messages=[ModelMessage(role=MessageRole.ASSISTANT, content=legacy_resp.text)],
            usage=ModelUsage(),
            finish_reason="stop",
            healthy=True,
            fallback_used="fallback_reason" in meta,
            fallback_reason=str(meta.get("fallback_reason") or ""),
            meta={
                **meta,
                "engine": meta.get("engine", self.name),
                "role": meta.get("role", request.role),
                "used_context": bool(meta.get("used_context", bool(request.context))),
            },
        )


class ModelGatewayAsLLMProvider:
    """
    Exposes a ModelGateway (or any ModelProvider) as a legacy LLMProvider
    so LanguageEngine.process(...) keeps working unchanged.
    """

    def __init__(self, provider: Any, *, name: Optional[str] = None) -> None:
        self._provider = provider
        self.name = name or getattr(provider, "name", "model-gateway-llm-adapter")

    def generate(self, request: LLMRequest) -> LLMResponse:
        model_req = ModelRequest.from_prompt(
            request.prompt,
            role=request.role or "GUEST",
            context=request.context,
        )
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
        }
        return LLMResponse(text=resp.text, meta=meta)


def wrap_default_legacy_providers() -> Dict[str, LegacyLLMProviderAdapter]:
    """Factory for common legacy adapters (dummy + http)."""
    return {
        "dummy": LegacyLLMProviderAdapter(LocalDummyLLMProvider()),
        "http": LegacyLLMProviderAdapter(HttpLLMProvider()),
    }
