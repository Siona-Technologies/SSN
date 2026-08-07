"""Phase 4A temporal-salience dataset readiness tests (no SNN training)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from ssn.cognition.neuromorphic.phase4a_dataset import (
    EVENTS_PER_SAMPLE,
    SPLIT_SIZES,
    generate_split,
    majority_baseline_balanced_accuracy,
    split_fingerprint,
    total_event_count_values,
)

ROOT = Path(__file__).resolve().parents[2]
TASK_CONFIG = ROOT / "config" / "phase4a_temporal_salience_task.json"

EXPECTED_FINGERPRINTS = {
    "train": "e124d6b5858399956f7b52f1fc6e342e9d2833704b44710315d57844c43805bd",
    "validation": "cfd32c4b9b2684dc10f21e9b28d169807c42ae54e7968d5080a676d602929285",
    "test": "34d93878277a0b6afae880c02a3b2d878fbc142a1cfee77b51985eebbf7f4116",
}


class TestPhase4ATemporalSalienceDataset(unittest.TestCase):
    def test_task_config_keeps_training_disabled(self):
        cfg = json.loads(TASK_CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(cfg["task_id"], "phase4a-temporal-salience-v1")
        self.assertEqual(cfg["status"], "READINESS_DEFINED_TRAINING_NOT_AUTHORIZED")
        self.assertFalse(cfg["training"]["authorized"])
        self.assertFalse(cfg["candidate_backend"]["dependency_installation_authorized"])
        self.assertFalse(cfg["generation"]["private_or_user_data"])
        self.assertFalse(cfg["generation"]["qwen_generated_labels"])
        self.assertEqual(cfg["candidate_backend"]["preferred_for_dependency_gate"], "snntorch")
        self.assertEqual(cfg["candidate_backend"]["preferred_version_researched"], "1.0.0")

    def test_split_sizes_balance_and_fingerprints_are_stable(self):
        for split, expected_size in SPLIT_SIZES.items():
            samples = generate_split(split)
            self.assertEqual(len(samples), expected_size)
            self.assertEqual(sum(s.label == 0 for s in samples), expected_size // 2)
            self.assertEqual(sum(s.label == 1 for s in samples), expected_size // 2)
            self.assertEqual(split_fingerprint(split), EXPECTED_FINGERPRINTS[split])

    def test_equal_event_budget_blocks_count_only_label_leakage(self):
        for split in SPLIT_SIZES:
            self.assertEqual(total_event_count_values(split), (EVENTS_PER_SAMPLE,))
            for sample in generate_split(split):
                self.assertEqual(sample.event_count, EVENTS_PER_SAMPLE)

    def test_classes_are_separated_by_temporal_distribution_not_total_count(self):
        for split in SPLIT_SIZES:
            samples = generate_split(split)
            for sample in samples:
                if sample.label == 1:
                    self.assertEqual(sample.late_event_count, 12)
                    self.assertEqual(sample.late_event_fraction, 0.75)
                else:
                    self.assertLessEqual(sample.late_event_count, 4)
                    self.assertLessEqual(sample.late_event_fraction, 0.25)

    def test_majority_balanced_accuracy_is_declared_chance_level(self):
        for split in SPLIT_SIZES:
            self.assertEqual(majority_baseline_balanced_accuracy(split), 0.5)

    def test_task_acceptance_thresholds_are_predeclared(self):
        cfg = json.loads(TASK_CONFIG.read_text(encoding="utf-8"))
        thresholds = cfg["acceptance_thresholds_for_future_authorized_training"]
        self.assertEqual(thresholds["test_balanced_accuracy_min"], 0.9)
        self.assertEqual(thresholds["per_class_recall_min"], 0.85)
        self.assertEqual(thresholds["margin_over_balanced_random_min"], 0.2)
        self.assertFalse(thresholds["live_test_set_threshold_tuning_allowed"])
        self.assertTrue(thresholds["time_reversal_sensitivity_required"])
        self.assertEqual(thresholds["time_reversal_positive_score_drop_min"], 0.1)


if __name__ == "__main__":
    unittest.main()
