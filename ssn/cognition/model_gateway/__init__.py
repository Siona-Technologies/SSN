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
    CancelToken,
    DeterministicModelProvider,
    FailingModelProvider,
    MalformedModelProvider,
    SlowModelProvider,
    UnhealthyModelProvider,
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
    "SlowModelProvider",
    "UnhealthyModelProvider",
    "MalformedModelProvider",
    "CancelToken",
    "LegacyLLMProviderAdapter",
    "ModelGatewayAsLLMProvider",
    "ModelGateway",
]
