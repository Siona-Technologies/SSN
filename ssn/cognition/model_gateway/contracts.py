"""
Production-oriented model gateway contracts.

Vendor-agnostic: OpenAI / Anthropic / Ollama / vLLM / llama.cpp remain adapters.
Preserves LanguageEngine.process(...) via LegacyLLMAdapter.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Protocol, Sequence


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True)
class ModelMessage:
    role: MessageRole
    content: str
    name: str = ""
    tool_call_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value if isinstance(self.role, MessageRole) else str(self.role),
            "content": self.content,
            "name": self.name,
            "tool_call_id": self.tool_call_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelMessage":
        role = data.get("role", "user")
        if isinstance(role, MessageRole):
            r = role
        else:
            r = MessageRole(str(role))
        return cls(
            role=r,
            content=str(data.get("content") or ""),
            name=str(data.get("name") or ""),
            tool_call_id=str(data.get("tool_call_id") or ""),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True)
class MultimodalRef:
    """Reference to multimodal content (not raw bytes by default)."""

    media_type: str  # image/audio/video/file
    uri: str = ""
    mime: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolCallProposal:
    """Model-proposed tool call — never executes directly."""

    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    call_id: str = ""
    confidence: float = 0.5
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "arguments": dict(self.arguments),
            "call_id": self.call_id,
            "confidence": float(self.confidence),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ModelUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens or (self.prompt_tokens + self.completion_tokens),
            "latency_ms": self.latency_ms,
        }


@dataclass(frozen=True)
class ModelCapabilities:
    chat: bool = True
    streaming: bool = False
    tools: bool = False
    structured_json: bool = False
    multimodal: bool = False
    context_window: int = 4096
    provider_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chat": self.chat,
            "streaming": self.streaming,
            "tools": self.tools,
            "structured_json": self.structured_json,
            "multimodal": self.multimodal,
            "context_window": self.context_window,
            "provider_name": self.provider_name,
            "metadata": dict(self.metadata),
        }


@dataclass
class ModelRequest:
    messages: List[ModelMessage]
    role: str = "GUEST"  # SIONA OWNER/GUEST role (orthogonal to message roles)
    system: str = ""
    temperature: float = 0.0
    max_tokens: int = 1024
    response_format: str = "text"  # text | json
    tools: List[Dict[str, Any]] = field(default_factory=list)
    multimodal: List[MultimodalRef] = field(default_factory=list)
    timeout_s: float = 30.0
    cancel_token: Optional[Any] = None
    trace_id: str = ""
    session_id: str = ""
    tenant_id: str = "default"
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def flat_prompt(self) -> str:
        """Compatibility helper for legacy flat-prompt providers."""
        parts: List[str] = []
        if self.system:
            parts.append(f"SYSTEM: {self.system}")
        for m in self.messages:
            parts.append(f"{m.role.value.upper()}: {m.content}")
        return "\n".join(parts)

    @classmethod
    def from_prompt(
        cls,
        prompt: str,
        *,
        role: str = "GUEST",
        context: Optional[Dict[str, Any]] = None,
        system: str = "",
    ) -> "ModelRequest":
        return cls(
            messages=[ModelMessage(role=MessageRole.USER, content=prompt)],
            role=role,
            system=system,
            context=dict(context or {}),
        )


@dataclass(frozen=True)
class ModelResponse:
    text: str
    provider: str
    messages: List[ModelMessage] = field(default_factory=list)
    tool_calls: List[ToolCallProposal] = field(default_factory=list)
    structured: Optional[Dict[str, Any]] = None
    usage: ModelUsage = field(default_factory=ModelUsage)
    finish_reason: str = "stop"
    healthy: bool = True
    fallback_used: bool = False
    fallback_reason: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "provider": self.provider,
            "messages": [m.to_dict() for m in self.messages],
            "tool_calls": [t.to_dict() for t in self.tool_calls],
            "structured": self.structured,
            "usage": self.usage.to_dict(),
            "finish_reason": self.finish_reason,
            "healthy": self.healthy,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "meta": dict(self.meta),
        }


class ModelProvider(Protocol):
    name: str

    def capabilities(self) -> ModelCapabilities:
        ...

    def health(self) -> Dict[str, Any]:
        ...

    def generate(self, request: ModelRequest) -> ModelResponse:
        ...


class StreamingModelProvider(Protocol):
    name: str

    def capabilities(self) -> ModelCapabilities:
        ...

    def health(self) -> Dict[str, Any]:
        ...

    def generate(self, request: ModelRequest) -> ModelResponse:
        ...

    def stream(self, request: ModelRequest) -> Iterator[str]:
        ...


class AsyncStreamingModelProvider(Protocol):
    name: str

    async def astream(self, request: ModelRequest) -> AsyncIterator[str]:
        ...
