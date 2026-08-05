#!/usr/bin/env python3
"""
CI-safe unittest runner for SIONA.

Runs modules known to pass offline without import side-effects.
Expand this list as test debt is cleared (see docs/SIONA_BUILD_PLAN.md).
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


CI_TEST_MODULES = [
    # Phase 1 — inference
    "ssn.tests.test_mock_llm_integration",
    "ssn.tests.test_llm_providers_basic",
    # Front Door + HTTP API
    "ssn.tests.test_front_door_gateway",
    "ssn.tests.test_http_front_door",
    "ssn.tests.test_phase3_tenant_law",
    "ssn.tests.test_phase4_speech_and_senses",
    "ssn.tests.test_phase5_embedding_and_knowledge_rag",
    "ssn.tests.test_phase6_production_shape",
    # Eval harness
    "ssn.tests.test_phase47_eval_harness_smoke",
    # Interface / runtime (stable subset)
    "ssn.tests.test_phase40_interface_gateway",
    "ssn.tests.test_phase50_sensory_contracts",
    "ssn.tests.test_phase51_sensory_bus",
    "ssn.tests.test_phase52_encoders_contracts",
    "ssn.tests.test_phase53_spike_bridge",
    "ssn.tests.test_phase54_perception_hub",
    "ssn.tests.test_phase60_world_runtime_wiring",
    "ssn.tests.test_phase61_sense_tick_to_world",
    "ssn.tests.test_phase62_trace_and_world_persistence",
    "ssn.tests.test_phase63_world_context_injection",
    "ssn.tests.test_phase37_memory_consolidation",
    "ssn.tests.test_phase37_preference_memory",
    "ssn.tests.test_phase37_suggestion_engine",
    "ssn.tests.test_phase38_fusion_stabilizer",
    "ssn.tests.test_phase38_fusion_stabilizer_no_drift_regression",
    "ssn.tests.test_phase39_mode_damper",
    # Cognitive runtime foundation (Phase 1 neuromorphic architecture)
    "ssn.tests.test_cognitive_runtime_v1",
    "ssn.tests.test_cognitive_runtime_hardening",
    # Phase 2 runtime integration
    "ssn.tests.test_phase2_runtime_integration",
    "ssn.tests.test_phase2_integration_hardening",
    "ssn.tests.test_phase2_trace_isolation_shutdown",
    # Skipped / placeholder modules (import-safe)
    "ssn.tests.test_internet_research_basic",
    "ssn.tests.test_orchestrator_internet_research",
    "ssn.tests.test_phase55_world_model_updates",
    "ssn.tests.test_phase56_perception_to_world_model",
]


def main() -> int:
    os.environ.setdefault("SSN_OFFLINE", "1")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for mod in CI_TEST_MODULES:
        suite.addTests(loader.loadTestsFromName(mod))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
