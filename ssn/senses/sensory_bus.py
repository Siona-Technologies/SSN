# ssn/senses/sensory_bus.py

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ssn.senses.contracts import SensorEnvelope


@dataclass(frozen=True)
class BusStats:
    streams: int
    total_events: int
    dropped: int
    per_stream_counts: Dict[str, int]


class SensoryBus:
    """
    Phase 5.1 — Sensory Bus (bounded, efficient)

    - Maintains per-stream ring buffers of SensorEnvelope
    - Applies backpressure by dropping oldest entries when capacity exceeded
    - Supports retrieval by (sensor_type, device_id, stream_id) and time windows
    """

    def __init__(self, *, max_events_per_stream: int = 256, max_total_events: int = 4096):
        if max_events_per_stream <= 0:
            raise ValueError("max_events_per_stream must be > 0")
        if max_total_events <= 0:
            raise ValueError("max_total_events must be > 0")

        self.max_events_per_stream = int(max_events_per_stream)
        self.max_total_events = int(max_total_events)

        # stream_key -> list[SensorEnvelope] (chronological)
        self._streams: Dict[str, List[SensorEnvelope]] = {}
        self._dropped = 0

    @staticmethod
    def _stream_key(e: SensorEnvelope) -> str:
        return f"{e.sensor_type}:{e.device_id}:{e.stream_id}"

    def _enforce_limits(self) -> None:
        total = sum(len(v) for v in self._streams.values())
        if total <= self.max_total_events:
            return

        while total > self.max_total_events:
            oldest: Optional[Tuple[float, str]] = None
            for k, buf in self._streams.items():
                if not buf:
                    continue
                ts0 = buf[0].ts
                if oldest is None or ts0 < oldest[0]:
                    oldest = (ts0, k)

            if oldest is None:
                break

            _, k = oldest
            buf = self._streams.get(k, [])
            if buf:
                buf.pop(0)
                self._dropped += 1
                total -= 1
            else:
                self._streams.pop(k, None)

    def _enforce_stream_limit(self, key: str) -> None:
        buf = self._streams.get(key)
        if not buf:
            return
        while len(buf) > self.max_events_per_stream:
            buf.pop(0)
            self._dropped += 1

    def publish(self, event: SensorEnvelope) -> None:
        if not isinstance(event, SensorEnvelope):
            raise TypeError("event must be a SensorEnvelope")
        event.validate()

        key = self._stream_key(event)
        buf = self._streams.setdefault(key, [])
        buf.append(event)

        # Keep chronological (handle occasional out-of-order)
        if len(buf) >= 2 and buf[-2].ts > buf[-1].ts:
            buf.sort(key=lambda x: x.ts)

        self._enforce_stream_limit(key)
        self._enforce_limits()

        if not self._streams.get(key):
            self._streams.pop(key, None)

    def get_recent(
        self,
        *,
        sensor_type: Optional[str] = None,
        device_id: Optional[str] = None,
        stream_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[SensorEnvelope]:
        if limit <= 0:
            return []

        out: List[SensorEnvelope] = []
        for key, buf in self._streams.items():
            if not buf:
                continue
            st, did, sid = key.split(":", 2)

            if sensor_type and st != sensor_type:
                continue
            if device_id and did != device_id:
                continue
            if stream_id and sid != stream_id:
                continue

            out.extend(buf)

        out.sort(key=lambda x: x.ts, reverse=True)
        return out[: int(limit)]

    def get_window(
        self,
        *,
        t_min: float,
        t_max: float,
        sensor_type: Optional[str] = None,
        device_id: Optional[str] = None,
        stream_id: Optional[str] = None,
        limit: int = 200,
    ) -> List[SensorEnvelope]:
        """
        Get events in [t_min, t_max] matching filters.

        Important: allow t_min == 0.0 (first tick / bootstrapping).
        """
        if t_max < t_min:
            return []
        if limit <= 0:
            return []
        # allow t_min == 0.0; only reject negative
        if t_min < 0.0 or t_max <= 0.0:
            return []

        out: List[SensorEnvelope] = []
        for key, buf in self._streams.items():
            if not buf:
                continue
            st, did, sid = key.split(":", 2)

            if sensor_type and st != sensor_type:
                continue
            if device_id and did != device_id:
                continue
            if stream_id and sid != stream_id:
                continue

            for e in buf:
                if e.ts < t_min:
                    continue
                if e.ts > t_max:
                    continue
                out.append(e)

        out.sort(key=lambda x: x.ts)
        return out[: int(limit)]

    def prune_older_than(self, t_cutoff: float) -> int:
        if t_cutoff <= 0:
            return 0

        removed = 0
        for k in list(self._streams.keys()):
            buf = self._streams.get(k, [])
            if not buf:
                self._streams.pop(k, None)
                continue
            while buf and buf[0].ts < t_cutoff:
                buf.pop(0)
                removed += 1
            if not buf:
                self._streams.pop(k, None)

        return removed

    def stats(self) -> BusStats:
        per = {k: len(v) for k, v in self._streams.items() if v}
        total = sum(per.values())
        return BusStats(
            streams=len(per),
            total_events=total,
            dropped=int(self._dropped),
            per_stream_counts=per,
        )

    def clear(self) -> None:
        self._streams.clear()
        self._dropped = 0
