# ssn/senses/perception_hub.py

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ssn.senses.contracts import SensorEnvelope, PerceptionPacket, WorldStateDelta
from ssn.senses.sensory_bus import SensoryBus
from ssn.senses.encoders.registry import EncoderRegistry
from ssn.senses.spike_bridge import SpikeBridge
from ssn.senses.delta_builder import DeltaBuilder


@dataclass(frozen=True)
class PerceptionHubConfig:
    max_events_per_tick: int = 24
    trace_enabled: bool = True
    trace_excerpt_chars: int = 120
    future_tolerance_sec: float = 0.25
    world_updates_enabled: bool = True


class PerceptionHub:
    """
    Phase 5.4/5.6 — Perception Hub + World Model updates
    """

    def __init__(
        self,
        *,
        bus: SensoryBus,
        registry: EncoderRegistry,
        spike_bridge: Optional[SpikeBridge] = None,
        snn_engine: Optional[Any] = None,
        memory_hub: Optional[Any] = None,
        world_model: Optional[Any] = None,
        delta_builder: Optional[DeltaBuilder] = None,
        config: Optional[PerceptionHubConfig] = None,
    ):
        self.bus = bus
        self.registry = registry
        self.bridge = spike_bridge or SpikeBridge()
        self.snn = snn_engine
        self.memory_hub = memory_hub

        self.world_model = world_model
        self.delta_builder = delta_builder or DeltaBuilder()

        self.config = config or PerceptionHubConfig()
        self._last_ts = 0.0

    @staticmethod
    def _safe_excerpt(payload: Any, max_chars: int) -> str:
        try:
            s = str(payload)
        except Exception:
            s = "<unprintable>"
        s = s.replace("\n", " ").strip()
        return s[:max_chars]

    def _try_write_trace(self, payload: Dict[str, Any]) -> bool:
        if not self.memory_hub:
            return False

        candidates = [
            getattr(self.memory_hub, "add_trace", None),
            getattr(self.memory_hub, "write_trace", None),
        ]

        trace = getattr(self.memory_hub, "trace", None)
        if trace is not None:
            candidates.append(getattr(trace, "add_trace", None))
            candidates.append(getattr(trace, "append", None))

        trace_memory = getattr(self.memory_hub, "trace_memory", None)
        if trace_memory is not None:
            candidates.append(getattr(trace_memory, "add_trace", None))
            candidates.append(getattr(trace_memory, "append", None))

        for fn in candidates:
            if callable(fn):
                try:
                    try:
                        fn(payload=payload)
                    except TypeError:
                        fn(payload)
                    return True
                except Exception:
                    continue

        return False

    def process_once(self) -> Dict[str, Any]:
        start = time.time()
        now = time.time()

        tol = float(self.config.future_tolerance_sec or 0.0)
        if tol < 0.0:
            tol = 0.0
        if tol > 2.0:
            tol = 2.0

        t_min = max(self._last_ts - 0.001, 0.0)
        t_max = now + tol

        events = self.bus.get_window(t_min=t_min, t_max=t_max, limit=self.config.max_events_per_tick)
        events = [e for e in events if e.ts > self._last_ts]

        if events:
            self._last_ts = max(e.ts for e in events)

        processed = 0
        skipped = 0
        trace_written = 0
        world_applied = 0

        for e in events[: self.config.max_events_per_tick]:
            try:
                pkt = self.registry.encode(e)

                snn_out = None
                if self.snn is not None:
                    snn_out = self.bridge.feed_snn(self.snn, pkt)

                # World model update (bounded belief state)
                if self.config.world_updates_enabled and self.world_model is not None:
                    d = self.delta_builder.build(pkt=pkt, snn_out=snn_out)
                    if d is not None:
                        try:
                            # world_model must implement apply_delta
                            fn = getattr(self.world_model, "apply_delta", None)
                            if callable(fn):
                                fn(d)
                                world_applied += 1
                        except Exception:
                            pass

                if self.config.trace_enabled:
                    trace_payload = {
                        "type": "perception_tick_item",
                        "ts": e.ts,
                        "sensor_type": e.sensor_type,
                        "device_id": e.device_id,
                        "stream_id": e.stream_id,
                        "privacy": e.privacy,
                        "quality": e.quality,
                        "payload_excerpt": self._safe_excerpt(e.payload, self.config.trace_excerpt_chars),
                        "features_keys": sorted(list((pkt.features or {}).keys())),
                        "anomaly_score": pkt.anomaly_score,
                        "confidence": pkt.confidence,
                        "snn": None if snn_out is None else {
                            "signal_strength": snn_out.get("signal_strength"),
                            "anomaly_score": snn_out.get("anomaly_score"),
                            "spikes_detected": snn_out.get("spikes_detected"),
                        },
                        "meta": {
                            "encoder": (pkt.meta or {}).get("encoder"),
                            "future_tolerance_sec": tol,
                            "world_updates_enabled": bool(self.config.world_updates_enabled),
                        },
                    }
                    if self._try_write_trace(trace_payload):
                        trace_written += 1

                processed += 1

            except KeyError:
                skipped += 1
            except Exception:
                skipped += 1

        return {
            "status": "ok",
            "events_in_window": len(events),
            "processed": processed,
            "skipped": skipped,
            "trace_written": trace_written,
            "world_applied": world_applied,
            "has_snn": self.snn is not None,
            "has_world_model": self.world_model is not None,
            "runtime_ms": round((time.time() - start) * 1000, 3),
        }
