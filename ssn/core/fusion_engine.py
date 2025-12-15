"""
SSN Cognitive Fusion Engine (Phase 3.4 – COMPATIBLE VERSION)
+ Phase 3.8 Stabilization Overlay (internal-only, advisory)
+ Phase 5.8 World Summary Normalizer (OWNER-only, bounded)

This engine fuses:
- LLM cognition (reasoning, language)
- SNN perception (signals, patterns)
- Mode weights (deep, fast, hybrid, sensory, language)

Compatible with Orchestrator calling style:
    fuse(user_input, role, context, mode)

Phase 3.8 adds:
- FusionStabilizer overlay (optional)
- Damping + style hints using Phase 3.7 signals (drift, prefs)
- No external actions, no law changes, no autonomy escalation

Phase 5.8 adds:
- If context contains world snapshot (context["world"]), compute bounded world_summary
- Inject world_summary into LLM context (OWNER only)
- Return world_summary in the fusion packet (non-breaking)
"""

from __future__ import annotations
from typing import Any, Dict, Optional

from ssn.core.language_engine import LanguageEngine
from ssn.core.snn_engine import SNNEngine

# Phase 3.8 (safe import, never break fusion if missing)
try:
    from ssn.core.fusion_stabilizer import FusionStabilizer
except Exception:
    FusionStabilizer = None  # type: ignore

# Phase 5.8 (safe import)
try:
    from ssn.world.world_summary import WorldSummaryNormalizer, WorldSummaryConfig
except Exception:
    WorldSummaryNormalizer = None  # type: ignore
    WorldSummaryConfig = None  # type: ignore


class FusionEngine:
    """
    Hybrid cognitive fusion engine with mode-aware weighting.
    Phase 3.8 can optionally apply stabilization based on recent drift/preferences.
    Phase 5.8 can optionally compute + inject world_summary for OWNER context.
    """

    def __init__(self, memory_hub: Any = None, safety_monitor: Any = None):
        self.llm = LanguageEngine()
        self.snn = SNNEngine()

        # Optional (for Phase 3.8 stabilizer). Keeps backward compatibility.
        self.memory_hub = memory_hub
        self.safety_monitor = safety_monitor

        # Phase 5.8 summarizer (optional)
        self.world_summarizer = None
        if WorldSummaryNormalizer is not None and WorldSummaryConfig is not None:
            try:
                self.world_summarizer = WorldSummaryNormalizer(
                    WorldSummaryConfig(
                        max_entities=6,
                        max_events=6,
                        max_attr_keys=4,
                        max_chars=600,
                    )
                )
            except Exception:
                self.world_summarizer = None

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
    # Phase 5.8 helpers
    # ------------------------------------------------------------
    def _normalize_context(self, context: Optional[Dict]) -> Dict[str, Any]:
        return dict(context) if isinstance(context, dict) else {}

    def _maybe_add_world_summary(self, *, role: str, context: Dict[str, Any]) -> tuple[Dict[str, Any], Optional[str]]:
        """
        OWNER-only: if context["world"] exists, compute bounded world_summary and place it in context.
        Returns (context_copy, world_summary_or_none).
        """
        ctx = dict(context or {})
        if role != "OWNER":
            return ctx, None

        # If already present, respect it
        if isinstance(ctx.get("world_summary"), str):
            return ctx, ctx.get("world_summary")

        world = ctx.get("world")
        if not isinstance(world, dict):
            return ctx, None

        if self.world_summarizer is None:
            return ctx, None

        try:
            summary = self.world_summarizer.summarize(world)
            if isinstance(summary, str) and summary:
                ctx["world_summary"] = summary
                return ctx, summary
        except Exception:
            return ctx, None

        return ctx, None

    # ------------------------------------------------------------
    # MAIN FUSION FUNCTION — fully compatible signature
    # ------------------------------------------------------------
    def fuse(
        self,
        user_input: Any,
        role: str = "GUEST",
        context: Optional[Dict] = None,
        mode: str = "hybrid",
    ) -> Dict:
        """
        Main fusion function.
        Compatible with calls like:
            fuse(user_input, role, context, mode)
        """

        # Normalize context
        base_context = self._normalize_context(context)

        # Validate or fallback to hybrid
        if mode not in self.MODE_WEIGHTS:
            mode = "hybrid"

        weights = self.MODE_WEIGHTS[mode]

        # Phase 5.8: inject world_summary into LLM context (OWNER only)
        llm_context, world_summary = self._maybe_add_world_summary(role=role, context=base_context)

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
            context=llm_context,
            role=role,
        )

        # -------------------------------
        # Step 3 — SNN processing
        # -------------------------------
        snn_out = self.snn.process(user_input if is_sensor else None)

        # -------------------------------
        # Step 4 — Weighted fusion score
        # -------------------------------
        llm_signal = 1.0
        snn_signal = float(snn_out.get("signal_strength", 0.0) or 0.0)

        fusion_score = (llm_signal * weights["llm"]) + (snn_signal * weights["snn"])

        if role == "OWNER":
            fusion_score += weights["bonus"]

        fusion_score = round(min(float(fusion_score), 1.0), 3)

        # -------------------------------
        # Step 5 — Build base result
        # -------------------------------
        result: Dict[str, Any] = {
            "role": role,
            "mode": mode,
            "fusion_score": fusion_score,
            "cognition_llm": llm_out,
            "perception_snn": snn_out,
        }

        # Phase 5.8: expose summary in the packet (non-breaking)
        if isinstance(world_summary, str):
            result["world_summary"] = world_summary

        # -------------------------------
        # Phase 3.8 — Stabilization overlay (advisory, safe)
        # -------------------------------
        if FusionStabilizer is not None:
            try:
                stabilizer = FusionStabilizer(
                    memory_hub=getattr(self, "memory_hub", None),
                    safety_monitor=getattr(self, "safety_monitor", None),
                )
                result = stabilizer.apply_to_fusion_result(result)
            except Exception:
                # Never break fusion if stabilizer fails
                result.setdefault("stability", {"status": "skipped"})

        # -------------------------------
        # Step 6 — Unified final output (computed last so it matches stabilized score)
        # -------------------------------
        final_score = result.get("fusion_score", fusion_score)
        final_message = (
            f"{weights['msg']}\n"
            f"Fusion complete.\n"
            f"- LLM interpreted intent.\n"
            f"- SNN analyzed sensory patterns.\n"
            f"- Mode: {mode}\n"
            f"- Fusion score: {final_score}\n"
        )

        result["final_message"] = final_message
        return result
