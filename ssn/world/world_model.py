# ssn/world/world_model.py

from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List


DEFAULT_WORLD_PATH = "ssn/data/world_model.json"


@dataclass
class WorldEntity:
    id: str
    entity: str
    status: str = "unknown"
    confidence: float = 0.5
    last_seen_ts: float = 0.0
    attributes: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"


@dataclass
class WorldEvent:
    type: str
    ts: float
    confidence: float = 0.5
    source: str = "unknown"
    details: Dict[str, Any] = field(default_factory=dict)


class WorldModel:
    """
    Phase 5.x — WorldModel (Persisted + Atomic)

    Keeps your existing behavior:
    - Stores entities + events (bounded retention)
    - apply_update/update/ingest/merge
    - snapshot(...) for interface handlers

    Adds:
    - Disk persistence (required for CLI, since each command is a new process)
      File: ssn/data/world_model.json
    - Atomic JSON writes to reduce corruption on abrupt shutdowns
    """

    MAX_ENTITIES = 500
    MAX_EVENTS = 2000

    def __init__(self, path: str = DEFAULT_WORLD_PATH):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

        self._entities: Dict[str, WorldEntity] = {}
        self._events: List[WorldEvent] = []
        self._ts: float = time.time()

        self._load()

    @staticmethod
    def _now() -> float:
        return time.time()

    @staticmethod
    def _clip01(x: float) -> float:
        try:
            xf = float(x)
        except Exception:
            return 0.0
        if xf < 0.0:
            return 0.0
        if xf > 1.0:
            return 1.0
        return xf

    # -----------------------------
    # Persistence (atomic)
    # -----------------------------
    @staticmethod
    def _atomic_write_json(path: str, data: Any) -> None:
        dir_name = os.path.dirname(path) or "."
        base_name = os.path.basename(path)

        fd = None
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(prefix=base_name + ".", suffix=".tmp", dir=dir_name)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_path, path)

            # POSIX directory fsync (best effort)
            try:
                dir_fd = os.open(dir_name, os.O_DIRECTORY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except Exception:
                pass

        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def _load(self) -> None:
        if not os.path.exists(self.path):
            self._save()  # create empty file
            return

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

        if not isinstance(data, dict):
            data = {}

        try:
            self._ts = float(data.get("ts", self._now()) or self._now())
        except Exception:
            self._ts = self._now()

        ents = data.get("entities", {})
        if isinstance(ents, dict):
            for eid, raw in ents.items():
                if not isinstance(raw, dict):
                    continue
                try:
                    self._entities[str(eid)] = WorldEntity(
                        id=str(eid),
                        entity=str(raw.get("entity", "unknown")),
                        status=str(raw.get("status", "unknown")),
                        confidence=self._clip01(raw.get("confidence", 0.5)),
                        last_seen_ts=float(raw.get("last_seen_ts", 0.0) or 0.0),
                        attributes=dict(raw.get("attributes", {}) or {}),
                        source=str(raw.get("source", "unknown")),
                    )
                except Exception:
                    continue

        evs = data.get("events", [])
        if isinstance(evs, list):
            for raw in evs:
                if not isinstance(raw, dict):
                    continue
                try:
                    tsf = float(raw.get("ts", self._now()) or self._now())
                except Exception:
                    tsf = self._now()

                self._events.append(
                    WorldEvent(
                        type=str(raw.get("type", "event")),
                        ts=tsf,
                        confidence=self._clip01(raw.get("confidence", 0.5)),
                        source=str(raw.get("source", "unknown")),
                        details=dict(raw.get("details", {}) or {}),
                    )
                )

        self._enforce_bounds()

    def _save(self) -> None:
        self._enforce_bounds()

        data = {
            "ts": float(self._ts),
            "entities": {
                eid: {
                    "entity": e.entity,
                    "status": e.status,
                    "confidence": float(e.confidence),
                    "last_seen_ts": float(e.last_seen_ts),
                    "attributes": dict(e.attributes),
                    "source": e.source,
                }
                for eid, e in self._entities.items()
            },
            "events": [
                {
                    "type": ev.type,
                    "ts": float(ev.ts),
                    "confidence": float(ev.confidence),
                    "source": ev.source,
                    "details": dict(ev.details),
                }
                for ev in self._events
            ],
        }

        self._atomic_write_json(self.path, data)

    def _enforce_bounds(self) -> None:
        # bounded entities (evict least-recently-seen)
        if len(self._entities) > self.MAX_ENTITIES:
            items = sorted(self._entities.items(), key=lambda kv: kv[1].last_seen_ts)
            for k, _ in items[: max(1, len(self._entities) - self.MAX_ENTITIES)]:
                self._entities.pop(k, None)

        # bounded events (keep most recent)
        if len(self._events) > self.MAX_EVENTS:
            self._events = self._events[-self.MAX_EVENTS :]

    # -----------------------------
    # Entity / event primitives
    # -----------------------------
    def upsert_entity(self, ent: Dict[str, Any]) -> None:
        if not isinstance(ent, dict):
            return

        eid = ent.get("id")
        etype = ent.get("entity") or ent.get("type")
        if not isinstance(eid, str) or not eid.strip():
            return
        if not isinstance(etype, str) or not etype.strip():
            etype = "unknown"

        now = self._now()
        status = ent.get("status", "unknown")
        conf = self._clip01(ent.get("confidence", 0.5))
        src = ent.get("source", "unknown")
        attrs = ent.get("attributes", {}) if isinstance(ent.get("attributes"), dict) else {}

        prev = self._entities.get(eid)
        if prev is None:
            self._entities[eid] = WorldEntity(
                id=eid,
                entity=str(etype),
                status=str(status),
                confidence=conf,
                last_seen_ts=now,
                attributes=dict(attrs),
                source=str(src),
            )
        else:
            prev.entity = str(etype or prev.entity)
            prev.status = str(status or prev.status)
            prev.confidence = max(prev.confidence, conf)
            prev.last_seen_ts = now
            prev.source = str(src or prev.source)
            prev.attributes.update(dict(attrs))

        self._ts = now
        self._save()

    def add_event(self, ev: Dict[str, Any]) -> None:
        if not isinstance(ev, dict):
            return

        etype = ev.get("type") or ev.get("sensor_type") or "event"
        ts = ev.get("ts", None)
        try:
            tsf = float(ts) if ts is not None else self._now()
        except Exception:
            tsf = self._now()

        conf = self._clip01(ev.get("confidence", 0.5))
        src = ev.get("source", "unknown")

        details = ev.get("details", {})
        if not isinstance(details, dict):
            details = {}

        self._events.append(
            WorldEvent(
                type=str(etype),
                ts=tsf,
                confidence=conf,
                source=str(src),
                details=dict(details),
            )
        )

        self._ts = self._now()
        self._save()

    # -----------------------------
    # Update packet entrypoints
    # -----------------------------
    def apply_update(self, update_packet: Dict[str, Any]) -> None:
        if not isinstance(update_packet, dict):
            return

        src = update_packet.get("source", "unknown")

        ents = update_packet.get("entities", [])
        if isinstance(ents, list):
            for ent in ents:
                if isinstance(ent, dict):
                    if "source" not in ent:
                        ent = dict(ent)
                        ent["source"] = src
                    self.upsert_entity(ent)

        evs = update_packet.get("events", [])
        if isinstance(evs, list):
            for ev in evs:
                if isinstance(ev, dict):
                    if "source" not in ev:
                        ev = dict(ev)
                        ev["source"] = src
                    self.add_event(ev)

        self._ts = self._now()
        self._save()

    # Compatibility aliases
    def update(self, update_packet: Dict[str, Any]) -> None:
        self.apply_update(update_packet)

    def ingest(self, update_packet: Dict[str, Any]) -> None:
        self.apply_update(update_packet)

    def merge(self, update_packet: Dict[str, Any]) -> None:
        self.apply_update(update_packet)

    # -----------------------------
    # Snapshot for interface output
    # -----------------------------
    def snapshot(self, *, include_events: bool = True, max_entities: int = 10, max_events: int = 20) -> Dict[str, Any]:
        max_entities = int(max_entities or 0)
        max_events = int(max_events or 0)
        if max_entities < 0:
            max_entities = 0
        if max_events < 0:
            max_events = 0

        ents = sorted(self._entities.values(), key=lambda e: e.last_seen_ts, reverse=True)
        ents = ents[:max_entities] if max_entities else []

        out_ents = [
            {
                "id": e.id,
                "entity": e.entity,
                "status": e.status,
                "confidence": float(e.confidence),
                "last_seen_ts": float(e.last_seen_ts),
                "attributes": dict(e.attributes),
                "source": e.source,
            }
            for e in ents
        ]

        out_events: List[Dict[str, Any]] = []
        if include_events and max_events:
            evs = self._events[-max_events:]
            out_events = [
                {
                    "type": ev.type,
                    "ts": float(ev.ts),
                    "confidence": float(ev.confidence),
                    "source": ev.source,
                    "details": dict(ev.details),
                }
                for ev in evs
            ]

        return {
            "ts": float(self._ts),
            "entity_count": len(self._entities),
            "entities": out_ents,
            "events": out_events,
        }
