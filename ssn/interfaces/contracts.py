# ssn/interfaces/contracts.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ErrorInfo:
    code: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_any(err: Any, *, default_code: str = "ERROR") -> "ErrorInfo":
        if isinstance(err, ErrorInfo):
            return err

        if isinstance(err, dict):
            code = err.get("code") or default_code
            msg = err.get("message") or str(err)
            det = err.get("details") if isinstance(err.get("details"), dict) else {}
            return ErrorInfo(code=str(code), message=str(msg), details=dict(det))

        if isinstance(err, BaseException):
            return ErrorInfo(code=default_code, message=str(err), details={"type": err.__class__.__name__})

        return ErrorInfo(code=default_code, message=str(err), details={})

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": dict(self.details or {})}


@dataclass(frozen=True)
class InterfaceRequest:
    """
    Stable internal interface contract (Front Door Gateway).
    NOTE: role is a *requested role*. Actual role must be resolved by identity.
    """
    action: str

    # Caller-provided (hint only; do not trust)
    role: str = "GUEST"  # OWNER/GUEST

    # Primary payload
    user_input: Any = None
    context: Optional[Dict[str, Any]] = None

    # Stable envelope fields (used for idempotency + tracing)
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    turn_id: Optional[str] = None

    # Control flags (gateway-level)
    confirm: bool = False
    offline: bool = False
    strict: bool = False
    degraded: bool = False
    allow_tools: bool = True
    allow_research: bool = True
    allow_degraded: bool = False
    force_research: bool = False

    # Extra metadata (safe; never include secrets)
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "action", str(self.action or ""))
        except Exception:
            pass

        # Normalize requested role (hint only)
        try:
            r = str(self.role or "GUEST").upper().strip()
            if r not in ("OWNER", "GUEST"):
                r = "GUEST"
            object.__setattr__(self, "role", r)
        except Exception:
            pass

        # Defensive: ensure context is dict or None
        try:
            if self.context is not None and not isinstance(self.context, dict):
                object.__setattr__(self, "context", None)
        except Exception:
            pass


@dataclass(frozen=True)
class InterfaceResponse:
    """
    Stable internal response contract.
    Convention: data should include (when applicable):
      - answer: str
      - citations: list[dict]
      - sources: list[dict]
      - used_tools: list[str]
      - session_state: dict
      - approval_request: dict (if needs approval)
      - note: str
    """
    ok: bool
    action: str
    role: str  # RESOLVED role (OWNER/GUEST)
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[ErrorInfo] = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "action", str(self.action or ""))
        except Exception:
            pass

        try:
            r = str(self.role or "GUEST").upper().strip()
            if r not in ("OWNER", "GUEST"):
                r = "GUEST"
            object.__setattr__(self, "role", r)
        except Exception:
            pass

        try:
            if not isinstance(self.data, dict):
                object.__setattr__(self, "data", {})
        except Exception:
            pass

        if self.error is not None and not isinstance(self.error, ErrorInfo):
            try:
                object.__setattr__(self, "error", ErrorInfo.from_any(self.error, default_code="RUNTIME_ERROR"))
            except Exception:
                object.__setattr__(
                    self, "error", ErrorInfo(code="RUNTIME_ERROR", message="Unknown error", details={})
                )
