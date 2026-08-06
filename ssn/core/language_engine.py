"""
SSN Language Engine (Phase 1 → V10)

Phase 1:
- simple simulated LLM brain for OWNER / GUEST.

V10 blueprint:
- LanguageEngine becomes a thin wrapper around a pluggable LLMProvider
  so that local / remote / future custom models can be swapped in
  without touching BrainRouter, FusionEngine, or tools.

Governed prompt-context (opt-in, SSN_GOVERNED_CONTEXT=1):
- Canonical insertion point is the pre-provider wrapper around LLMProvider.
- Governance runs before any provider / ModelGateway / LocalHttpTransport call.
- Disabled by default; legacy behaviour unchanged.
"""

from __future__ import annotations
from typing import Any, Dict, Optional

from ssn.core.llm_providers import (
    LLMProvider,
    LLMRequest,
    get_default_provider_from_env,
)
from ssn.governance.runtime_context import (
    GOVERNED_RESULT_META_KEY,
    GovernedContextLLMProvider,
)


def _wrap_provider(provider: LLMProvider) -> LLMProvider:
    if isinstance(provider, GovernedContextLLMProvider):
        return provider
    return GovernedContextLLMProvider(provider)


class LanguageEngine:
    """
    LLM facade used by BrainRouter and FusionEngine.

    External contract (stable):
      - process(text, context, role) -> dict with keys:
          reply, role, used_context, engine

    Internally this delegates to a governed LLMProvider wrapper, which can be
    swapped for a real local/remote model later. The local provider never makes
    governance decisions.
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        inner: LLMProvider = provider or get_default_provider_from_env()
        self._provider: LLMProvider = _wrap_provider(inner)

    @property
    def engine_name(self) -> str:
        return getattr(self._provider, "name", "ssn-llm-unknown")

    def process(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        role: str = "GUEST",
    ) -> Dict[str, Any]:
        """
        Universal method expected by BrainRouter/FusionEngine.
        Returns a structured response.
        """

        req = LLMRequest(prompt=text, role=role, context=context)
        resp = self._provider.generate(req)

        meta = resp.meta or {}
        result: Dict[str, Any] = {
            "reply": resp.text,
            "role": meta.get("role", role),
            "used_context": bool(meta.get("used_context", bool(context))),
            "engine": meta.get("engine", self.engine_name),
        }
        if GOVERNED_RESULT_META_KEY in meta:
            result["governed_context"] = meta[GOVERNED_RESULT_META_KEY]
        for key in (
            "governed_identity_guard_applied",
            "governed_identity_guard_accepted",
            "governed_identity_fallback_used",
            "governed_identity_preflight_blocked",
            "governed_identity_reason",
            "governed_identity_response_mode",
            "governed_identity_requested_count",
            "governed_identity_included_count",
            "governed_identity_structured_source",
            "governed_identity_model_inference_count",
            "structured_source",
            "model_structured_output_accepted",
        ):
            if key in meta:
                result[key] = meta[key]
        return result

    def generate_reply(
        self,
        *,
        prompt: str,
        role: str = "GUEST",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Convenience wrapper used in tests / scripts.

        Returns:
          {
            "text": <reply text>,
            "meta": {...}
          }
        """

        req = LLMRequest(prompt=prompt, role=role, context=context)
        resp = self._provider.generate(req)
        return {
            "text": resp.text,
            "meta": {
                **(resp.meta or {}),
                "engine": (resp.meta or {}).get("engine", self.engine_name),
            },
        }
