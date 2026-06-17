# ssn/tests/test_phase47_eval_harness_smoke.py

import os
import unittest

from ssn.eval.scenarios import default_eval_scenarios
from ssn.eval.runner import build_default_eval_gateway, EvalRunner


class TestPhase47EvalHarnessSmoke(unittest.TestCase):

    def setUp(self) -> None:
        os.environ.pop("SSN_MASTER_KEY", None)

    def test_eval_harness_runs_and_passes(self):
        env = build_default_eval_gateway()
        runner = EvalRunner(env["gateway"])

        report = runner.run_all(default_eval_scenarios())

        self.assertIn("summary", report)
        self.assertEqual(report["summary"]["failed"], 0, report)

        # sanity: orchestrator got called at least once by think scenario
        orch = env["orchestrator"]
        self.assertGreaterEqual(getattr(orch, "calls", 0), 1)

    def test_eval_harness_is_deterministic(self):
        env1 = build_default_eval_gateway()
        env2 = build_default_eval_gateway()

        r1 = EvalRunner(env1["gateway"]).run_all(default_eval_scenarios())
        r2 = EvalRunner(env2["gateway"]).run_all(default_eval_scenarios())

        self.assertEqual(r1["summary"], r2["summary"])
        # Compare response snapshots at a high level
        snaps1 = [x["response_snapshot"] for x in r1["results"]]
        snaps2 = [x["response_snapshot"] for x in r2["results"]]
        self.assertEqual(snaps1, snaps2)


if __name__ == "__main__":
    unittest.main()
