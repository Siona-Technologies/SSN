"""Neuromorphic runtime abstraction package."""

from __future__ import annotations

from ssn.cognition.neuromorphic.contracts import (
    AnomalyOutput,
    NeuromorphicCapabilities,
    NeuromorphicEvent,
    NeuromorphicOutput,
    NeuromorphicState,
    SalienceOutput,
    SpikeBatch,
)
from ssn.cognition.neuromorphic.providers import (
    DeterministicNeuromorphicProvider,
    data_to_neuromorphic_event,
)
from ssn.cognition.neuromorphic.legacy_adapter import (
    LegacySNNEngineAdapter,
    NeuromorphicSNNFacade,
)

__all__ = [
    "AnomalyOutput",
    "NeuromorphicCapabilities",
    "NeuromorphicEvent",
    "NeuromorphicOutput",
    "NeuromorphicState",
    "SalienceOutput",
    "SpikeBatch",
    "DeterministicNeuromorphicProvider",
    "data_to_neuromorphic_event",
    "LegacySNNEngineAdapter",
    "NeuromorphicSNNFacade",
]
