"""Phase 3A — provider evaluation harness tests."""

from __future__ import annotations

import json
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
            path = Path(report["report_path"])
            self.assertTrue(path.exists())

    def test_cancellation_case_names_honest(self):
        cases = {c.case_id: c for c in default_provider_cases()}
        self.assertIn("prov.cancellation_before_network", cases)
        self.assertNotIn("prov.cancellation_during", cases)
        desc = cases["prov.cancellation_before_network"].description.lower()
        self.assertIn("before network", desc)
        self.assertIn("no mid-request cancel", desc)
        self.assertTrue(
            cases["prov.cancellation_before_network"].expected_constraints.get("pre_network_only")
        )
        self.assertIn("prov.in_progress_timeout", cases)

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

    def test_subprocess_result_repeated(self):
        from ssn.eval.provider_eval import _run_handler_with_timeout

        for _ in range(3):
            out = _run_handler_with_timeout("health_ok", {}, timeout_s=5.0)
            self.assertTrue(out.get("ok"), msg=str(out))
            out_t = _run_handler_with_timeout(
                "sleep_forever", {"sleep_s": 30}, timeout_s=0.3
            )
            self.assertEqual(out_t.get("error_category"), "timeout")

    def test_report_redacts_secrets(self):
        from ssn.eval.provider_eval import ProviderEvalCase, HANDLERS

        secret = "REPORT_SECRET_VALUE_SHOULD_NEVER_APPEAR_9z"

        def leaky(inp):
            return {
                "ok": True,
                "detail": f"saw {inp.get('secret')}",
                "master_key": secret,
            }

        HANDLERS["leaky_report"] = leaky
        case = ProviderEvalCase(
            "prov.leaky",
            "security",
            "report redaction",
            "leaky_report",
            input={"secret": secret, "prompt": f"master_key={secret}"},
            provider_configuration={"api_key": secret},
            expected_constraints={"token": secret},
            thresholds={"password": secret},
        )
        try:
            with isolated_runtime_data(prefix="eval-redact-"):
                report = run_provider_eval(
                    cases=[case], write_report=True, use_subprocess=False
                )
                blob = json.dumps(report, default=str)
                raw = Path(report["report_path"]).read_bytes()
                self.assertNotIn(secret, blob)
                self.assertNotIn(secret.encode("utf-8"), raw)
                self.assertNotIn(secret, str(report.get("results")))
        finally:
            HANDLERS.pop("leaky_report", None)

    def test_declarative_case_fields(self):
        case = default_provider_cases()[0]
        self.assertTrue(case.handler_id)
        self.assertIsInstance(case.input, dict)
        self.assertIsInstance(case.expected_constraints, dict)
        self.assertGreater(case.timeout_s, 0)


if __name__ == "__main__":
    unittest.main()
