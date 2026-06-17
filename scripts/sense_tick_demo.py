#!/usr/bin/env python3
"""
Phase 4 demo: synthetic vision/audio events → perception tick → world model snapshot.

Usage:
  SSN_OFFLINE=1 python scripts/sense_tick_demo.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ssn.runtime.perception_tick import PerceptionTick
from ssn.runtime.runtime_builder import SSNRuntimeBuilder


def _synthetic_events() -> list[dict]:
    ts = time.time()
    return [
        {
            "type": "vision_detection",
            "sensor_type": "vision_frame",
            "ts": ts,
            "confidence": 0.82,
            "entity": {
                "id": "person:demo",
                "entity": "person",
                "status": "present",
                "confidence": 0.82,
                "attributes": {"zone": "entry"},
            },
        },
        {
            "type": "audio_event",
            "sensor_type": "audio_chunk",
            "ts": ts + 0.05,
            "confidence": 0.55,
        },
        {
            "type": "motion_event",
            "sensor_type": "imu_sample",
            "ts": ts + 0.10,
            "confidence": 0.61,
        },
    ]


def main() -> int:
    os.environ.setdefault("SSN_OFFLINE", "1")

    rt = SSNRuntimeBuilder.build_default(default_role="OWNER", output_mode="full")
    events = _synthetic_events()

    tick = PerceptionTick(
        world_model=getattr(rt, "world_model", None),
        memory_hub=getattr(getattr(rt, "orchestrator", None), "memory_hub", None)
        or getattr(rt, "memory_hub", None),
        perception_hub=getattr(rt, "perception_hub", None),
        source="sense_tick_demo",
    )
    report = tick.run(events, max_events=25)

    print("=== Perception tick ===")
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))

    wm = getattr(rt, "world_model", None)
    if wm is not None and callable(getattr(wm, "snapshot", None)):
        snap = wm.snapshot(include_events=True, max_entities=10, max_events=10)
        print("\n=== World snapshot ===")
        print(json.dumps(snap, indent=2, ensure_ascii=False, default=str))

    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
