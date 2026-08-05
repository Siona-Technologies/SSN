"""SIONA model gateway package."""

from __future__ import annotations

from ssn.cognition.model_gateway.contracts import (
    MessageRole,
    ModelCapabilities,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelUsage,
    MultimodalRef,
    ToolCallProposal,
)
from ssn.cognition.model_gateway.deterministic import (
    DeterministicModelProvider,
    FailingModelProvider,
)
from ssn.cognition.model_gateway.adapters import (
    LegacyLLMProviderAdapter,
    ModelGatewayAsLLMProvider,
)
from ssn.cognition.model_gateway.gateway import ModelGateway

__all__ = [
    "MessageRole",
    "ModelCapabilities",
    "ModelMessage",
    "ModelRequest",
    "ModelResponse",
    "ModelUsage",
    "MultimodalRef",
    "ToolCallProposal",
    "DeterministicModelProvider",
    "FailingModelProvider",
    "LegacyLLMProviderAdapter",
    "ModelGatewayAsLLMProvider",
    "ModelGateway",
]
