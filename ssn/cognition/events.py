"""
Typed cognitive event contract for SIONA.

Designed for local in-process use now, with fields that support a future
transport adapter (without requiring Kafka/RabbitMQ in this phase).
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import IntEnum
from typing import Any, Dict, Mapping, Optional


# Soft bound on serialized payload size (bytes of JSON). Oversized
# nested structures are truncated rather than accepted unbounded.
DEFAULT_MAX_PAYLOAD_BYTES = 64_000
DEFAULT_MAX_METADATA_KEYS = 64


class EventPriority(IntEnum):
    """Higher numeric value = higher urgency for arbitration."""

    BACKGROUND = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class PrivacyClass(str):
    """Privacy classification string constants (stable for serialization)."""

    PUBLIC = "public"
    INTERNAL = "internal"
    PERSONAL = "personal"
    SENSITIVE = "sensitive"
    OWNER_ONLY = "owner_only"


def _monotonic() -> float:
    return float(time.monotonic())


def _wall_time() -> float:
    return float(time.time())


def _new_id() -> str:
    return str(uuid.uuid4())


def _clip01(x: float) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    if v != v:  # NaN
        return 0.0
    return max(0.0, min(1.0, v))


def _bound_mapping(
    data: Optional[Mapping[str, Any]],
    *,
    max_keys: int,
    max_bytes: int,
    label: str,
) -> Dict[str, Any]:
    """Return a JSON-safe, size-bounded dict copy."""
    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise TypeError(f"{label} must be a mapping")

    out: Dict[str, Any] = {}
    for i, (k, v) in enumerate(data.items()):
        if i >= max_keys:
            out["__truncated__"] = True
            out["__truncated_keys__"] = len(data) - max_keys
            break
        key = str(k)[:128]
        out[key] = v

    try:
        raw = json.dumps(out, sort_keys=True, default=str, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} is not JSON-serializable: {exc}") from exc

    if len(raw.encode("utf-8")) > max_bytes:
        # Keep a truncated string representation rather than unbounded data.
        truncated = {
            "__truncated__": True,
            "__original_bytes__": len(raw.encode("utf-8")),
            "__preview__": raw[:512],
        }
        return truncated
    return out


@dataclass(frozen=True)
class CognitiveEvent:
    """
    Canonical cognitive event.

    Compatible with future sensor events and distributed transport:
    identity, provenance, privacy, TTL, and correlation fields are first-class.
    """

    event_type: str
    source: str
    payload: Dict[str, Any] = field(default_factory=dict)

    event_id: str = field(default_factory=_new_id)
    timestamp: float = field(default_factory=_wall_time)
    monotonic_timestamp: float = field(default_factory=_monotonic)

    priority: EventPriority = EventPriority.NORMAL
    confidence: float = 1.0

    trace_id: str = ""
    correlation_id: str = ""
    tenant_id: str = "default"
    session_id: str = ""

    privacy_class: str = PrivacyClass.INTERNAL
    ttl_ms: Optional[int] = None
    requires_attention: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.event_type, str) or not self.event_type.strip():
            raise ValueError("event_type must be a non-empty string")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("source must be a non-empty string")

        object.__setattr__(self, "confidence", _clip01(self.confidence))

        if isinstance(self.priority, int) and not isinstance(self.priority, EventPriority):
            object.__setattr__(self, "priority", EventPriority(int(self.priority)))

        if self.ttl_ms is not None:
            if not isinstance(self.ttl_ms, int) or self.ttl_ms < 0:
                raise ValueError("ttl_ms must be a non-negative int or None")

        bounded_payload = _bound_mapping(
            self.payload,
            max_keys=256,
            max_bytes=DEFAULT_MAX_PAYLOAD_BYTES,
            label="payload",
        )
        object.__setattr__(self, "payload", bounded_payload)

        bounded_meta = _bound_mapping(
            self.metadata,
            max_keys=DEFAULT_MAX_METADATA_KEYS,
            max_bytes=16_000,
            label="metadata",
        )
        object.__setattr__(self, "metadata", bounded_meta)

        if not self.trace_id:
            object.__setattr__(self, "trace_id", self.event_id)
        if not self.correlation_id:
            object.__setattr__(self, "correlation_id", self.trace_id)

    def is_expired(self, *, now_mono: Optional[float] = None) -> bool:
        if self.ttl_ms is None:
            return False
        now = _monotonic() if now_mono is None else float(now_mono)
        age_ms = (now - self.monotonic_timestamp) * 1000.0
        return age_ms > float(self.ttl_ms)

    def age_ms(self, *, now_mono: Optional[float] = None) -> float:
        now = _monotonic() if now_mono is None else float(now_mono)
        return max(0.0, (now - self.monotonic_timestamp) * 1000.0)

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization (sorted keys via json helper)."""
        d = asdict(self)
        d["priority"] = int(self.priority)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False, default=str)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CognitiveEvent":
        if not isinstance(data, Mapping):
            raise TypeError("from_dict expects a mapping")
        priority = data.get("priority", EventPriority.NORMAL)
        if isinstance(priority, EventPriority):
            pri = priority
        else:
            pri = EventPriority(int(priority))
        return cls(
            event_type=str(data["event_type"]),
            source=str(data["source"]),
            payload=dict(data.get("payload") or {}),
            event_id=str(data.get("event_id") or _new_id()),
            timestamp=float(data.get("timestamp") or _wall_time()),
            monotonic_timestamp=float(data.get("monotonic_timestamp") or _monotonic()),
            priority=pri,
            confidence=float(data.get("confidence", 1.0)),
            trace_id=str(data.get("trace_id") or ""),
            correlation_id=str(data.get("correlation_id") or ""),
            tenant_id=str(data.get("tenant_id") or "default"),
            session_id=str(data.get("session_id") or ""),
            privacy_class=str(data.get("privacy_class") or PrivacyClass.INTERNAL),
            ttl_ms=data.get("ttl_ms"),
            requires_attention=bool(data.get("requires_attention", False)),
            metadata=dict(data.get("metadata") or {}),
        )

    @classmethod
    def text_input(
        cls,
        text: str,
        *,
        source: str = "user.text",
        role: str = "GUEST",
        session_id: str = "",
        tenant_id: str = "default",
        priority: EventPriority = EventPriority.NORMAL,
        **kwargs: Any,
    ) -> "CognitiveEvent":
        return cls(
            event_type="input.text",
            source=source,
            payload={"text": str(text)[:8000], "role": role},
            session_id=session_id,
            tenant_id=tenant_id,
            priority=priority,
            requires_attention=True,
            **kwargs,
        )
