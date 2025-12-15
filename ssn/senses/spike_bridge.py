# ssn/senses/spike_bridge.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional

from ssn.senses.contracts import PerceptionPacket


@dataclass(frozen=True)
class SpikeBridgeConfig:
    """
    Controls how we convert features into spikes.

    threshold: minimum absolute value for a spike
    max_spikes: hard cap for payload size
    """
    threshold: float = 0.20
    max_spikes: int = 256


class SpikeBridge:
    """
    Phase 5.3 — Spike Bridge

    Converts PerceptionPacket.features into a bounded "spike payload" suitable for SNNEngine.process().
    This is deterministic and lightweight (no heavy models).
    """

    def __init__(self, config: Optional[SpikeBridgeConfig] = None):
        self.config = config or SpikeBridgeConfig()

    @staticmethod
    def _is_num(x: Any) -> bool:
        return isinstance(x, (int, float)) and x == x and x not in (float("inf"), float("-inf"))

    def _flatten_numbers(self, obj: Any, out: List[float], *, cap: int) -> None:
        """
        Recursively collect numeric values from nested structures into `out` up to cap.
        """
        if len(out) >= cap:
            return

        if self._is_num(obj):
            out.append(float(obj))
            return

        if isinstance(obj, dict):
            # stable ordering for determinism
            for k in sorted(obj.keys(), key=lambda x: str(x)):
                if len(out) >= cap:
                    break
                self._flatten_numbers(obj.get(k), out, cap=cap)
            return

        if isinstance(obj, (list, tuple)):
            for it in obj:
                if len(out) >= cap:
                    break
                self._flatten_numbers(it, out, cap=cap)
            return

        # ignore other types (str/bytes/etc.)

    def to_spikes(self, pkt: PerceptionPacket) -> Dict[str, Any]:
        """
        Returns a bounded spike payload dict:
        {
          "spikes": List[Tuple[int, float]],
          "meta": {...}
        }
        """
        pkt.validate()

        # Prefer known feature keys first, then fallback to flatten all
        numeric: List[float] = []

        feats = pkt.features or {}

        # Priority 1: embeddings
        emb = feats.get("embedding")
        if isinstance(emb, (list, tuple)):
            self._flatten_numbers(emb, numeric, cap=self.config.max_spikes * 2)

        # Priority 2: event camera features
        if not numeric and isinstance(feats.get("event_count"), (int, float)):
            self._flatten_numbers([feats.get("event_count"), feats.get("polarity_balance", 0)], numeric, cap=64)

        # Priority 3: lidar
        if not numeric and isinstance(feats.get("point_count"), (int, float)):
            bbox = feats.get("bbox") or {}
            self._flatten_numbers([feats.get("point_count"), bbox], numeric, cap=128)

        # Priority 4: imu
        if not numeric and isinstance(feats.get("accel_mag"), (int, float)):
            self._flatten_numbers([feats.get("accel"), feats.get("gyro"), feats.get("accel_mag"), feats.get("gyro_mag")], numeric, cap=128)

        # Fallback: flatten everything
        if not numeric:
            self._flatten_numbers(feats, numeric, cap=self.config.max_spikes * 2)

        # Convert numeric vector -> spikes (index, value) by threshold
        spikes: List[Tuple[int, float]] = []
        thr = float(self.config.threshold)

        for i, v in enumerate(numeric):
            if len(spikes) >= self.config.max_spikes:
                break
            if not self._is_num(v):
                continue
            if abs(float(v)) >= thr:
                spikes.append((int(i), float(v)))

        # If still empty, inject a tiny "heartbeat" spike (keeps SNN from always seeing None)
        if not spikes:
            spikes = [(0, thr)]

        return {
            "spikes": spikes,
            "meta": {
                "source_sensor": pkt.source_sensor,
                "device_id": pkt.device_id,
                "stream_id": pkt.stream_id,
                "ts": pkt.ts,
                "anomaly_score": pkt.anomaly_score,
                "confidence": pkt.confidence,
                "threshold": thr,
                "max_spikes": int(self.config.max_spikes),
            },
        }

    def feed_snn(self, snn_engine: Any, pkt: PerceptionPacket) -> Dict[str, Any]:
        """
        Convenience: convert packet to spikes and feed SNNEngine.process().
        """
        payload = self.to_spikes(pkt)
        fn = getattr(snn_engine, "process", None)
        if not callable(fn):
            raise TypeError("snn_engine must have a callable .process(...)")
        return fn(payload)
