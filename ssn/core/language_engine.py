"""
SSN Language Engine (Phase 1 → V10)

Phase 1:
- simple simulated LLM brain for OWNER / GUEST.

V10 blueprint:
- LanguageEngine becomes a thin wrapper around a pluggable LLMProvider
  so that local / remote / future custom models can be swapped in
  without touching BrainRouter, FusionEngine, or tools.
"""

from __future__ import annotations
from typing import Any, Dict, Optional

from ssn.core.llm_providers import (
    LLMProvider,
    LLMRequest,
    get_default_provider_from_env,
)


class LanguageEngine:
    """
    LLM facade used by BrainRouter and FusionEngine.

    External contract (stable):
      - process(text, context, role) -> dict with keys:
          reply, role, used_context, engine

    Internally this delegates to an LLMProvider, which can be swapped
    for a real local/remote model later.
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        # If a provider is passed explicitly, use it; otherwise select
        # based on environment (SSN_LLM_PROVIDER, SSN_LLM_ENDPOINT, etc.).
        self._provider: LLMProvider = provider or get_default_provider_from_env()

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
        return {
            "reply": resp.text,
            "role": meta.get("role", role),
            "used_context": bool(meta.get("used_context", bool(context))),
            "engine": meta.get("engine", self.engine_name),
        }

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
                **resp.meta,
                "engine": resp.meta.get("engine", self.engine_name),
            },
        }
