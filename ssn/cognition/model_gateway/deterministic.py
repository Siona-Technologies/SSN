"""
Deterministic model providers for offline tests and local-first defaults.

These are NOT real intelligence — they enable stable contracts and CI.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterator, List, Optional

from ssn.cognition.model_gateway.contracts import (
    MessageRole,
    ModelCapabilities,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelUsage,
    ToolCallProposal,
)


class DeterministicModelProvider:
    """
    Offline-safe deterministic provider.

    Responses are derived from a stable hash of the request so tests
    can assert reproducibility without network access.
    """

    name = "siona-deterministic-model-v1"

    def __init__(self, *, prefix: str = "[SIONA Deterministic]") -> None:
        self.prefix = prefix
        self._requests = 0

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            chat=True,
            streaming=True,
            tools=True,
            structured_json=True,
            multimodal=False,
            context_window=8192,
            provider_name=self.name,
            metadata={"simulated": True, "intelligence": False},
        )

    def health(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "provider": self.name,
            "requests": self._requests,
            "simulated": True,
        }

    def _fingerprint(self, request: ModelRequest) -> str:
        blob = {
            "role": request.role,
            "system": request.system,
            "messages": [m.to_dict() for m in request.messages],
            "response_format": request.response_format,
            "tools": request.tools,
        }
        raw = json.dumps(blob, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def generate(self, request: ModelRequest) -> ModelResponse:
        self._requests += 1
        fp = self._fingerprint(request)
        user_text = ""
        for m in request.messages:
            if m.role == MessageRole.USER:
                user_text = m.content
                break
        if not user_text and request.messages:
            user_text = request.messages[-1].content

        if request.response_format == "json":
            structured = {
                "ok": True,
                "echo": user_text[:500],
                "fingerprint": fp,
                "role": request.role,
            }
            text = json.dumps(structured, sort_keys=True)
        else:
            structured = None
            text = (
                f"{self.prefix} role={request.role} fp={fp}\n"
                f'Echo: "{user_text[:500]}"'
            )

        tool_calls: List[ToolCallProposal] = []
        # Only propose a tool when tools are listed and the prompt asks for one.
        if request.tools and "tool:" in user_text.lower():
            tool_name = str(request.tools[0].get("name") or "unknown")
            tool_calls.append(
                ToolCallProposal(
                    name=tool_name,
                    arguments={"query": user_text[:200]},
                    call_id=f"call_{fp}",
                    confidence=0.4,
                    reason="deterministic_test_proposal",
                )
            )

        prompt_tokens = max(1, len(request.flat_prompt()) // 4)
        completion_tokens = max(1, len(text) // 4)

        return ModelResponse(
            text=text,
            provider=self.name,
            messages=[ModelMessage(role=MessageRole.ASSISTANT, content=text)],
            tool_calls=tool_calls,
            structured=structured,
            usage=ModelUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            finish_reason="stop",
            healthy=True,
            meta={
                "role": request.role,
                "used_context": bool(request.context),
                "engine": self.name,
                "fingerprint": fp,
                "simulated": True,
            },
        )

    def stream(self, request: ModelRequest) -> Iterator[str]:
        resp = self.generate(request)
        # Yield in small deterministic chunks
        chunk = 24
        text = resp.text
        for i in range(0, len(text), chunk):
            yield text[i : i + chunk]


class FailingModelProvider:
    """Provider that always fails — used to exercise gateway fallback."""

    name = "siona-failing-model-v1"

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(provider_name=self.name)

    def health(self) -> Dict[str, Any]:
        return {"ok": False, "provider": self.name, "error": "intentional_failure"}

    def generate(self, request: ModelRequest) -> ModelResponse:
        raise RuntimeError("intentional_provider_failure")
