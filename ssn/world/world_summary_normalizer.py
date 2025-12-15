# ssn/world/world_summary_normalizer.py

from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple


def _safe_str(x: Any) -> str:
    try:
        s = str(x)
    except Exception:
        s = ""
    return s


def _clip01(x: Any) -> float:
    try:
        f = float(x)
    except Exception:
        return 0.0
    return 0.0 if f < 0.0 else (1.0 if f > 1.0 else f)


def _pick(d: Dict[str, Any], keys: List[str], default=None):
    for k in keys:
        if k in d:
            return d.get(k)
    return default


def normalize_world_context(
    world_snapshot: Dict[str, Any],
    *,
    max_entities: int = 5,
    max_events: int = 5,
    max_chars: int = 700,
) -> Dict[str, Any]:
    """
    Produce a bounded, low-noise world context payload suitable for LLM context injection.

    Returns:
      {
        "attached": bool,
        "ts": float,
        "summary": str,
        "top_entities": [str, ...],
        "recent_events": [str, ...],
        "stats": {...}
      }
    """
    if not isinstance(world_snapshot, dict):
        return {
            "attached": False,
            "ts": time.time(),
            "summary": "World: unavailable (invalid_snapshot).",
            "top_entities": [],
            "recent_events": [],
            "stats": {"entity_count": None, "events_count": None},
        }

    # Your handler currently wraps as: {"available": True, "ts":..., "entity_count":..., "entities":[...], "events":[...]}
    available = bool(world_snapshot.get("available", True))
    ents = world_snapshot.get("entities", [])
    evs = world_snapshot.get("events", [])

    if not available:
        reason = _safe_str(world_snapshot.get("reason", "unavailable"))
        return {
            "attached": False,
            "ts": float(world_snapshot.get("ts", time.time()) or time.time()),
            "summary": f"World: unavailable ({reason}).",
            "top_entities": [],
            "recent_events": [],
            "stats": {"entity_count": None, "events_count": None},
        }

    if not isinstance(ents, list):
        ents = []
    if not isinstance(evs, list):
        evs = []

    max_entities = int(max_entities or 0)
    max_events = int(max_events or 0)
    if max_entities < 0:
        max_entities = 0
    if max_events < 0:
        max_events = 0

    # Build entity briefs
    top_entities: List[str] = []
    for e in ents[:max_entities]:
        if not isinstance(e, dict):
            continue
        eid = _safe_str(_pick(e, ["id", "eid"], "entity:?"))
        et = _safe_str(_pick(e, ["entity", "type"], "unknown"))
        st = _safe_str(_pick(e, ["status"], "unknown"))
        c = _clip01(_pick(e, ["confidence", "conf"], 0.5))
        attrs = e.get("attributes", {})
        zone = _safe_str(attrs.get("zone")) if isinstance(attrs, dict) else ""
        extra = f" zone={zone}" if zone else ""
        top_entities.append(f"{eid}:{et}({st},c={c:.2f}){extra}")

    # Build event briefs
    recent_events: List[str] = []
    for ev in evs[-max_events:]:
        if not isinstance(ev, dict):
            continue
        t = _safe_str(_pick(ev, ["type"], "event"))
        ts = ev.get("ts", None)
        try:
            tsf = float(ts) if ts is not None else 0.0
        except Exception:
            tsf = 0.0
        c = _clip01(_pick(ev, ["confidence", "conf"], 0.5))
        recent_events.append(f"{t}@{tsf:.2f}(c={c:.2f})")

    entity_count = world_snapshot.get("entity_count", None)
    if not isinstance(entity_count, int):
        try:
            entity_count = int(entity_count)
        except Exception:
            entity_count = len(ents)

    stats = {
        "entity_count": entity_count,
        "events_count": len(evs),
    }

    ent_part = ", ".join(top_entities) if top_entities else "none"
    ev_part = ", ".join(recent_events) if recent_events else "none"
    summary = f"World: entities={entity_count} | Top: {ent_part} | Events: {ev_part}"

    # Hard cap the final summary
    if len(summary) > max_chars:
        summary = summary[: max_chars - 3] + "..."

    return {
        "attached": True,
        "ts": float(world_snapshot.get("ts", time.time()) or time.time()),
        "summary": summary,
        "top_entities": top_entities,
        "recent_events": recent_events,
        "stats": stats,
    }
