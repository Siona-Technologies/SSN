"""Offline tests for EXP-3B-008 campaign runner (mock providers only)."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ssn.cognition.model_gateway.mock_local_server import MockLocalModelServer
from ssn.core.llm_providers import LLMResponse
from ssn.governance.identity_registry import load_approved_identity_registry
from ssn.governance.runtime_context import GOVERNED_INPUT_KEY

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_SCRIPT = ROOT / "scripts" / "run_real_governed_identity_campaign.py"
EVIDENCE_DIR = Path(r"C:\Users\njaji\SIONA\reports\EXP-3B-008")


class _MockGatewayProvider:
    name = "mock-gateway-campaign"

    def complete(self, request):
        from ssn.cognition.model_gateway.contracts import ModelResponse, ModelUsage

        return ModelResponse(
            text="SIONA is the unified intelligence engine and platform developed by SIONA Technologies.",
            provider=self.name,
            usage=ModelUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            healthy=True,
            fallback_used=False,
        )


class _MockGatewayLLM:
    def __init__(self) -> None:
        self._inner = _MockGatewayProvider()

    def generate(self, request):
        resp = self._inner.complete(request)
        return LLMResponse(
            text=resp.text,
            meta={
                "engine": resp.provider,
                "used_context": False,
                "fallback_used": False,
            },
        )


class TestRealGovernedIdentityCampaign(unittest.TestCase):
    def setUp(self) -> None:
        self._env_patch = mock.patch.dict(
            os.environ,
            {
                "SSN_OFFLINE": "1",
                "SSN_ALLOW_REAL_MODEL_CAMPAIGN": "1",
                "SSN_GOVERNED_CONTEXT": "1",
                "SSN_LLM_PROVIDER": "local",
                "SSN_MODEL_PROVIDER": "local",
                "SSN_LOCAL_MODEL_API_DIALECT": "openai_chat",
                "SSN_LOCAL_MODEL_ENDPOINT": "http://127.0.0.1:8080",
                "SSN_LOCAL_MODEL_VERIFY_MODEL_ID": "1",
                "SSN_LOCAL_MODEL_ID": "mock-model",
            },
            clear=False,
        )
        self._env_patch.start()

    def tearDown(self) -> None:
        self._env_patch.stop()

    def test_campaign_flag_required(self) -> None:
        from scripts.run_real_governed_identity_campaign import run_campaign, CampaignError

        os.environ.pop("SSN_ALLOW_REAL_MODEL_CAMPAIGN", None)
        with self.assertRaises(CampaignError):
            run_campaign(skip_server_check=True)

    def test_non_loopback_endpoint_rejected(self) -> None:
        from scripts.run_real_governed_identity_campaign import run_campaign, CampaignError

        os.environ["SSN_ALLOW_REAL_MODEL_CAMPAIGN"] = "1"
        os.environ["SSN_LOCAL_MODEL_ENDPOINT"] = "http://192.168.1.10:8080"
        with self.assertRaises(CampaignError):
            run_campaign(skip_server_check=True)

    def test_explicit_selection_subset(self) -> None:
        registry = load_approved_identity_registry()
        selected = registry.select_by_subject_ids(["product:siona"])
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].subject_id, "product:siona")

    def test_no_selection_means_no_records(self) -> None:
        registry = load_approved_identity_registry()
        selected = registry.select_by_subject_ids(["org:unknown-exp-3b-008"])
        self.assertEqual(len(selected), 0)

    def test_duplicate_ids_do_not_duplicate_records(self) -> None:
        registry = load_approved_identity_registry()
        selected = registry.select_by_subject_ids(["product:siona", "product:siona"])
        self.assertEqual(len(selected), 1)

    def test_raw_evidence_path_outside_git(self) -> None:
        self.assertFalse(str(EVIDENCE_DIR).lower().startswith(str(ROOT).lower()))

    def test_summary_does_not_include_governed_block(self) -> None:
        from scripts.run_real_governed_identity_campaign import _write_evidence, ProbeRecord

        with tempfile.TemporaryDirectory() as tmp:
            record = ProbeRecord(
                probe_id="P1",
                run_index=0,
                selected_subject_ids=["product:siona"],
                governed_supplied=True,
                candidate_count=1,
                included_count=1,
                denied_count=0,
                included_ids=["product:siona"],
                used_context=True,
                provider_name="mock",
                fallback_used=False,
                model_id="mock",
                latency_ms=1.0,
                prompt_tokens=1,
                completion_tokens=1,
                total_tokens=2,
                classification="PASS_GROUNDED",
                failure_reason="",
                reply_excerpt="SIONA platform",
            )
            summary = {"records": [{"reply_excerpt": record.reply_excerpt}]}
            with mock.patch(
                "scripts.run_real_governed_identity_campaign.EVIDENCE_DIR", Path(tmp)
            ):
                _write_evidence([record], [], summary)
            body = (Path(tmp) / "campaign_summary_latest.json").read_text(encoding="utf-8")
            self.assertNotIn("governed context follows", body.lower())

    def test_no_subprocess_in_focused_tests(self) -> None:
        with mock.patch("subprocess.Popen") as popen:
            registry = load_approved_identity_registry()
            self.assertEqual(len(registry.all_records()), 3)
            popen.assert_not_called()

    def test_no_gguf_open_in_focused_tests(self) -> None:
        from ssn.governance.identity_registry import load_approved_identity_registry

        gguf = list(ROOT.rglob("*.gguf"))
        if not gguf:
            return
        path = gguf[0]
        before = path.stat().st_mtime_ns
        load_approved_identity_registry()
        self.assertEqual(path.stat().st_mtime_ns, before)

    def test_mock_campaign_run_writes_outside_git(self) -> None:
        from scripts.run_real_governed_identity_campaign import run_campaign

        os.environ["SSN_ALLOW_REAL_MODEL_CAMPAIGN"] = "1"
        os.environ["SSN_LOCAL_MODEL_ENDPOINT"] = "http://127.0.0.1:8080"
        os.environ["SSN_LOCAL_MODEL_ID"] = "mock-model"

        import scripts.run_real_governed_identity_campaign as campaign_mod

        with mock.patch("ssn.core.language_engine.LanguageEngine") as mock_engine:
            from ssn.cognition.model_gateway.contracts import ModelResponse, ModelUsage

            mock_gateway = mock.Mock()
            mock_gateway.complete.return_value = ModelResponse(
                text="SIONA is the unified intelligence engine and platform developed by SIONA Technologies.",
                provider="mock-gateway-campaign",
                usage=ModelUsage(prompt_tokens=5, completion_tokens=10, total_tokens=15),
                healthy=True,
                fallback_used=False,
            )
            instance = mock_engine.return_value
            instance.process.return_value = {
                "reply": "SIONA is the unified intelligence engine and platform developed by SIONA Technologies.",
                "used_context": True,
                "engine": "mock",
                "governed_context": {
                    "candidate_count": 1,
                    "included_count": 1,
                    "denied_count": 0,
                    "included_ids": ["product:siona"],
                    "has_context_block": True,
                },
            }
            inner = mock.Mock()
            inner._provider = mock_gateway
            instance._provider = mock.Mock()
            instance._provider._inner = inner
            with tempfile.TemporaryDirectory() as tmp:
                with mock.patch.object(campaign_mod, "EVIDENCE_DIR", Path(tmp)):
                    summary = run_campaign(skip_server_check=True)
        self.assertGreater(summary["probe_count"], 0)
        self.assertTrue(str(summary["summary_path"]).startswith(str(Path(tmp))))

    def test_tool_calls_not_enabled(self) -> None:
        source = (ROOT / "scripts" / "run_real_governed_identity_campaign.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("ToolGateway", source)
        self.assertNotIn("tool_bridge", source)


if __name__ == "__main__":
    unittest.main()
