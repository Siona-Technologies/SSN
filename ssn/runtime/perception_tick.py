# ssn/runtime/perception_tick.py

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional


class PerceptionTick:
    """
    Phase 6.0 — Perception Tick (manual, bounded)

    Goal:
      - Accept a small batch of sensor events (dicts)
      - Optionally route through PerceptionHub (if wired)
      - Update WorldModel (if wired)
      - Write a trace (if MemoryHub/Trace exists)

    This module performs NO external actions.
    """

    def __init__(
        self,
        *,
        world_model: Any = None,
        memory_hub: Any = None,
        perception_hub: Any = None,
        source: str = "sense_tick",
    ):
        self.world_model = world_model
        self.memory_hub = memory_hub
        self.perception_hub = perception_hub
        self.source = source

    # ---------------------------
    # Utilities (safe adapters)
    # ---------------------------
    @staticmethod
    def _now() -> float:
        return time.time()

    @staticmethod
    def _is_event(x: Any) -> bool:
        return isinstance(x, dict) and len(x) > 0

    @staticmethod
    def _getattr(obj: Any, name: str, default=None):
        try:
            return getattr(obj, name)
        except Exception:
            return default

    def _write_trace(self, payload: Dict[str, Any]) -> bool:
        """
        Best-effort trace write. Never raises.
        Tries common shapes:
          - memory_hub.trace_memory.add_trace(payload)
          - memory_hub.trace.add_trace(payload)
          - memory_hub.add_trace(payload)
          - memory_hub.write_trace(payload)
        """
        mh = self.memory_hub
        if mh is None:
            return False

        candidates = []

        tm = self._getattr(mh, "trace_memory", None)
        if tm is not None:
            candidates.extend(
                [
                    ("trace_memory.add_trace", self._getattr(tm, "add_trace", None)),
                    ("trace_memory.write_trace", self._getattr(tm, "write_trace", None)),
                    ("trace_memory.log", self._getattr(tm, "log", None)),
                ]
            )

        tr = self._getattr(mh, "trace", None)
        if tr is not None:
            candidates.extend(
                [
                    ("trace.add_trace", self._getattr(tr, "add_trace", None)),
                    ("trace.write_trace", self._getattr(tr, "write_trace", None)),
                    ("trace.log", self._getattr(tr, "log", None)),
                ]
            )

        candidates.extend(
            [
                ("memory_hub.add_trace", self._getattr(mh, "add_trace", None)),
                ("memory_hub.write_trace", self._getattr(mh, "write_trace", None)),
                ("memory_hub.log_trace", self._getattr(mh, "log_trace", None)),
            ]
        )

        for _, fn in candidates:
            if callable(fn):
                try:
                    fn(payload)
                    return True
                except Exception:
                    continue

        return False

    def _world_apply_update(self, update: Dict[str, Any]) -> bool:
        """
        Best-effort WorldModel update. Never raises.
        Tries common APIs:
          - world_model.apply_update(update)
          - world_model.update(update) / update(**update)
          - world_model.ingest(update)
          - world_model.merge(update)
        """
        wm = self.world_model
        if wm is None:
            return False

        for name in ("apply_update", "ingest", "merge"):
            fn = self._getattr(wm, name, None)
            if callable(fn):
                try:
                    fn(update)
                    return True
                except Exception:
                    pass

        fn = self._getattr(wm, "update", None)
        if callable(fn):
            try:
                fn(update)
                return True
            except TypeError:
                try:
                    fn(**update)
                    return True
                except Exception:
                    pass
            except Exception:
                pass

        # Fine-grained fallback if available
        add_event = self._getattr(wm, "add_event", None)
        upsert_entity = self._getattr(wm, "upsert_entity", None)
        if callable(add_event):
            try:
                for ev in update.get("events", []) or []:
                    add_event(ev)
            except Exception:
                pass
        if callable(upsert_entity):
            try:
                for ent in update.get("entities", []) or []:
                    upsert_entity(ent)
            except Exception:
                pass

        # If at least one of the above is present, consider "updated"
        return callable(add_event) or callable(upsert_entity)

    # ---------------------------
    # Public API
    # ---------------------------
    def run(
        self,
        events: Optional[List[Dict[str, Any]]] = None,
        *,
        max_events: int = 25,
        write_trace: bool = True,
        update_world: bool = True,
    ) -> Dict[str, Any]:
        """
        Runs one bounded perception tick.

        Returns:
          {
            "ok": True,
            "processed": int,
            "skipped": int,
            "world_updated": bool,
            "trace_written": bool,
            "ts": float,
            "note": str,
          }
        """
        ts = self._now()

        # Normalize events
        evs = [e for e in (events or []) if self._is_event(e)]
        if len(evs) > max_events:
            evs = evs[:max_events]

        processed = 0
        skipped = 0

        # Optionally pass through PerceptionHub if present
        hub = self.perception_hub
        hub_report: Dict[str, Any] = {}

        if hub is not None:
            # try common hub methods
            called = False
            for meth in ("process_batch", "process_events", "process", "ingest", "consume"):
                fn = self._getattr(hub, meth, None)
                if callable(fn):
                    try:
                        out = fn(evs)
                        if isinstance(out, dict):
                            hub_report = out
                        called = True
                        break
                    except Exception:
                        continue
            if called:
                # try read processed/skipped from report if present
                if isinstance(hub_report.get("processed"), int):
                    processed = int(hub_report["processed"])
                if isinstance(hub_report.get("skipped"), int):
                    skipped = int(hub_report["skipped"])

        # If no hub or hub didn’t report counts, do local counting
        if processed == 0 and skipped == 0:
            for e in evs:
                st = e.get("sensor_type") or e.get("type")
                if isinstance(st, str) and st.strip():
                    processed += 1
                else:
                    skipped += 1

        # Build a conservative update packet for WorldModel
        update_packet = {
            "type": "world_update",
            "ts": ts,
            "source": self.source,
            "entities": [],
            "events": [],
        }

        for e in evs:
            # If event already contains entity info, carry it
            if isinstance(e.get("entities"), list):
                update_packet["entities"].extend([x for x in e["entities"] if isinstance(x, dict)])
            if isinstance(e.get("entity"), dict):
                update_packet["entities"].append(e["entity"])

            # Record a small, redacted event object
            update_packet["events"].append(
                {
                    "type": str(e.get("type") or e.get("sensor_type") or "event"),
                    "ts": float(e.get("ts") or ts),
                    "confidence": float(e.get("confidence") or 0.5),
                    "source": self.source,
                }
            )

        world_updated = False
        if update_world and self.world_model is not None:
            world_updated = bool(self._world_apply_update(update_packet))

        trace_written = False
        if write_trace:
            trace_written = bool(
                self._write_trace(
                    {
                        "type": "sense_tick",
                        "ts": ts,
                        "source": self.source,
                        "event_count": len(evs),
                        "processed": processed,
                        "skipped": skipped,
                        "world_updated": world_updated,
                    }
                )
            )

        return {
            "ok": True,
            "processed": processed,
            "skipped": skipped,
            "world_updated": world_updated,
            "trace_written": trace_written,
            "ts": ts,
            "note": "Phase 6.0 perception tick completed (bounded, internal-only).",
        }
