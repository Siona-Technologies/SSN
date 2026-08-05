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
            # In-process for speed; subprocess path covered separately
            report = run_provider_eval(cases=cases, write_report=True, use_subprocess=False)
            self.assertEqual(report["label"], "mock/deterministic")
            self.assertEqual(report["summary"]["total"], len(cases))
            failed = [r for r in report["results"] if r["status"] != "pass"]
            self.assertEqual(
                report["summary"]["failed"],
                0,
                msg=str([(f["case_id"], f.get("actual_result")) for f in failed]),
            )
            self.assertEqual(report["summary"]["passed"], len(cases))
            self.assertIn("git_commit", report)
            self.assertIn("environment", report)
            path = Path(report["report_path"])
            self.assertTrue(path.exists())
            self.assertIn("eval_reports", str(path).replace("\\", "/"))
            # Declarative fields present
            sample = report["results"][0]
            for key in (
                "input_summary",
                "expected_constraints",
                "provider_configuration",
                "timeout_s",
                "wall_latency_ms",
                "error_category",
            ):
                self.assertIn(key, sample)

    def test_failure_reporting(self):
        from ssn.eval.provider_eval import ProviderEvalCase, HANDLERS

        def boom(inp):
            return {"ok": False, "detail": "expected fail"}

        HANDLERS["force_fail"] = boom
        case = ProviderEvalCase(
            "prov.force_fail",
            "test",
            "force fail",
            "force_fail",
        )
        try:
            with isolated_runtime_data(prefix="eval-fail-"):
                report = run_provider_eval(
                    cases=[case], write_report=False, use_subprocess=False
                )
                self.assertEqual(report["summary"]["failed"], 1)
                self.assertEqual(report["results"][0]["status"], "fail")
        finally:
            HANDLERS.pop("force_fail", None)

    def test_shadow_case_present(self):
        ids = {c.case_id for c in default_provider_cases()}
        self.assertIn("prov.shadow_no_duplicate_inference", ids)

    def test_hard_timeout_subprocess(self):
        from ssn.eval.provider_eval import _run_handler_with_timeout

        out = _run_handler_with_timeout(
            "sleep_forever", {"sleep_s": 30}, timeout_s=0.4
        )
        self.assertFalse(out.get("ok"))
        self.assertEqual(out.get("error_category"), "timeout")

    def test_declarative_case_fields(self):
        case = default_provider_cases()[0]
        self.assertTrue(case.handler_id)
        self.assertIsInstance(case.input, dict)
        self.assertIsInstance(case.expected_constraints, dict)
        self.assertGreater(case.timeout_s, 0)


if __name__ == "__main__":
    unittest.main()
