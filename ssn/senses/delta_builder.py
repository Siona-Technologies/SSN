# ssn/senses/delta_builder.py

from __future__ import annotations

from typing import Any, Dict, Optional

from ssn.senses.contracts import PerceptionPacket, WorldStateDelta


class DeltaBuilder:
    """
    Phase 5.6 — Delta Builder (Perception -> WorldStateDelta)

    Deterministic heuristics only (no heavy models):
    - vision/cctv: create generic entity_detected when confidence is decent
    - lidar: create motion_event when point_count changes significantly (not tracked here, so simple event)
    - imu: create motion_event when accel_mag is high
    - event camera: create motion_event when event_count is high
    - propagate anomaly_score into delta meta for reasoning
    """

    def build(
        self,
        *,
        pkt: PerceptionPacket,
        snn_out: Optional[Dict[str, Any]] = None,
    ) -> Optional[WorldStateDelta]:
        pkt.validate()

        # Basic gating: if confidence too low and no strong anomaly, skip
        if pkt.confidence < 0.25 and pkt.anomaly_score < 0.6:
            return None

        st = pkt.source_sensor
        ts = pkt.ts

        meta = {
            "source_sensor": st,
            "device_id": pkt.device_id,
            "stream_id": pkt.stream_id,
            "anomaly_score": pkt.anomaly_score,
            "confidence": pkt.confidence,
        }
        if isinstance(snn_out, dict):
            meta["snn"] = {
                "signal_strength": snn_out.get("signal_strength"),
                "anomaly_score": snn_out.get("anomaly_score"),
                "spikes_detected": snn_out.get("spikes_detected"),
            }

        # Vision-like: create a generic "entity_detected"
        if st in ("vision_frame", "cctv_frame"):
            # deterministic entity id from stream (not identity recognition yet)
            ent_id = f"entity:{pkt.device_id}:{pkt.stream_id}"
            return WorldStateDelta(
                ts=ts,
                source="perception",
                changes=[{
                    "type": "entity_detected",
                    "entity": "unknown_visual",
                    "id": ent_id,
                    "attributes": {
                        "stream": pkt.stream_id,
                    }
                }],
                confidence=float(pkt.confidence),
                meta=meta,
            )

        # Event camera: motion-like if event_count is meaningful
        if st == "event_camera":
            ec = pkt.features.get("event_count")
            if isinstance(ec, (int, float)) and float(ec) >= 50:
                return WorldStateDelta(
                    ts=ts,
                    source="perception",
                    changes=[{
                        "type": "motion_event",
                        "area": pkt.stream_id,
                        "level": min(1.0, float(ec) / 500.0),
                        "reason": "event_camera_activity",
                    }],
                    confidence=float(pkt.confidence),
                    meta=meta,
                )
            return None

        # IMU: motion if accel magnitude is high
        if st == "imu_sample":
            mag = pkt.features.get("accel_mag")
            if isinstance(mag, (int, float)) and float(mag) >= 2.5:
                return WorldStateDelta(
                    ts=ts,
                    source="perception",
                    changes=[{
                        "type": "motion_event",
                        "area": pkt.stream_id,
                        "level": min(1.0, float(mag) / 25.0),
                        "reason": "imu_accel_mag",
                    }],
                    confidence=float(pkt.confidence),
                    meta=meta,
                )
            return None

        # LiDAR: motion/surprise if sparse or dense
        if st == "lidar_scan":
            pc = pkt.features.get("point_count")
            if isinstance(pc, (int, float)):
                lvl = 0.8 if float(pc) < 20 else 0.2
                return WorldStateDelta(
                    ts=ts,
                    source="perception",
                    changes=[{
                        "type": "motion_event",
                        "area": pkt.stream_id,
                        "level": float(lvl),
                        "reason": "lidar_point_count",
                        "point_count": int(pc),
                    }],
                    confidence=float(pkt.confidence),
                    meta=meta,
                )
            return None

        # Default: represent as generic event
        return WorldStateDelta(
            ts=ts,
            source="perception",
            changes=[{
                "type": "unknown_change",
                "sensor": st,
            }],
            confidence=float(pkt.confidence),
            meta=meta,
        )
