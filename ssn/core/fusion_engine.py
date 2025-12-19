from __future__ import annotations
from typing import Any, Dict, Optional, List

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
    Phase 3.8 can optionally apply stabilization.
    Phase 5.8 can optionally compute + inject world_summary.
    Phase 6.1 adds bounded reasoning transparency (non-intrusive).
    """

    def __init__(self, memory_hub: Any = None, safety_monitor: Any = None):
        self.llm = LanguageEngine()
        self.snn = SNNEngine()

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
    # Mode weight lookup table (UNCHANGED)
    # ------------------------------------------------------------
    MODE_WEIGHTS = {
        "deep": {"llm": 0.75, "snn": 0.25, "bonus": 0.10, "msg": "🧠 Deep Reasoning Mode — prioritizing structured thinking."},
        "fast": {"llm": 0.25, "snn": 0.75, "bonus": 0.05, "msg": "⚡ Fast Reaction Mode — prioritizing rapid pattern detection."},
        "hybrid": {"llm": 0.50, "snn": 0.50, "bonus": 0.10, "msg": "🔷 Hybrid Mode — balanced cognition + perception."},
        "sensory": {"llm": 0.10, "snn": 0.90, "bonus": 0.00, "msg": "👁 Sensory Mode — SNN dominates."},
        "language": {"llm": 0.90, "snn": 0.10, "bonus": 0.00, "msg": "💬 Language Mode — LLM dominates."},
    }

    # ------------------------------------------------------------
    # Helpers (UNCHANGED)
    # ------------------------------------------------------------
    def _normalize_context(self, context: Optional[Dict]) -> Dict[str, Any]:
        return dict(context) if isinstance(context, dict) else {}

    def _maybe_add_world_summary(self, *, role: str, context: Dict[str, Any]) -> tuple[Dict[str, Any], Optional[str]]:
        ctx = dict(context or {})
        if role != "OWNER":
            return ctx, None

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
            pass

        return ctx, None

    # ------------------------------------------------------------
    # NEW: bounded research extraction (read-only)
    # ------------------------------------------------------------
    def _collect_research(self, query: str) -> List[Dict[str, Any]]:
        if not self.memory_hub or not isinstance(query, str):
            return []

        semantic = getattr(self.memory_hub, "semantic", None)
        if not semantic or not hasattr(semantic, "dump"):
            return []

        out: List[Dict[str, Any]] = []
        facts = semantic.dump()

        for k, v in facts.items():
            if not isinstance(k, str) or not k.startswith("research:"):
                continue
            if not isinstance(v, dict):
                continue

            content = str(v.get("content", "")).lower()
            if query.lower() in content:
                out.append(
                    {
                        "title": v.get("title"),
                        "source": v.get("source"),
                        "confidence": v.get("confidence"),
                    }
                )

            if len(out) >= 3:  # hard bound
                break

        return out

    # ------------------------------------------------------------
    # MAIN FUSION FUNCTION (LOGIC PRESERVED)
    # ------------------------------------------------------------
    def fuse(
        self,
        user_input: Any,
        role: str = "GUEST",
        context: Optional[Dict] = None,
        mode: str = "hybrid",
    ) -> Dict:

        base_context = self._normalize_context(context)

        if mode not in self.MODE_WEIGHTS:
            mode = "hybrid"

        weights = self.MODE_WEIGHTS[mode]

        llm_context, world_summary = self._maybe_add_world_summary(
            role=role, context=base_context
        )

        is_language = isinstance(user_input, str)
        is_sensor = isinstance(user_input, (int, float, bytes, list, dict))

        llm_out = self.llm.process(
            user_input if is_language else str(user_input),
            context=llm_context,
            role=role,
        )

        snn_out = self.snn.process(user_input if is_sensor else None)

        llm_signal = 1.0
        snn_signal = float(snn_out.get("signal_strength", 0.0) or 0.0)

        fusion_score = (llm_signal * weights["llm"]) + (snn_signal * weights["snn"])
        if role == "OWNER":
            fusion_score += weights["bonus"]

        fusion_score = round(min(float(fusion_score), 1.0), 3)

        result: Dict[str, Any] = {
            "role": role,
            "mode": mode,
            "fusion_score": fusion_score,
            "cognition_llm": llm_out,
            "perception_snn": snn_out,
        }

        if isinstance(world_summary, str):
            result["world_summary"] = world_summary

        # -------------------------------
        # NEW: reasoning transparency (NO logic impact)
        # -------------------------------
        if role == "OWNER" and isinstance(user_input, str):
            research_used = self._collect_research(user_input)
            result["reasoning"] = {
                "grounded": bool(research_used),
                "research_count": len(research_used),
                "research_used": research_used,
            }

        # Phase 3.8 stabilization (UNCHANGED)
        if FusionStabilizer is not None:
            try:
                stabilizer = FusionStabilizer(
                    memory_hub=self.memory_hub,
                    safety_monitor=self.safety_monitor,
                )
                result = stabilizer.apply_to_fusion_result(result)
            except Exception:
                result.setdefault("stability", {"status": "skipped"})

        final_message = (
            f"{weights['msg']}\n"
            f"Fusion complete.\n"
            f"- LLM interpreted intent.\n"
            f"- SNN analyzed sensory patterns.\n"
            f"- Mode: {mode}\n"
            f"- Fusion score: {fusion_score}\n"
        )

        result["final_message"] = final_message
        return result
