"""Phase 3A — provider evaluation harness tests."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("SSN_OFFLINE", "1")

from ssn.eval.provider_eval import default_provider_cases, run_provider_eval
from ssn.runtime.paths import isolated_runtime_data


class TestProviderEval(unittest.TestCase):
    def test_deterministic_totals_and_stable_ids(self):
        with isolated_runtime_data(prefix="eval-"):
            cases = default_provider_cases()
            ids = [c.case_id for c in cases]
            self.assertEqual(len(ids), len(set(ids)))
            report = run_provider_eval(cases=cases, write_report=True)
            self.assertEqual(report["label"], "mock/deterministic")
            self.assertEqual(report["summary"]["total"], len(cases))
            self.assertEqual(report["summary"]["failed"], 0)
            self.assertEqual(report["summary"]["passed"], len(cases))
            self.assertIn("git_commit", report)
            self.assertIn("environment", report)
            path = Path(report["report_path"])
            self.assertTrue(path.exists())
            # Report is under isolated eval dir, not tracked repo artifacts by default
            self.assertIn("eval_reports", str(path).replace("\\", "/"))

    def test_failure_reporting(self):
        from ssn.eval.provider_eval import ProviderEvalCase

        def boom():
            return {"ok": False, "detail": "expected fail"}

        case = ProviderEvalCase("prov.force_fail", "test", "force fail", boom)
        with isolated_runtime_data(prefix="eval-fail-"):
            report = run_provider_eval(cases=[case], write_report=False)
            self.assertEqual(report["summary"]["failed"], 1)
            self.assertEqual(report["results"][0]["status"], "fail")

    def test_shadow_case_present(self):
        ids = {c.case_id for c in default_provider_cases()}
        self.assertIn("prov.shadow_no_duplicate_inference", ids)


if __name__ == "__main__":
    unittest.main()
