"""
SSN SNN Engine (Phase 1)

Simulated spiking neural network engine.
Does basic anomaly scoring + spike detection.

Later phases will integrate real SNN models (snnTorch, Loihi, etc.)
"""

from __future__ import annotations
import random
from typing import Any, Dict


class SNNEngine:
    """
    Dummy SNN engine for Phase 1.

    Real SNN work comes in Phase 3.
    """

    def __init__(self):
        self.engine_name = "ssn-snn-dummy-v1"

    def process(self, data: Any, metadata: Dict = None) -> Dict:
        """
        Universal interface expected by BrainRouter.

        Produces:
        - signal_strength (0–1)
        - anomaly_score (0–1)
        - spikes_detected (int)
        """

        # -------------------------
        # 1. Compute signal_strength
        # -------------------------
        if isinstance(data, (int, float)):
            # Normalize numeric values
            strength = min(1.0, max(0.0, abs(float(data)) / 100.0))
        elif isinstance(data, bytes):
            strength = min(1.0, len(data) / 32.0)
        elif isinstance(data, str):
            strength = min(1.0, len(data) / 50.0)
        elif isinstance(data, list) or isinstance(data, dict):
            strength = 0.5
        else:
            strength = random.random() * 0.2  # random low signal

        # -------------------------
        # 2. Simple anomaly score
        # -------------------------
        anomaly = round(random.random() * 0.25 + (1 - strength) * 0.25, 3)

        # -------------------------
        # 3. Spike detection
        # -------------------------
        spikes = int(strength * 10) + random.randint(0, 3)

        return {
            "signal_strength": round(strength, 3),
            "anomaly_score": anomaly,
            "spikes_detected": spikes,
            "meta": {
                "engine": self.engine_name,
                "used_metadata": metadata is not None,
            },
        }
