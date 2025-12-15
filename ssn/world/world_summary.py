# ssn/world/world_summary.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class WorldSummaryConfig:
    """
    Bounds for deterministic world summarization.
    """
    max_entities: int = 6
    max_events: int = 6
    max_attr_keys: int = 4
    max_chars: int = 600


class WorldSummaryNormalizer:
    """
    Phase 5.8 — World Summary Normalizer

    Converts the structured world context (from WorldContextProvider) into a compact,
    bounded, deterministic text summary suitable for stable cognition conditioning.
    """

    def __init__(self, config: Optional[WorldSummaryConfig] = None):
        self.config = config or WorldSummaryConfig()
        if self.config.max_entities <= 0:
            raise ValueError("max_entities must be > 0")
        if self.config.max_events < 0:
            raise ValueError("max_events must be >= 0")
        if self.config.max_attr_keys <= 0:
            raise ValueError("max_attr_keys must be > 0")
        if self.config.max_chars <= 40:
            raise ValueError("max_chars too small")

    def summarize(self, world: Dict[str, Any]) -> str:
        if not isinstance(world, dict):
            return "World: unavailable (invalid type)."

        available = world.get("available")
        if available is False:
            reason = world.get("reason", "unknown")
            return f"World: unavailable ({reason})."

        entities = world.get("entities", [])
        events = world.get("events", [])

        if not isinstance(entities, list):
            entities = []
        if not isinstance(events, list):
            events = []

        # Entities: take the first N (expected to be already recency-sorted)
        entities = entities[: int(self.config.max_entities)]

        # Events: take the MOST RECENT N
        if self.config.max_events > 0:
            events = events[-int(self.config.max_events) :]
        else:
            events = []

        ent_bits: List[str] = []
        for e in entities:
            if not isinstance(e, dict):
                continue

            eid = e.get("id", "?")
            ety = e.get("entity", "unknown")
            st = e.get("status", "unknown")
            conf = e.get("confidence", None)

            attrs = e.get("attributes", {})
            attr_txt = ""
            if isinstance(attrs, dict) and attrs:
                keys = sorted(attrs.keys(), key=lambda x: str(x))[: int(self.config.max_attr_keys)]
                kvs = [f"{k}={attrs.get(k)}" for k in keys]
                if len(attrs.keys()) > int(self.config.max_attr_keys):
                    kvs.append("…")
                attr_txt = " [" + ", ".join(kvs) + "]"

            if isinstance(conf, (int, float)):
                ent_bits.append(f"{eid}:{ety}({st},c={round(float(conf), 2)}){attr_txt}")
            else:
                ent_bits.append(f"{eid}:{ety}({st}){attr_txt}")

        ev_bits: List[str] = []
        for ev in events:
            if not isinstance(ev, dict):
                continue
            t = ev.get("type", "event")
            ts = ev.get("ts", None)
            c = ev.get("confidence", None)

            if isinstance(ts, (int, float)) and isinstance(c, (int, float)):
                ev_bits.append(f"{t}@{round(float(ts), 3)}(c={round(float(c), 2)})")
            elif isinstance(ts, (int, float)):
                ev_bits.append(f"{t}@{round(float(ts), 3)}")
            else:
                ev_bits.append(str(t))

        ent_count = world.get("entity_count", len(ent_bits))
        try:
            ent_count = int(ent_count)
        except Exception:
            ent_count = len(ent_bits)

        parts: List[str] = []
        parts.append(f"World: entities={ent_count}")
        parts.append("Top entities: " + (", ".join(ent_bits) if ent_bits else "none"))
        if self.config.max_events > 0:
            parts.append("Recent events: " + (", ".join(ev_bits) if ev_bits else "none"))

        s = " | ".join(parts)

        # Hard bound
        if len(s) > int(self.config.max_chars):
            s = s[: int(self.config.max_chars) - 1] + "…"

        return s
