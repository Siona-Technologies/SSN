"""
Runtime integration modes for Phase 2.

legacy (default): existing Orchestrator/BrainRouter/Front Door only.
shadow: same authoritative path + redacted cognitive observation (no duplicate model).
cognitive_experimental: opt-in cognitive loop (proposals only; still uses existing
identity/policy entry points when called through Front Door).
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Optional


class RuntimeMode(str, Enum):
    LEGACY = "legacy"
    SHADOW = "shadow"
    COGNITIVE_EXPERIMENTAL = "cognitive_experimental"


_VALID = {m.value for m in RuntimeMode}
ENV_KEY = "SSN_COGNITIVE_MODE"


def resolve_runtime_mode(value: Optional[str] = None) -> RuntimeMode:
    """
    Resolve mode from explicit value or env. Invalid → legacy (safe fallback).
    """
    raw = value if value is not None else os.getenv(ENV_KEY)
    if raw is None or str(raw).strip() == "":
        return RuntimeMode.LEGACY
    key = str(raw).strip().lower()
    # Accept common aliases
    aliases = {
        "experimental": RuntimeMode.COGNITIVE_EXPERIMENTAL.value,
        "cognitive": RuntimeMode.COGNITIVE_EXPERIMENTAL.value,
        "exp": RuntimeMode.COGNITIVE_EXPERIMENTAL.value,
    }
    key = aliases.get(key, key)
    if key not in _VALID:
        return RuntimeMode.LEGACY
    return RuntimeMode(key)


def get_runtime_mode() -> RuntimeMode:
    return resolve_runtime_mode(None)
