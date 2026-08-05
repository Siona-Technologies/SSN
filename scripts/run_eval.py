#!/usr/bin/env python3
"""
Run SIONA eval scenarios (offline-safe).

Usage:
  SSN_OFFLINE=1 python scripts/run_eval.py
  SSN_OFFLINE=1 python scripts/run_eval.py --production
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    os.environ.setdefault("SSN_OFFLINE", "1")
    # Eval must not pick up a real master key from the developer environment.
    os.environ.pop("SSN_MASTER_KEY", None)

    from ssn.runtime.paths import cleanup_ensured_isolation, ensure_isolated_for_tests

    ensure_isolated_for_tests()
    try:
        return _main_body()
    finally:
        cleanup_ensured_isolation()


def _main_body() -> int:
    parser = argparse.ArgumentParser(description="Run SIONA eval scenarios")
    parser.add_argument(
        "--production",
        action="store_true",
        help="Also run production runtime scenarios (SSNRuntimeBuilder)",
    )
    parser.add_argument(
        "--provider",
        action="store_true",
        help="Also run Phase 3A provider-oriented evaluation cases (deterministic/mock)",
    )
    args = parser.parse_args()

    from ssn.eval.runner import EvalRunner, build_default_eval_gateway, build_production_eval_gateway
    from ssn.eval.scenarios import default_eval_scenarios, production_eval_scenarios

    scenarios = list(default_eval_scenarios())
    env = build_default_eval_gateway()
    runner = EvalRunner(env["gateway"])
    report = runner.run_all(scenarios)

    if args.production:
        prod_env = build_production_eval_gateway()
        prod_runner = EvalRunner(prod_env["gateway"])
        prod_report = prod_runner.run_all(production_eval_scenarios())
        report["results"].extend(prod_report["results"])
        report["summary"]["total"] += prod_report["summary"]["total"]
        report["summary"]["passed"] += prod_report["summary"]["passed"]
        report["summary"]["failed"] += prod_report["summary"]["failed"]

    if args.provider:
        from ssn.eval.provider_eval import run_provider_eval

        prov = run_provider_eval()
        report["provider_eval"] = {
            "summary": prov.get("summary"),
            "label": prov.get("label"),
            "commit": prov.get("git_commit"),
        }
        report["summary"]["provider_total"] = prov["summary"]["total"]
        report["summary"]["provider_passed"] = prov["summary"]["passed"]
        report["summary"]["provider_failed"] = prov["summary"]["failed"]
        report["summary"]["provider_skipped"] = prov["summary"]["skipped"]
        if prov["summary"]["failed"]:
            print(json.dumps(prov["summary"], indent=2))
            failed = [r for r in prov["results"] if r.get("status") == "fail"]
            print(json.dumps(failed, indent=2, default=str))
            return 1

    print(json.dumps(report["summary"], indent=2))
    failed = [r for r in report["results"] if not r["passed"]]
    if failed:
        print(json.dumps(failed, indent=2, default=str))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
