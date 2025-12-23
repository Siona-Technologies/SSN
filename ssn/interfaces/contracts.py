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
        """
        Normalize common error shapes into ErrorInfo.
        Accepts:
          - ErrorInfo
          - dict with {code, message, details?}
          - Exception / any object (stringified)
        """
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
    Stable internal interface contract (Phase 4.0).
    """
    action: str
    role: str = "GUEST"  # OWNER/GUEST
    user_input: Any = None
    context: Optional[Dict[str, Any]] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Normalize role/action defensively (production safety)
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

    def __post_init__(self) -> None:
        # Normalize role/action + coerce error into ErrorInfo
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

        if self.error is not None and not isinstance(self.error, ErrorInfo):
            try:
                object.__setattr__(self, "error", ErrorInfo.from_any(self.error, default_code="RUNTIME_ERROR"))
            except Exception:
                # If coercion fails, drop error rather than breaking response construction
                object.__setattr__(self, "error", ErrorInfo(code="RUNTIME_ERROR", message="Unknown error", details={}))
