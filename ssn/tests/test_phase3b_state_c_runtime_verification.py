"""EXP-3B-013 — State C evidence integrity (offline recomputation)."""

from __future__ import annotations

import hashlib
import json
import os
import unittest
from pathlib import Path
from typing import Any, Dict, Tuple

os.environ.setdefault("SSN_OFFLINE", "1")

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs" / "evidence" / "EXP-3B-013_STATE_C.json"
DOC = ROOT / "docs" / "SIONA_STATE_C_REGISTRY_BOUND_RUNTIME_VERIFICATION.md"
STATUS = ROOT / "docs" / "PHASE_STATUS.md"
ADR = ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md"
RESEARCH = ROOT / "docs" / "PHASE_3B_MODEL_RUNTIME_RESEARCH.md"
RUNBOOK = ROOT / "docs" / "PHASE_3B_INSTALLATION_RUNBOOK.md"
REGISTRY = ROOT / "config" / "model_registry.json"

APPROVED_PROVIDER = "siona-local-open-weight-v1"
APPROVED_MODEL = "Qwen3-1.7B-Q4_K_M"
APPROVED_CAPS = {
    "chat": True,
    "tools": False,
    "structured_json": False,
    "streaming": False,
    "multimodal": False,
    "context_window": 4096,
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _caps_match(obj: Dict[str, Any], *, require_siona_native_false: bool = False) -> bool:
    if not isinstance(obj, dict):
        return False
    for key, expected in APPROVED_CAPS.items():
        if obj.get(key) != expected:
            return False
    if require_siona_native_false and obj.get("siona_native") is not False:
        return False
    return True


def derive_state_c(data: Dict[str, Any]) -> Tuple[bool, bool, bool, bool, bool, bool]:
    """Independently recompute A–E and STATE_C_VERIFIED from committed fields."""
    # A — registry record available (canonical file + exact entry)
    a = False
    if REGISTRY.is_file():
        reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
        models = reg.get("models") if isinstance(reg, dict) else None
        if isinstance(models, list):
            for entry in models:
                if not isinstance(entry, dict):
                    continue
                if (
                    entry.get("provider_id") == APPROVED_PROVIDER
                    and entry.get("model_id") == APPROVED_MODEL
                    and _caps_match(entry.get("capabilities") or {})
                    and entry.get("siona_native") is False
                ):
                    a = True
                    break

    # B — registry entry bound
    bind = data.get("pre_inference_binding") or {}
    pbind = data.get("provider_binding") or {}
    b = (
        bind.get("model_registry_entry_bound") is True
        and bind.get("provider_id") == APPROVED_PROVIDER
        and bind.get("model_id") == APPROVED_MODEL
        and bind.get("artifact_verification_status") == "verified"
        and bind.get("capability_verification_status") == "verified"
        and pbind.get("canonical_registry_path_used") is True
        and pbind.get("builder") == "build_local_provider_from_env"
        and _caps_match(bind, require_siona_native_false=True)
    )

    # C — real runtime running during experiment
    runtime = data.get("runtime") or {}
    health = data.get("health_check") or {}
    c = (
        runtime.get("startup_result") == "SUCCESS"
        and runtime.get("host") == "127.0.0.1"
        and runtime.get("port") == 8080
        and runtime.get("ctx") == 4096
        and runtime.get("threads") == 4
        and runtime.get("n_gpu_layers") == 0
        and runtime.get("reasoning") == "off"
        and health.get("ok") is True
        and health.get("http_status") == 200
        and data.get("loopback_only") is True
        and data.get("not_bound_0_0_0_0") is True
        and data.get("v1_models_approved_id_listed") is True
    )

    # D — real inference completed
    summary = data.get("inference_summary") or {}
    llama = summary.get("llama_cpp_request_evidence") or {}
    probes = data.get("probes") or []
    successful = [
        p
        for p in probes
        if isinstance(p, dict)
        and p.get("registry_entry_bound") is True
        and p.get("real_provider_call") is True
        and p.get("response_received") is True
        and p.get("fallback_used") is False
        and p.get("tool_calls_count") == 0
        and p.get("final_siona_status") == "REAL_LOCAL_RESPONSE"
    ]
    d = (
        int(summary.get("controlled_text_probes") or 0) >= 1
        and int(summary.get("real_provider_calls") or 0) >= 1
        and int(summary.get("real_model_responses") or 0) >= 1
        and summary.get("deterministic_fallback_during_live_probes") == 0
        and len(successful) >= 1
        and len(successful) == int(summary.get("real_model_responses") or -1)
        and llama.get("server_log_grew_during_probes") is True
        and int(llama.get("log_bytes_after") or 0) > int(llama.get("log_bytes_before") or 0)
    )

    # E — runtime shut down
    shutdown = data.get("shutdown") or {}
    post = data.get("post_shutdown") or {}
    e = (
        shutdown.get("success") is True
        and post.get("port_8080_status") == "CLOSED"
        and post.get("llama_cpp_status") == "STOPPED"
        and post.get("qwen_status") == "STOPPED"
        and post.get("relevant_process_count") == 0
        and post.get("local_model_unavailable") is True
        and post.get("deterministic_fallback_works") is True
        and post.get("automatic_restart_observed") is False
    )

    # Cross-cutting safety / consistency
    safety = data.get("safety") or {}
    mutation = data.get("registry_mutation") or {}
    post_caps = data.get("post_inference_capabilities") or {}
    actual_sha = _sha256_file(REGISTRY)
    tool_ok = (
        summary.get("tool_execution_count") == 0
        and safety.get("tool_execution_count") == 0
        and all(int((p or {}).get("tool_calls_count") or 0) == 0 for p in probes if isinstance(p, dict))
    )
    mutation_ok = (
        mutation.get("config_model_registry_json_mutated") is False
        and mutation.get("sha256") == actual_sha
    )
    caps_ok = _caps_match(post_caps, require_siona_native_false=True)
    zeros_ok = (
        safety.get("training_count") == 0
        and safety.get("lora_qlora_peft_count") == 0
        and safety.get("embeddings_count") == 0
        and safety.get("weight_modifications") == 0
        and safety.get("model_download_count") == 0
        and safety.get("runtime_download_count") == 0
        and safety.get("persistent_autostart_created") is False
        and safety.get("machine_wide_env_persisted") is False
        and safety.get("ssn_data_changed") is False
        and safety.get("world_model_json_changed") is False
        and safety.get("website_changed") is False
        and data.get("approved_baseline", {}).get("siona_native") is False
        and data.get("siona_native_claimed") is False
        and data.get("operator_override_allowed") is False
    )
    phase_ok = (
        data.get("adr_0003_status") == "PROPOSED"
        and data.get("phase_3b_status") == "IN_PROGRESS"
        and data.get("phase_4_status") == "NOT_STARTED"
        and data.get("remaining_blocker")
        == "ADR 0003 ACCEPTANCE + PHASE 3B COMPLETION DECISION"
    )

    verified = bool(
        a and b and c and d and e and tool_ok and mutation_ok and caps_ok and zeros_ok and phase_ok
    )
    return a, b, c, d, e, verified


class TestExp3B013StateCEvidence(unittest.TestCase):
    def test_decision_independently_recomputed(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(data["experiment_id"], "EXP-3B-013")
        self.assertFalse(data["operator_override_allowed"])

        a, b, c, d, e, verified = derive_state_c(data)
        expected = "STATE_C_VERIFIED" if verified else "STATE_C_NOT_VERIFIED"
        self.assertEqual(data["decision"], expected)
        self.assertTrue(data.get("decision_computed"))

        states = data["activation_states"]
        self.assertEqual(states["A_registry_record_available"], a)
        self.assertEqual(states["B_registry_entry_bound"], b)
        self.assertEqual(states["C_real_runtime_running_during_experiment"], c)
        self.assertEqual(states["D_real_inference_completed"], d)
        self.assertEqual(states["E_runtime_shut_down"], e)

        # Immutable historical observations remain present when verified.
        if verified:
            self.assertEqual(data["inference_summary"]["controlled_text_probes"], 2)
            self.assertEqual(data["inference_summary"]["real_provider_calls"], 2)
            self.assertEqual(data["inference_summary"]["real_model_responses"], 2)
            self.assertEqual(data["inference_summary"]["deterministic_fallback_during_live_probes"], 0)
            self.assertEqual(data["runtime"]["pid"], 4688)
            self.assertEqual(
                data["probes"][0]["full_response_sha256"],
                "d2eec60f0c989553edefd96860e14fd68a6849a7b45f1eaf3a2e421f9e4b89dc",
            )
            self.assertEqual(
                data["probes"][1]["full_response_sha256"],
                "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
            )
            self.assertEqual(data["probes"][0]["latency_ms"], 1464.8)
            self.assertEqual(data["probes"][1]["latency_ms"], 457.9)

        blob = EVIDENCE.read_text(encoding="utf-8").lower()
        self.assertNotIn("c:\\users\\", blob)
        self.assertNotIn("/users/", blob)

    def test_documentation_consistency_and_regression_guards(self):
        doc = DOC.read_text(encoding="utf-8")
        status = STATUS.read_text(encoding="utf-8")
        adr = ADR.read_text(encoding="utf-8")
        research = RESEARCH.read_text(encoding="utf-8")
        runbook = RUNBOOK.read_text(encoding="utf-8")
        current = "\n".join([doc, status, adr, research, runbook])

        self.assertIn("STATE C CONTROLLED REGISTRY-BOUND REAL-RUNTIME VERIFICATION PASSED", doc)
        self.assertIn("STATE C DOES NOT MEAN AUTOMATIC OR PERMANENT MODEL STARTUP", doc)
        self.assertIn("STATE_C_VERIFIED", doc)
        self.assertIn("EXP-3B-013", status)
        self.assertIn("State C controlled registry-bound real-runtime verification passed", status)
        self.assertIn("ADR 0003 acceptance and Phase 3B completion decision still pending", status)
        self.assertIn("Phase 4 remains **not started**", status)
        self.assertRegex(adr.replace("\r\n", "\n"), r"(?m)^## Status\n\nProposed\n")
        self.assertIn("ADR 0003 ACCEPTANCE + PHASE 3B COMPLETION DECISION", adr)
        self.assertIn("State C controlled registry-bound real-runtime verification", adr)

        # Current-state regression guards (not historical experiment chronology).
        self.assertNotIn("until that separate authorized experiment", research)
        self.assertNotIn("controlled controlled verification", research.lower())
        self.assertNotIn("registry-bound\nADR acceptance", runbook)
        self.assertNotIn("registry-bound ADR acceptance", runbook)
        self.assertNotIn(", and ADR acceptance.", runbook)
        self.assertIn(
            "`UNAPPROVED` for ADR acceptance / Phase 3B completion and for capability",
            runbook,
        )
        self.assertIn("State C controlled registry-bound real-runtime verification (EXP-3B-013)", runbook)
        self.assertIn("The runtime was shut", runbook)
        self.assertIn("down after State C", runbook)
        self.assertIn("deliberately stopped after the controlled verification", research)
        self.assertNotIn("STATE C REAL-RUNTIME VERIFICATION PENDING", current)
        # Avoid claiming State C is still pending in current-state docs.
        for banned in (
            "state C remains pending",
            "state c remains pending",
            "state C real-runtime verification not yet performed",
        ):
            self.assertNotIn(banned, current.lower())

        # Registry file still present and conservative.
        reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
        entry = reg["models"][0]
        self.assertEqual(entry["provider_id"], APPROVED_PROVIDER)
        self.assertEqual(entry["model_id"], APPROVED_MODEL)
        self.assertTrue(_caps_match(entry["capabilities"]))
        self.assertFalse(entry["siona_native"])


if __name__ == "__main__":
    unittest.main()
