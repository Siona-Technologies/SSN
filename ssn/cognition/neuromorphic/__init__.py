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
from ssn.cognition.neuromorphic.learned_artifact import (
    LearnedNeuromorphicArtifactError,
    load_learned_artifact,
)
from ssn.cognition.neuromorphic.learned_provider import (
    LearnedNeuromorphicInputError,
    LearnedTemporalSalienceProvider,
    build_learned_temporal_salience_provider,
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
    "LearnedNeuromorphicArtifactError",
    "LearnedNeuromorphicInputError",
    "LearnedTemporalSalienceProvider",
    "build_learned_temporal_salience_provider",
    "load_learned_artifact",
]
