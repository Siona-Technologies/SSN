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

# Local provider / registry are imported lazily via __getattr__ to avoid a
# circular import: local_provider → integration.redaction → facade → loop → here.


def __getattr__(name: str):
    if name in {
        "LocalOpenWeightProvider",
        "build_local_provider_from_env",
        "local_provider_enabled",
        "local_provider_env_active",
    }:
        from ssn.cognition.model_gateway import local_provider as _lp

        mapping = {
            "LocalOpenWeightProvider": _lp.LocalOpenWeightProvider,
            "build_local_provider_from_env": _lp.build_local_provider_from_env,
            "local_provider_enabled": _lp.local_provider_enabled,
            "local_provider_env_active": _lp.local_provider_env_active,
        }
        return mapping[name]
    if name in {
        "ModelRegistry",
        "ModelRegistryEntry",
        "load_registry",
        "mock_ci_registry_payload",
        "validate_entry_dict",
    }:
        from ssn.cognition.model_gateway import registry as _reg

        mapping = {
            "ModelRegistry": _reg.ModelRegistry,
            "ModelRegistryEntry": _reg.ModelRegistryEntry,
            "load_registry": _reg.load_registry,
            "mock_ci_registry_payload": _reg.mock_ci_registry_payload,
            "validate_entry_dict": _reg.validate_entry_dict,
        }
        return mapping[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
    "LocalOpenWeightProvider",
    "build_local_provider_from_env",
    "local_provider_enabled",
    "local_provider_env_active",
    "ModelRegistry",
    "ModelRegistryEntry",
    "load_registry",
    "mock_ci_registry_payload",
    "validate_entry_dict",
]
