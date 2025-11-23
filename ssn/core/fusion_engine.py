"""
SSN Cognitive Fusion Engine (Phase 3.4 – COMPATIBLE VERSION)

This engine fuses:
- LLM cognition (reasoning, language)
- SNN perception (signals, patterns)
- Mode weights (deep, fast, hybrid, sensory, language)

Now compatible with Orchestrator calling style:
    fuse(user_input, role, context, mode)
"""

from __future__ import annotations
from typing import Any, Dict, Optional

from ssn.core.language_engine import LanguageEngine
from ssn.core.snn_engine import SNNEngine


class FusionEngine:
    """
    Hybrid cognitive fusion engine with mode-aware weighting.
    """

    def __init__(self):
        self.llm = LanguageEngine()
        self.snn = SNNEngine()

    # ------------------------------------------------------------
    # Mode weight lookup table
    # ------------------------------------------------------------
    MODE_WEIGHTS = {
        "deep": {
            "llm": 0.75,
            "snn": 0.25,
            "bonus": 0.10,
            "msg": "🧠 Deep Reasoning Mode — prioritizing structured thinking.",
        },
        "fast": {
            "llm": 0.25,
            "snn": 0.75,
            "bonus": 0.05,
            "msg": "⚡ Fast Reaction Mode — prioritizing rapid pattern detection.",
        },
        "hybrid": {
            "llm": 0.50,
            "snn": 0.50,
            "bonus": 0.10,
            "msg": "🔷 Hybrid Mode — balanced cognition + perception.",
        },
        "sensory": {
            "llm": 0.10,
            "snn": 0.90,
            "bonus": 0.00,
            "msg": "👁 Sensory Mode — SNN dominates.",
        },
        "language": {
            "llm": 0.90,
            "snn": 0.10,
            "bonus": 0.00,
            "msg": "💬 Language Mode — LLM dominates.",
        },
    }

    # ------------------------------------------------------------
    # MAIN FUSION FUNCTION — fully compatible signature
    # ------------------------------------------------------------
    def fuse(
        self,
        user_input: Any,
        role: str = "GUEST",
        context: Optional[Dict] = None,
        mode: str = "hybrid"
    ) -> Dict:
        """
        Main fusion function.
        Compatible with calls like:
            fuse(user_input, role, context, mode)
        """

        # Validate or fallback to hybrid
        if mode not in self.MODE_WEIGHTS:
            mode = "hybrid"

        weights = self.MODE_WEIGHTS[mode]

        # -------------------------------
        # Step 1 — Type detection
        # -------------------------------
        is_language = isinstance(user_input, str)
        is_sensor = isinstance(user_input, (int, float, bytes, list, dict))

        # -------------------------------
        # Step 2 — LLM processing
        # -------------------------------
        llm_out = self.llm.process(
            user_input if is_language else str(user_input),
            context=context,
            role=role,
        )

        # -------------------------------
        # Step 3 — SNN processing
        # -------------------------------
        snn_out = self.snn.process(
            user_input if is_sensor else None
        )

        # -------------------------------
        # Step 4 — Weighted fusion score
        # -------------------------------
        llm_signal = 1.0
        snn_signal = snn_out["signal_strength"]

        fusion_score = (
            llm_signal * weights["llm"]
            + snn_signal * weights["snn"]
        )

        if role == "OWNER":
            fusion_score += weights["bonus"]

        fusion_score = round(min(fusion_score, 1.0), 3)

        # -------------------------------
        # Step 5 — Unified final output
        # -------------------------------
        final_message = (
            f"{weights['msg']}\n"
            f"Fusion complete.\n"
            f"- LLM interpreted intent.\n"
            f"- SNN analyzed sensory patterns.\n"
            f"- Mode: {mode}\n"
            f"- Fusion score: {fusion_score}\n"
        )

        return {
            "role": role,
            "mode": mode,
            "fusion_score": fusion_score,
            "cognition_llm": llm_out,
            "perception_snn": snn_out,
            "final_message": final_message,
        }
