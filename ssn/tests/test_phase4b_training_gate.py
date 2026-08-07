"""Phase 4B first CPU SNN training-gate regression tests (no training stack)."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "config" / "phase4b_cpu_snn_training_plan.json"
GATE = ROOT / "docs" / "PHASE_4B_FIRST_CPU_SNN_TRAINING_GATE.md"
RUNNER = ROOT / "scripts" / "run_phase4b_cpu_snn_training.py"
REQUIREMENTS = ROOT / "requirements.txt"
ADR4 = ROOT / "docs" / "adr" / "0004-learned-neuromorphic-backend-strategy.md"


class TestPhase4BTrainingGate(unittest.TestCase):
    def test_frozen_plan(self):
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        self.assertEqual(plan["execution_experiment_id"], "EXP-4-003")
        self.assertEqual(plan["task_id"], "phase4a-temporal-salience-v1")
        self.assertEqual(plan["environment"]["required_python"], "3.11.x 64-bit")
        self.assertEqual(plan["environment"]["torch"]["version"], "2.13.0+cpu")
        self.assertEqual(plan["environment"]["snntorch"]["version"], "1.0.0")
        self.assertFalse(plan["execution"]["cuda_allowed"])
        self.assertTrue(plan["execution"]["cpu_only"])
        self.assertFalse(plan["execution"]["hosted_ci_training_allowed"])
        self.assertTrue(plan["execution"]["one_controlled_training_run_authorized_after_merge"])
        self.assertTrue(plan["environment"]["project_requirements_file_must_remain_unchanged"])
        self.assertNotIn("if_python_3_11_unavailable", plan["environment"])

        model = plan["model"]
        self.assertEqual(model["architecture_id"], "phase4b-lif-final-membrane-v1")
        self.assertEqual(model["input_features"], 8)
        self.assertEqual(model["hidden_units"], 16)
        self.assertEqual(model["output_classes"], 2)
        self.assertEqual(model["timesteps"], 20)
        self.assertEqual(model["beta"], 0.9)
        self.assertEqual(model["threshold"], 1.0)
        self.assertEqual(model["surrogate_slope"], 25.0)
        self.assertFalse(model["learn_beta"])
        self.assertFalse(model["learn_threshold"])

        training = plan["training"]
        self.assertEqual(training["seed"], 42007)
        self.assertEqual(training["batch_size"], 32)
        self.assertEqual(training["max_epochs"], 80)
        self.assertEqual(training["learning_rate"], 0.01)
        self.assertEqual(training["weight_decay"], 0.0001)
        self.assertEqual(training["gradient_clip_norm"], 1.0)
        self.assertEqual(training["max_wall_clock_seconds"], 600)
        self.assertEqual(training["test_evaluations_allowed"], 1)
        self.assertFalse(training["test_tuning_allowed"])
        self.assertTrue(training["torch_deterministic_algorithms"])

    def test_python_bootstrap_gate_is_controlled_and_narrow(self):
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        bootstrap = plan["environment"]["python_bootstrap"]
        self.assertTrue(bootstrap["allowed_if_missing"])
        self.assertTrue(bootstrap["one_controlled_installation"])
        self.assertEqual(bootstrap["required_family"], "CPython")
        self.assertEqual(bootstrap["required_version"], "3.11.x")
        self.assertEqual(bootstrap["required_architecture"], "x64")
        self.assertEqual(bootstrap["preferred_package_manager"], "winget")
        self.assertEqual(bootstrap["package_id"], "Python.Python.3.11")
        self.assertEqual(bootstrap["scope"], "user")
        self.assertTrue(bootstrap["side_by_side_only"])
        self.assertFalse(bootstrap["may_uninstall_existing_python"])
        self.assertFalse(bootstrap["may_modify_qgis_python"])
        self.assertFalse(bootstrap["may_manually_edit_path"])
        self.assertFalse(bootstrap["may_change_global_default_python"])
        self.assertTrue(bootstrap["verify_python_launcher_registration"])
        self.assertTrue(bootstrap["verify_existing_python314_still_available"])
        self.assertTrue(bootstrap["training_may_resume_only_after_verification"])
        self.assertTrue(bootstrap["bootstrap_does_not_consume_training_run"])

        gate = GATE.read_text(encoding="utf-8")
        self.assertIn("Python.Python.3.11", gate)
        self.assertIn("one controlled side-by-side", gate.lower())
        self.assertIn("does **not** consume the EXP-4-003 training", gate)
        self.assertIn("preserve existing Python 3.14", gate)
        self.assertIn("preserve QGIS Python", gate)
        self.assertIn("avoid manual PATH edits", gate)
        self.assertNotIn("STOP_DO_NOT_INSTALL_PYTHON_AUTOMATICALLY", gate)

    def test_acceptance_thresholds_remain_predeclared(self):
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        gate = plan["acceptance"]
        self.assertEqual(gate["test_balanced_accuracy_min"], 0.9)
        self.assertEqual(gate["per_class_recall_min"], 0.85)
        self.assertEqual(gate["margin_over_balanced_random_min"], 0.2)
        self.assertEqual(gate["balanced_random_baseline"], 0.5)
        self.assertEqual(gate["time_reversal_positive_score_drop_min"], 0.1)
        self.assertFalse(gate["tool_authority"])
        self.assertFalse(gate["physical_actuation_authority"])

    def test_project_requirements_stay_training_stack_free(self):
        text = REQUIREMENTS.read_text(encoding="utf-8").lower()
        for package in ("torch", "torchvision", "snntorch", "norse"):
            self.assertNotIn(package, text)

    def test_runner_plan_validation_needs_no_training_dependency(self):
        proc = subprocess.run(
            [sys.executable, str(RUNNER), "--validate-plan"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["plan_valid"])
        self.assertFalse(payload["training_executed"])
        self.assertEqual(payload["experiment_id"], "EXP-4-003")

    def test_gate_is_historical_one_run_authorization_and_keeps_authority_separate(self):
        text = GATE.read_text(encoding="utf-8")
        lower = text.lower()
        self.assertIn("one controlled", lower)
        self.assertIn("cpu training/evaluation run", lower)
        self.assertIn("does not accept adr 0004", lower)
        self.assertIn("does not integrate the learned checkpoint", lower)
        self.assertIn("no operator override", lower)
        self.assertIn("qwen fine-tuning", lower)
        self.assertIn("physical actuation", lower)
        self.assertIn("project `requirements.txt` was not changed", text)

    def test_current_adr4_is_accepted_without_rewriting_historical_gate(self):
        adr = ADR4.read_text(encoding="utf-8")
        status = adr.replace("\r\n", "\n").split("## Status", 1)[1].split("## Context", 1)[0]
        self.assertIn("Accepted (Phase 4)", status)
        self.assertNotRegex(status, r"(?m)^\s*Proposed\s*$")
        gate = GATE.read_text(encoding="utf-8")
        self.assertIn("does not accept ADR 0004", gate)


if __name__ == "__main__":
    unittest.main()
