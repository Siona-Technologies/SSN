"""Offline mocked tests for EXP-3B-010 guarded identity retest."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import mock

from ssn.core.language_engine import LanguageEngine
from ssn.core.llm_providers import LLMRequest, LLMResponse
from ssn.governance.guarded_identity_retest import (
    EXPECTED_PROBE_IDS,
    LOCAL_EVIDENCE_DIR,
    MAX_EXCERPT_CHARS,
    RAW_FROM_GUARDED,
    RAW_SEPARATE,
    RecordingLLMProvider,
    RetestError,
    assert_evidence_dir_outside_repo,
    build_committed_adjudication,
    build_probe_catalog,
    canonical_json_bytes,
    compute_campaign_summary,
    load_and_validate_exp_3b_010_adjudication,
    run_campaign,
    sanitize_excerpt,
    sha256_text,
    validate_campaign_environment,
    validate_probe_catalog,
)
from ssn.governance.identity_records import IdentityFactRecord
from ssn.governance.identity_response_guard import (
    ACTION_REFUSAL_TEXT,
    DISCLOSURE_REFUSAL_TEXT,
    STRUCTURED_SOURCE_FALLBACK,
    STRUCTURED_SOURCE_MODEL,
    UNAVAILABLE_TEXT,
    render_canonical_json,
    render_canonical_text,
)
from ssn.governance.information_classes import (
    AllowedUse,
    ApprovalStatus,
    InformationClass,
    SubjectType,
)
from ssn.governance.policy import PolicyContext
from ssn.governance.runtime_context import GovernedContextLLMProvider

ROOT = Path(__file__).resolve().parents[2]
WORLD_MODEL = ROOT / "ssn" / "data" / "world_model.json"
ENV = "SSN_GOVERNED_CONTEXT"

STMT_PRODUCT = (
    "SIONA is the unified intelligence engine and platform developed by "
    "SIONA Technologies."
)
STMT_COMPANY = (
    "SIONA Technologies is an African-founded technology company developing "
    "software, intelligent systems and digital infrastructure."
)
STMT_PERSON = (
    "Samson Sibona Njaji is a Kenyan software engineer and technology "
    "entrepreneur, a co-founder of SIONA Technologies, and is involved in "
    "the design and development of SIONA."
)


def _record(subject: str, subject_id: str, subject_type: SubjectType, classification: InformationClass, statement: str) -> IdentityFactRecord:
    return IdentityFactRecord(
        subject=subject,
        subject_id=subject_id,
        subject_type=subject_type,
        classification=classification,
        statement=statement,
        source_type="owner_approval",
        source_reference="test://exp-3b-010",
        approval_status=ApprovalStatus.APPROVED,
        approved_by="person:samson-sibona-njaji",
        approval_timestamp="2026-08-06T08:20:00Z",
        intended_uses=(
            AllowedUse.PUBLIC_RESPONSE,
            AllowedUse.MODEL_PROMPT,
            AllowedUse.RETRIEVAL,
        ),
        prohibited_uses=(AllowedUse.TRAINING_DATASET,),
        review_date="2027-08-06",
        revocation_status="none",
    )


def product_record() -> IdentityFactRecord:
    return _record("SIONA", "product:siona", SubjectType.PRODUCT, InformationClass.PUBLIC_COMPANY, STMT_PRODUCT)


def company_record() -> IdentityFactRecord:
    return _record(
        "SIONA Technologies",
        "company:siona-technologies",
        SubjectType.COMPANY,
        InformationClass.PUBLIC_COMPANY,
        STMT_COMPANY,
    )


def person_record() -> IdentityFactRecord:
    return _record(
        "Samson Sibona Njaji",
        "person:samson-sibona-njaji",
        SubjectType.PERSON,
        InformationClass.PUBLIC_PROFESSIONAL,
        STMT_PERSON,
    )


class _FakeRegistry:
    def __init__(self, records: Dict[str, IdentityFactRecord]) -> None:
        self._records = records

    def select_by_subject_ids(self, ids: List[str]) -> tuple:
        out = []
        seen = set()
        for sid in ids:
            if sid in seen:
                continue
            seen.add(sid)
            if sid in self._records:
                out.append(self._records[sid])
        return tuple(sorted(out, key=lambda r: r.subject_id))


class _ScriptedInner:
    name = "scripted-inner"

    def __init__(self, replies: Optional[List[str]] = None) -> None:
        self.replies = list(replies or [])
        self.calls: List[LLMRequest] = []

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        text = self.replies.pop(0) if self.replies else ""
        return LLMResponse(text=text, meta={"engine": self.name, "used_context": False})


def _registry() -> _FakeRegistry:
    return _FakeRegistry(
        {
            "product:siona": product_record(),
            "company:siona-technologies": company_record(),
            "person:samson-sibona-njaji": person_record(),
        }
    )


def _campaign_env() -> Dict[str, str]:
    return {
        "SSN_OFFLINE": "1",
        "SSN_GOVERNED_CONTEXT": "1",
        "SSN_LLM_PROVIDER": "local",
        "SSN_MODEL_PROVIDER": "local",
        "SSN_LOCAL_MODEL_API_DIALECT": "openai_chat",
        "SSN_LOCAL_MODEL_ENDPOINT": "http://127.0.0.1:8080",
        "SSN_LOCAL_MODEL_VERIFY_MODEL_ID": "1",
        "SSN_LOCAL_MODEL_MAX_TOKENS_CAP": "128",
        "ALLOW_REMOTE": "0",
        "SSN_LOCAL_MODEL_ID": "Qwen3-1.7B-Q4_K_M",
    }


class TestCatalogAndEnv(unittest.TestCase):
    def test_exact_21_probe_catalogue(self) -> None:
        catalog = build_probe_catalog()
        validate_probe_catalog(catalog)
        self.assertEqual(len(catalog), 21)
        self.assertEqual([p.probe_id for p in catalog], list(EXPECTED_PROBE_IDS))

    def test_duplicate_probe_rejected(self) -> None:
        catalog = build_probe_catalog()
        bad = list(catalog) + [catalog[0]]
        with self.assertRaises(RetestError):
            validate_probe_catalog(bad)

    def test_missing_probe_rejected(self) -> None:
        catalog = build_probe_catalog()[:-1]
        with self.assertRaises(RetestError):
            validate_probe_catalog(catalog)

    def test_unexpected_probe_rejected(self) -> None:
        catalog = list(build_probe_catalog())
        object.__setattr__(catalog[0], "probe_id", "ZX")  # frozen - will fail
        # replace instead
        from ssn.governance.guarded_identity_retest import GuardedProbeSpec

        catalog[0] = GuardedProbeSpec(
            "ZX", "positive", "x", ("product:siona",), ("product:siona",)
        )
        with self.assertRaises(RetestError):
            validate_probe_catalog(catalog)

    def test_family_mismatch_rejected(self) -> None:
        from ssn.governance.guarded_identity_retest import GuardedProbeSpec

        catalog = list(build_probe_catalog())
        catalog[0] = GuardedProbeSpec(
            "P1", "json", "What is SIONA?", ("product:siona",), ("product:siona",)
        )
        with self.assertRaises(RetestError):
            validate_probe_catalog(catalog)

    def test_campaign_flag_env_required(self) -> None:
        env = _campaign_env()
        validate_campaign_environment(env)
        env["SSN_LOCAL_MODEL_MAX_TOKENS_CAP"] = "129"
        with self.assertRaises(RetestError):
            validate_campaign_environment(env)


class TestSanitizationAndHashes(unittest.TestCase):
    def test_excerpt_cap(self) -> None:
        text = "x" * 500
        out = sanitize_excerpt(text)
        self.assertLessEqual(len(out), MAX_EXCERPT_CHARS)

    def test_contacts_urls_paths_sanitized(self) -> None:
        text = (
            "email me at a@b.com or call 555-123-4567 see https://evil.test "
            "and C:\\Users\\njaji\\SIONA\\models\\x.gguf"
        )
        out = sanitize_excerpt(text)
        self.assertNotIn("@", out)
        self.assertNotIn("https://", out)
        self.assertNotIn("C:\\Users", out)
        self.assertIn("[email]", out)
        self.assertIn("[url]", out)
        self.assertIn("[path]", out)

    def test_hashes_over_complete_text(self) -> None:
        text = "complete response body"
        self.assertEqual(sha256_text(text), hashlib.sha256(text.encode()).hexdigest())

    def test_evidence_dir_outside_git(self) -> None:
        assert_evidence_dir_outside_repo(LOCAL_EVIDENCE_DIR, ROOT)
        # Windows operator path must remain outside even on POSIX CI resolve.
        assert_evidence_dir_outside_repo(
            Path(r"C:\Users\njaji\SIONA\reports\EXP-3B-010"), ROOT
        )
        with self.assertRaises(RetestError):
            assert_evidence_dir_outside_repo(ROOT / "docs" / "evidence", ROOT)
        with tempfile.TemporaryDirectory() as td:
            assert_evidence_dir_outside_repo(Path(td), ROOT)


class TestCampaignMocked(unittest.TestCase):
    def setUp(self) -> None:
        self._wm = WORLD_MODEL.stat().st_mtime_ns if WORLD_MODEL.exists() else None
        for k, v in _campaign_env().items():
            os.environ[k] = v

    def tearDown(self) -> None:
        if self._wm is not None and WORLD_MODEL.exists():
            self.assertEqual(WORLD_MODEL.stat().st_mtime_ns, self._wm)

    def _engine_for(self, replies: List[str]):
        inner = _ScriptedInner(replies)
        recorder = RecordingLLMProvider(inner)
        raw = RecordingLLMProvider(_ScriptedInner(["raw-control"] * 50))
        engine = LanguageEngine(provider=GovernedContextLLMProvider(recorder))
        return engine, recorder, raw, inner

    def test_guarded_call_count_at_most_one_and_raw_labels(self) -> None:
        # Enough replies for provider-invoked probes; preflight uses separate raw.
        replies = [STMT_PRODUCT, STMT_COMPANY, STMT_PERSON]
        replies.append(
            "\n\n".join([STMT_COMPANY, STMT_PERSON, STMT_PRODUCT])
        )
        # JSON probes (6) — invalid then fallback
        replies.extend(['{"nope":1}'] * 6)
        engine, recorder, raw, inner = self._engine_for(replies)
        results, summary = run_campaign(
            engine=engine,
            recorder=recorder,
            registry=_registry(),
            raw_provider=raw,
        )
        self.assertEqual(len(results), 21)
        for item in results:
            self.assertLessEqual(item.guarded_provider_call_count, 1)
            self.assertLessEqual(item.raw_control_call_count, 1)
            if item.guarded_provider_call_count == 1:
                self.assertEqual(item.raw_source, RAW_FROM_GUARDED)
            elif item.guarded_provider_call_count == 0:
                self.assertIn(item.raw_source, {RAW_SEPARATE, "RAW_NOT_AVAILABLE_DUE_TO_PROVIDER_FAILURE"})
        self.assertEqual(summary["actual_tool_execution_count"], 0)
        self.assertFalse(summary["website_changed"])
        self.assertFalse(summary["registry_active"])

    def test_positive_canonical_and_selection_unavailable(self) -> None:
        replies = [
            STMT_PRODUCT,
            STMT_COMPANY,
            STMT_PERSON,
            "\n\n".join([STMT_COMPANY, STMT_PERSON, STMT_PRODUCT]),
        ] + ['{"bad":true}'] * 6
        engine, recorder, raw, _ = self._engine_for(replies)
        results, _ = run_campaign(
            engine=engine, recorder=recorder, registry=_registry(), raw_provider=raw
        )
        by_id = {r.probe_id: r for r in results}
        self.assertEqual(by_id["P1"].final_text, STMT_PRODUCT)
        self.assertEqual(by_id["P1"].operator_adjudication, "PASS")
        self.assertEqual(by_id["S1"].final_text, UNAVAILABLE_TEXT)
        self.assertEqual(by_id["S1"].guarded_provider_call_count, 0)
        self.assertEqual(by_id["U6"].final_text, ACTION_REFUSAL_TEXT)
        self.assertEqual(by_id["A2"].final_text, DISCLOSURE_REFUSAL_TEXT)
        self.assertEqual(by_id["A4"].final_text, ACTION_REFUSAL_TEXT)
        self.assertEqual(by_id["N2"].final_text, UNAVAILABLE_TEXT)
        self.assertEqual(by_id["N2"].guarded_provider_call_count, 0)

    def test_json_model_validated_vs_fallback(self) -> None:
        good = render_canonical_json((product_record(),), ("product:siona",))
        replies = [
            STMT_PRODUCT,
            STMT_COMPANY,
            STMT_PERSON,
            "\n\n".join([STMT_COMPANY, STMT_PERSON, STMT_PRODUCT]),
            good,
            good,
            render_canonical_json((company_record(),), ("company:siona-technologies",)),
            render_canonical_json((company_record(),), ("company:siona-technologies",)),
            render_canonical_json((person_record(),), ("person:samson-sibona-njaji",)),
            "not-json",
        ]
        engine, recorder, raw, _ = self._engine_for(replies)
        results, summary = run_campaign(
            engine=engine, recorder=recorder, registry=_registry(), raw_provider=raw
        )
        by_id = {r.probe_id: r for r in results}
        self.assertEqual(by_id["J1A"].answer_quality_result, "MODEL_VALIDATED")
        self.assertEqual(by_id["J1A"].structured_source, STRUCTURED_SOURCE_MODEL)
        self.assertEqual(by_id["J3B"].answer_quality_result, "DETERMINISTIC_GUARD_FALLBACK")
        self.assertEqual(by_id["J3B"].structured_source, STRUCTURED_SOURCE_FALLBACK)
        self.assertFalse(summary["pinned_baseline_model_native_json_verified"])

    def test_acceptance_false_when_one_fails(self) -> None:
        replies = [
            STMT_PRODUCT,
            STMT_COMPANY,
            STMT_PERSON,
            "\n\n".join([STMT_COMPANY, STMT_PERSON, STMT_PRODUCT]),
        ] + [
            render_canonical_json((product_record(),), ("product:siona",)),
            render_canonical_json((product_record(),), ("product:siona",)),
            render_canonical_json((company_record(),), ("company:siona-technologies",)),
            render_canonical_json((company_record(),), ("company:siona-technologies",)),
            render_canonical_json((person_record(),), ("person:samson-sibona-njaji",)),
            render_canonical_json((person_record(),), ("person:samson-sibona-njaji",)),
        ]
        engine, recorder, raw, _ = self._engine_for(replies)
        results, summary = run_campaign(
            engine=engine, recorder=recorder, registry=_registry(), raw_provider=raw
        )
        self.assertTrue(summary["guarded_campaign_acceptance_met"])
        # Mutate one guarded final adjudication to prove acceptance cannot stay true.
        results[0].operator_adjudication = "FAIL"
        results[0].answer_quality_result = "NOT_CANONICAL"
        bad_summary = compute_campaign_summary(results)
        self.assertFalse(bad_summary["guarded_campaign_acceptance_met"])
        self.assertIn("P1", bad_summary["guarded_failure_probe_ids"])
        adjudication = build_committed_adjudication(results, bad_summary)
        with self.assertRaises(RetestError):
            adjudication["guarded_campaign_acceptance_met"] = True
            load_and_validate_exp_3b_010_adjudication(adjudication)

    def test_committed_adjudication_validates(self) -> None:
        replies = [
            STMT_PRODUCT,
            STMT_COMPANY,
            STMT_PERSON,
            "\n\n".join([STMT_COMPANY, STMT_PERSON, STMT_PRODUCT]),
        ] + [
            render_canonical_json((product_record(),), ("product:siona",)),
            render_canonical_json((product_record(),), ("product:siona",)),
            render_canonical_json((company_record(),), ("company:siona-technologies",)),
            render_canonical_json((company_record(),), ("company:siona-technologies",)),
            render_canonical_json((person_record(),), ("person:samson-sibona-njaji",)),
            render_canonical_json((person_record(),), ("person:samson-sibona-njaji",)),
        ]
        engine, recorder, raw, _ = self._engine_for(replies)
        results, summary = run_campaign(
            engine=engine, recorder=recorder, registry=_registry(), raw_provider=raw
        )
        adjudication = build_committed_adjudication(results, summary)
        summary_sha = hashlib.sha256(canonical_json_bytes(summary)).hexdigest()
        adjudication["summary_sha256"] = summary_sha
        manifest = {
            "experiment_id": "EXP-3B-010",
            "complete_responses_retained_locally": True,
        }
        adjudication["manifest_sha256"] = hashlib.sha256(
            canonical_json_bytes(manifest)
        ).hexdigest()
        out = load_and_validate_exp_3b_010_adjudication(
            adjudication, manifest=manifest, summary=summary
        )
        self.assertTrue(out["ok"])
        self.assertTrue(summary["guarded_campaign_acceptance_met"])
        self.assertTrue(summary["pinned_baseline_model_native_json_verified"])
        blob = json.dumps(adjudication)
        self.assertNotIn("tool_arguments", blob)
        self.assertNotIn(STMT_PRODUCT * 2, blob)  # complete statements may appear in 240 excerpts; ensure no raw_text key
        self.assertNotIn('"raw_text"', blob)
        self.assertNotIn('"final_text"', blob)

    def test_confirm_flag_required_in_script(self) -> None:
        import scripts.run_real_guarded_identity_retest as runner

        code = runner.main([])
        self.assertEqual(code, 1)

    def test_no_network_subprocess_gguf_data(self) -> None:
        with mock.patch("urllib.request.urlopen") as urlopen:
            sanitize_excerpt("hello")
            urlopen.assert_not_called()
        with mock.patch("subprocess.Popen") as popen:
            build_probe_catalog()
            popen.assert_not_called()
        # No GGUF open
        ggufs = list(ROOT.rglob("*.gguf"))
        if ggufs:
            before = ggufs[0].stat().st_mtime_ns
            sanitize_excerpt("x")
            self.assertEqual(ggufs[0].stat().st_mtime_ns, before)


class TestNoRegistryAutoload(unittest.TestCase):
    def test_n2_no_registry_load_during_guard_flow(self) -> None:
        for k, v in _campaign_env().items():
            os.environ[k] = v
        replies = [
            STMT_PRODUCT,
            STMT_COMPANY,
            STMT_PERSON,
            "\n\n".join([STMT_COMPANY, STMT_PERSON, STMT_PRODUCT]),
        ] + [
            render_canonical_json((product_record(),), ("product:siona",)),
            render_canonical_json((product_record(),), ("product:siona",)),
            render_canonical_json((company_record(),), ("company:siona-technologies",)),
            render_canonical_json((company_record(),), ("company:siona-technologies",)),
            render_canonical_json((person_record(),), ("person:samson-sibona-njaji",)),
            render_canonical_json((person_record(),), ("person:samson-sibona-njaji",)),
        ]
        inner = _ScriptedInner(replies)
        recorder = RecordingLLMProvider(inner)
        raw = RecordingLLMProvider(_ScriptedInner(["raw"] * 50))
        engine = LanguageEngine(provider=GovernedContextLLMProvider(recorder))
        with mock.patch(
            "ssn.governance.identity_registry.load_approved_identity_registry"
        ) as load_fn:
            # Campaign supplies registry explicitly; guard must not auto-load.
            results, _ = run_campaign(
                engine=engine,
                recorder=recorder,
                registry=_registry(),
                raw_provider=raw,
            )
            load_fn.assert_not_called()
        self.assertEqual(results[-6].probe_id[0], "J")  # still ran JSON
        n2 = next(r for r in results if r.probe_id == "N2")
        self.assertEqual(n2.guarded_provider_call_count, 0)


if __name__ == "__main__":
    unittest.main()
