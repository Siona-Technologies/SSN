#!/usr/bin/env python3
"""
CI-safe unittest runner for SIONA.

Runs modules known to pass offline without import side-effects.
Each test receives a unique SSN_RUNTIME_DATA_DIR (per-test isolation).
"""

from __future__ import annotations

import atexit
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
    "ssn.tests.test_phase2_closeout_docs",
    # Phase 3A local model / eval foundation
    "ssn.tests.test_phase3a_runtime_data_isolation",
    "ssn.tests.test_phase3a_local_provider",
    "ssn.tests.test_phase3a_model_registry",
    "ssn.tests.test_phase3a_provider_eval",
    "ssn.tests.test_phase3a_security_gate",
    "ssn.tests.test_phase3b_openai_chat_transport",
    "ssn.tests.test_identity_information_governance",
    "ssn.tests.test_approved_identity_registry",
    "ssn.tests.test_governed_runtime_context",
    "ssn.tests.test_governed_identity_response_guard",
    "ssn.tests.test_real_governed_identity_campaign",
    "ssn.tests.test_real_guarded_identity_retest",
    "ssn.tests.test_gate_e_breadth_evaluation",
    "ssn.tests.test_phase3b_model_registry_activation",
    # Phase 4 learned neuromorphic (model-free; no torch/snnTorch)
    "ssn.tests.test_phase_roadmap_current_status",
    "ssn.tests.test_phase4_planning_docs",
    "ssn.tests.test_phase4a_readiness",
    "ssn.tests.test_phase4a_temporal_salience_dataset",
    "ssn.tests.test_phase4b_training_gate",
    "ssn.tests.test_phase4b_exp4_003_evidence",
    "ssn.tests.test_phase4c_learned_snn_provider",
    "ssn.tests.test_phase4d_learned_snn_breadth_safety",
    "ssn.tests.test_phase4_closeout",
    # Skipped / placeholder modules (import-safe)
    "ssn.tests.test_internet_research_basic",
    "ssn.tests.test_orchestrator_internet_research",
    "ssn.tests.test_phase55_world_model_updates",
    "ssn.tests.test_phase56_perception_to_world_model",
]


def main() -> int:
    os.environ.setdefault("SSN_OFFLINE", "1")

    from ssn.runtime.paths import cleanup_ensured_isolation
    from ssn.runtime.test_isolation import IsolatedTextTestRunner

    atexit.register(cleanup_ensured_isolation)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for mod in CI_TEST_MODULES:
        suite.addTests(loader.loadTestsFromName(mod))

    runner = IsolatedTextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
