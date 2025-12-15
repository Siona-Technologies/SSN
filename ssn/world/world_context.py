# ssn/world/world_context.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class WorldContextConfig:
    """
    Bounds and redaction rules for injecting world state into cognition context.
    """
    max_entities: int = 8
    max_events: int = 8
    max_attr_keys: int = 10
    include_events: bool = True


class WorldContextProvider:
    """
    Phase 5.7 — World Context Provider

    Produces a bounded, redacted world snapshot suitable for use in LLM context.
    This avoids pushing raw sensor payloads or unbounded structures into cognition.

    Inputs:
      - world_model: should implement snapshot(include_events:bool, max_entities:int, max_events:int) -> dict
        (Older snapshot implementations that only accept max_events are supported via fallback.)

    Output:
      - dict safe for context["world"]
    """

    def __init__(self, config: Optional[WorldContextConfig] = None):
        self.config = config or WorldContextConfig()
        if self.config.max_entities <= 0:
            raise ValueError("max_entities must be > 0")
        if self.config.max_events < 0:
            raise ValueError("max_events must be >= 0")
        if self.config.max_attr_keys <= 0:
            raise ValueError("max_attr_keys must be > 0")

    def build(self, world_model: Any) -> Dict[str, Any]:
        # If no world model or no snapshot method, return minimal marker
        snap_fn = getattr(world_model, "snapshot", None)
        if not callable(snap_fn):
            return {"available": False, "reason": "world_model_missing_snapshot"}

        include_events = bool(self.config.include_events)
        max_entities = int(self.config.max_entities)
        max_events = int(self.config.max_events)

        # Prefer passing max_entities + max_events; fall back for older signatures
        try:
            raw = snap_fn(include_events=include_events, max_entities=max_entities, max_events=max_events)
        except TypeError:
            raw = snap_fn(include_events=include_events, max_events=max_events)

        if not isinstance(raw, dict):
            return {"available": False, "reason": "snapshot_not_dict"}

        entities = raw.get("entities", [])
        if not isinstance(entities, list):
            entities = []

        # Keep top N entities (WorldModel.snapshot() is expected to sort by recency)
        entities = entities[:max_entities]

        safe_entities: List[Dict[str, Any]] = []
        for e in entities:
            if not isinstance(e, dict):
                continue

            attrs = e.get("attributes", {})
            safe_attrs: Dict[str, Any] = {}
            if isinstance(attrs, dict):
                # stable + bounded attribute keys
                for i, k in enumerate(sorted(attrs.keys(), key=lambda x: str(x))):
                    if i >= int(self.config.max_attr_keys):
                        safe_attrs["…"] = True
                        break
                    safe_attrs[str(k)] = attrs.get(k)

            # Support both last_seen and last_seen_ts depending on the model
            last_seen = e.get("last_seen", e.get("last_seen_ts"))

            safe_entities.append(
                {
                    "id": e.get("id"),
                    "entity": e.get("entity"),
                    "status": e.get("status"),
                    "confidence": e.get("confidence"),
                    "last_seen": last_seen,
                    "attributes": safe_attrs,
                    "source": e.get("source"),
                }
            )

        safe: Dict[str, Any] = {
            "available": True,
            "ts": raw.get("ts"),
            "entity_count": int(raw.get("entity_count", len(safe_entities)) or len(safe_entities)),
            "entities": safe_entities,
        }

        if include_events:
            evs = raw.get("events", [])
            if not isinstance(evs, list):
                evs = []
            evs = evs[-max_events:] if max_events > 0 else []

            safe_events: List[Dict[str, Any]] = []
            for ev in evs:
                if not isinstance(ev, dict):
                    continue
                # Redact heavy/unknown payloads; keep only summary fields
                safe_events.append(
                    {
                        "type": ev.get("type"),
                        "ts": ev.get("ts"),
                        "confidence": ev.get("confidence"),
                        "source": ev.get("source"),
                        # keep tiny known keys if present
                        "id": ev.get("id", None),
                        "entity": ev.get("entity", None),
                        # do NOT include ev["payload"] (could be large)
                    }
                )

            safe["events"] = safe_events

        return safe
