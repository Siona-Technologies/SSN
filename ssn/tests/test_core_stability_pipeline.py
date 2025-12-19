"""
Integration test for Phase 3.7 – 3.9 core stability pipeline.

Validates:
- BrainRouter routing
- Trace writing (router_decision)
- ConsistencyMonitor drift_report
- ModeDamper decision reading
- FusionStabilizer application safety
"""

from ssn.memory.memory_hub import MemoryHub
from ssn.core.brain_router import BrainRouter
from ssn.core.consistency_monitor import ConsistencyMonitor
from ssn.core.mode_damper import ModeDamper
from ssn.core.fusion_stabilizer import FusionStabilizer


def run_test():
    # --------------------------------------------------
    # Setup
    # --------------------------------------------------
    memory = MemoryHub()

    router = BrainRouter(memory_hub=memory, safety_monitor=None)
    consistency = ConsistencyMonitor(memory_hub=memory, safety_monitor=None)
    damper = ModeDamper(memory_hub=memory, safety_monitor=None)
    stabilizer = FusionStabilizer(memory_hub=memory, safety_monitor=None)

    # --------------------------------------------------
    # Step 1: OWNER interaction (writes router_decision)
    # --------------------------------------------------
    out = router.route(
        role="OWNER",
        user_input="Analyze this deeply and carefully.",
        context={"task": "test"},
    )

    assert out["role"] == "OWNER"
    assert "result" in out

    traces = memory.get_recent_traces(50)
    assert any(
        t.get("payload", {}).get("type") == "router_decision"
        for t in traces
    ), "router_decision trace missing"

    # --------------------------------------------------
    # Step 2: Consistency monitor produces drift_report
    # --------------------------------------------------
    drift = consistency.evaluate_recent(trace_limit=50)

    assert drift["status"] == "completed"
    assert "drift_score" in drift

    traces = memory.get_recent_traces(50)
    assert any(
        t.get("payload", {}).get("type") == "drift_report"
        for t in traces
    ), "drift_report trace missing"

    # --------------------------------------------------
    # Step 3: Mode damper reads drift safely
    # --------------------------------------------------
    decision = damper.damp_mode("deep")

    assert decision.original_mode == "deep"
    assert decision.selected_mode in {"deep", "hybrid"}

    # --------------------------------------------------
    # Step 4: Fusion stabilizer applies safely
    # --------------------------------------------------
    fusion_packet = {
        "fusion_score": 0.92,
        "mode": "deep",
    }

    stabilized = stabilizer.apply_to_fusion_result(fusion_packet)

    assert "stability" in stabilized
    assert "fusion_score" in stabilized
    assert 0.0 <= stabilized["fusion_score"] <= 1.0

    print("✅ Core stability pipeline test PASSED")


if __name__ == "__main__":
    run_test()
