# ssn/interfaces/contracts.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ErrorInfo:
    code: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InterfaceRequest:
    """
    Stable internal interface contract (Phase 4.0).
    """
    action: str                      # e.g., "think", "explain_state", "summarize_memory", "suggest"
    role: str = "GUEST"              # OWNER/GUEST
    user_input: Any = None
    context: Optional[Dict[str, Any]] = None
    meta: Dict[str, Any] = field(default_factory=dict)   # optional: speaker_id, session_id, etc.


@dataclass(frozen=True)
class InterfaceResponse:
    """
    Stable internal response contract.
    """
    ok: bool
    action: str
    role: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[ErrorInfo] = None
