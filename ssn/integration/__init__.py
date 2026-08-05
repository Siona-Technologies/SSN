"""
SIONA Phase 2 runtime integration — cognitive observation bridges.

Does not replace Orchestrator / Front Door / BrainRouter authority.
Does not alter owner-control semantics.
"""

from __future__ import annotations

from ssn.integration.runtime_modes import (
    RuntimeMode,
    get_runtime_mode,
    resolve_runtime_mode,
)
from ssn.integration.trace_context import TraceContext
from ssn.integration.facade import IntegrationFacade

__all__ = [
    "RuntimeMode",
    "get_runtime_mode",
    "resolve_runtime_mode",
    "TraceContext",
    "IntegrationFacade",
]
