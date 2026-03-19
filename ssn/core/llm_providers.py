from __future__ import annotations

"""
LLM provider abstraction for SIONA / SSN.

This keeps LanguageEngine and the rest of the brain architecture
independent from any specific model or serving stack.

V10 blueprint alignment:
- LocalLLMProvider (default, local-first, CPU-friendly)
- RemoteLLMProvider (optional HTTP/API client)
- FutureCustomProvider (owner-trained/distilled models)

Right now we only ship a minimal LocalDummyLLMProvider which preserves
the behavior of the original Phase 1 LanguageEngine. When you are ready
to plug in a real model, you swap this provider (or add new ones) while
keeping the LanguageEngine.process(...) contract stable.
"""

from dataclasses import dataclass
import json
import os
from typing import Any, Dict, Optional, Protocol
from urllib import error as urllib_error
from urllib import request as urllib_request


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    role: str = "GUEST"
    context: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class LLMResponse:
    text: str
    meta: Dict[str, Any]


class LLMProvider(Protocol):
    """
    Minimal provider interface.

    Implementations may call local models, HTTP servers, or any other
    backend, but must keep this contract stable so higher layers never
    depend on a specific vendor or library.
    """

    name: str

    def generate(self, request: LLMRequest) -> LLMResponse:
        ...


class LocalDummyLLMProvider:
    """
    Drop-in replacement for the original dummy LanguageEngine behavior.

    This is intentionally simple and deterministic so tests and existing
    behavior remain stable until a real model is wired in.
    """

    name = "ssn-local-dummy-llm-v1"

    def generate(self, request: LLMRequest) -> LLMResponse:
        prompt = request.prompt
        ctx = request.context or {}
        role = request.role or "GUEST"

        if role == "OWNER":
            text = (
                "[SSN → Samson]: I received your request and processed it "
                "using the Phase 1 language core.\n\n"
                f'Your message was: "{prompt}"\n\n'
                f"[Context used: {bool(ctx)}]"
            )
            meta = {
                "role": "OWNER",
                "used_context": bool(ctx),
                "engine": self.name,
            }
        else:
            text = f'[SSN → Guest]: I received your message: "{prompt}".'
            meta = {
                "role": "GUEST",
                "used_context": False,
                "engine": self.name,
            }

        return LLMResponse(text=text, meta=meta)


class HttpLLMProvider:
    """
    HTTP-based provider for local/remote inference servers.

    - Reads base URL from SSN_LLM_ENDPOINT (or constructor arg).
    - Sends JSON: {"prompt": ..., "role": ..., "context": {...}}.
    - Expects JSON: {"text": "...", "meta": {...}}.

    On any error or missing configuration, it falls back to a
    deterministic stub reply so callers never crash.
    """

    name = "ssn-http-llm-v1"

    def __init__(self, base_url: Optional[str] = None) -> None:
        env_url = os.getenv("SSN_LLM_ENDPOINT")
        self.base_url = (base_url or env_url or "").strip()

    def _stub(self, request: LLMRequest, reason: str) -> LLMResponse:
        prompt = request.prompt
        role = request.role or "GUEST"
        ctx = request.context or {}
        endpoint = self.base_url or "<unset>"

        text = (
            "[SSN HTTP LLM Stub]\n"
            f"Endpoint: {endpoint}\n"
            f"Role: {role}\n"
            f"Prompt: {prompt}\n"
            f"Context keys: {sorted(list(ctx.keys())) if isinstance(ctx, dict) else []}\n\n"
            f"NOTE: HttpLLMProvider is running in stub/fallback mode: {reason}"
        )

        meta = {
            "role": role,
            "used_context": bool(ctx),
            "engine": self.name,
            "endpoint": endpoint,
            "fallback_reason": reason,
        }
        return LLMResponse(text=text, meta=meta)

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.base_url:
            return self._stub(request, "no endpoint configured (SSN_LLM_ENDPOINT unset)")

        payload = {
            "prompt": request.prompt,
            "role": request.role or "GUEST",
            "context": request.context or {},
        }

        try:
            data = json.dumps(payload).encode("utf-8")
        except Exception as e:
            return self._stub(request, f"json_encoding_error: {e}")

        req = urllib_request.Request(
            self.base_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib_request.urlopen(req, timeout=20.0) as resp:
                raw = resp.read()
        except urllib_error.URLError as e:
            return self._stub(request, f"http_error: {e}")
        except Exception as e:
            return self._stub(request, f"http_exception: {e}")

        try:
            obj = json.loads(raw.decode("utf-8", errors="replace"))
        except Exception as e:
            return self._stub(request, f"response_json_error: {e}")

        if not isinstance(obj, dict):
            return self._stub(request, "response_not_dict")

        text = obj.get("text")
        meta = obj.get("meta")

        if not isinstance(text, str):
            return self._stub(request, "response_missing_text")
        if not isinstance(meta, dict):
            meta = {}

        meta.setdefault("engine", self.name)
        meta.setdefault("role", request.role or "GUEST")
        meta.setdefault("used_context", bool(request.context))
        meta.setdefault("endpoint", self.base_url)

        return LLMResponse(text=text, meta=meta)


def get_default_provider_from_env() -> LLMProvider:
    """
    Select an LLMProvider based on environment configuration.

    Env keys:
      - SSN_LLM_PROVIDER:
          "dummy"  (default)  -> LocalDummyLLMProvider
          "http"             -> HttpLLMProvider (stub, local/remote URL)
      - SSN_LLM_ENDPOINT:
          base URL for HttpLLMProvider (e.g., http://localhost:8000/generate)
    """

    name = (os.getenv("SSN_LLM_PROVIDER") or "dummy").strip().lower()

    if name == "http":
        return HttpLLMProvider()

    # Fallback / default: local dummy implementation
    return LocalDummyLLMProvider()

