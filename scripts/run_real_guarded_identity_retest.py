#!/usr/bin/env python3
"""
EXP-3B-010 — controlled real-Qwen guarded-path retest runner.

Modes (mutually exclusive):
  --confirm-real-model-campaign
      Start pinned llama.cpp, run the 21-probe campaign once, retain local
      complete evidence, verify shutdown, then write committed evidence.
  --regenerate-committed-evidence-from-local
      Offline only: validate retained local evidence and regenerate committed
      adjudication/summary/manifest. No network, subprocess, or GGUF access.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ssn.governance.exp_3b_010_integrity import (
    HASH_SEMANTICS,
    OPERATOR_LOCAL_LABEL,
    canonical_object_sha256,
)
from ssn.governance.guarded_identity_retest import (
    ALLOWED_ENDPOINT,
    EXPECTED_MODEL_SHA256,
    EXPECTED_MODEL_SIZE,
    EXPERIMENT_ID,
    LOCAL_EVIDENCE_DIR,
    MAX_OUTPUT_TOKENS,
    MODEL_PATH,
    REQUIRED_ENV,
    RUNTIME_DIR,
    RUNTIME_EXE,
    RUNTIME_SOURCE_COMMIT,
    RUNTIME_VERSION,
    RecordingLLMProvider,
    RetestError,
    build_committed_adjudication,
    build_probe_catalog,
    check_server_model_id,
    compute_campaign_summary,
    load_and_validate_exp_3b_010_adjudication,
    load_and_validate_local_exp_3b_010_evidence,
    run_campaign,
    validate_campaign_environment,
    validate_probe_catalog,
    validate_single_server_model_id,
    verify_model_artifact,
    verify_runtime_executable,
    write_local_evidence,
)

COMMITTED_EVIDENCE_DIR = ROOT / "docs" / "evidence"
PROCESS_PATTERNS = ("llama-server", "llama.cpp", "qwen")


def _port_open(host: str = "127.0.0.1", port: int = 8080) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def _process_matches(patterns: tuple[str, ...] = PROCESS_PATTERNS) -> bool:
    try:
        out = subprocess.check_output(
            ["tasklist"], text=True, stderr=subprocess.DEVNULL
        )
    except Exception:
        try:
            out = subprocess.check_output(
                ["ps", "-A", "-o", "comm="], text=True, stderr=subprocess.DEVNULL
            )
        except Exception:
            return False
    lower = out.lower()
    return any(p.lower() in lower for p in patterns)


def _require_clean_runtime() -> None:
    if _port_open():
        raise RetestError("port_8080_already_listening")
    if _process_matches():
        raise RetestError("preexisting_model_process")


def _set_campaign_env(model_id: str) -> None:
    os.environ["SSN_OFFLINE"] = "1"
    for key, value in REQUIRED_ENV.items():
        os.environ[key] = value
    os.environ["SSN_LOCAL_MODEL_MAX_TOKENS"] = str(MAX_OUTPUT_TOKENS)
    os.environ["SSN_LOCAL_MODEL_TIMEOUT_SECONDS"] = "30"
    os.environ["SSN_LOCAL_MODEL_ID"] = model_id
    os.environ["SSN_ALLOW_REAL_MODEL_CAMPAIGN"] = "1"


def _start_llama_server(log_path: Path) -> subprocess.Popen:
    verify_runtime_executable()
    verify_model_artifact()
    cmd = [
        str(RUNTIME_EXE),
        "-m",
        str(MODEL_PATH),
        "--host",
        "127.0.0.1",
        "--port",
        "8080",
        "-c",
        "4096",
        "-n",
        "128",
        "-ngl",
        "0",
        "-t",
        "4",
        "--reasoning",
        "off",
    ]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_fh = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        cwd=str(RUNTIME_DIR),
        stdout=log_fh,
        stderr=subprocess.STDOUT,
    )
    proc._ssn_log_fh = log_fh  # type: ignore[attr-defined]
    deadline = time.time() + 90
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RetestError("llama_server_exited_early")
        if _port_open():
            try:
                with urllib.request.urlopen(
                    ALLOWED_ENDPOINT + "/health", timeout=2
                ) as resp:
                    if resp.status == 200:
                        return proc
            except Exception:
                try:
                    with urllib.request.urlopen(
                        ALLOWED_ENDPOINT + "/v1/models", timeout=2
                    ) as resp:
                        if resp.status == 200:
                            return proc
                except Exception:
                    pass
        time.sleep(1.0)
    raise RetestError("llama_server_start_timeout")


def _stop_llama_server(proc: Optional[subprocess.Popen], log_path: Path) -> str:
    method = "graceful"
    exit_code: Optional[int] = None
    if proc is None:
        method = "not_started"
    else:
        try:
            proc.terminate()
            try:
                exit_code = proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                method = "forced_after_bounded_graceful_wait"
                proc.kill()
                exit_code = proc.wait(timeout=10)
        finally:
            fh = getattr(proc, "_ssn_log_fh", None)
            if fh is not None:
                try:
                    fh.close()
                except Exception:
                    pass

    deadline = time.time() + 15
    while time.time() < deadline:
        if not _port_open() and not _process_matches():
            break
        time.sleep(0.5)

    process_stopped = not _process_matches()
    port_closed = not _port_open()
    if not process_stopped:
        raise RetestError("model_process_still_running_after_shutdown")
    if not port_closed:
        raise RetestError("port_8080_still_open_after_shutdown")

    payload = {
        "shutdown_method": method,
        "process_exit_code": exit_code,
        "process_stopped": True,
        "port_8080_closed": True,
        "verification_timestamp_utc": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return method


def _write_committed_evidence(
    results: Any,
    summary: Dict[str, Any],
    *,
    timestamp_utc: Optional[str] = None,
) -> Dict[str, str]:
    COMMITTED_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    ts = timestamp_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    adjudication = build_committed_adjudication(results, summary, timestamp_utc=ts)
    summary_doc = dict(summary)
    summary_doc["timestamp_utc"] = ts
    summary_doc["runtime_version"] = RUNTIME_VERSION
    summary_doc["runtime_source_commit"] = RUNTIME_SOURCE_COMMIT
    summary_doc["model_filename"] = MODEL_PATH.name
    summary_doc["model_size"] = EXPECTED_MODEL_SIZE
    summary_doc["model_sha256"] = EXPECTED_MODEL_SHA256
    summary_doc["server_model_id_count_validated"] = True
    summary_doc["provider_bound_to_server_reported_model_id"] = True
    summary_doc["server_model_id_independent_expected_match_verified"] = False
    summary_doc["model_artifact_size_sha256_verified"] = True
    summary_doc["hash_semantics"] = HASH_SEMANTICS

    adjudication_canonical_sha256 = canonical_object_sha256(adjudication)
    summary_canonical_sha256 = canonical_object_sha256(summary_doc)
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "evidence_directory": "docs/evidence",
        "complete_responses_retained_locally": True,
        "complete_responses_committed": False,
        "committed_response_type": "SANITIZED_TRUNCATED_RESPONSE_EXCERPTS",
        "committed_excerpt_limit": 240,
        "adjudication_scope": summary["adjudication_scope"],
        "local_complete_evidence_location": OPERATOR_LOCAL_LABEL,
        "hash_semantics": HASH_SEMANTICS,
        "files": [
            {
                "filename": "EXP-3B-010_ADJUDICATION.json",
                "evidence_type": "SANITIZED_TRUNCATED_RESPONSE_EXCERPTS",
            },
            {
                "filename": "EXP-3B-010_SUMMARY.json",
                "evidence_type": "CAMPAIGN_SUMMARY",
            },
            {
                "filename": "EXP-3B-010_EVIDENCE_MANIFEST.json",
                "evidence_type": "EVIDENCE_MANIFEST",
            },
        ],
        "adjudication_canonical_sha256": adjudication_canonical_sha256,
        "summary_canonical_sha256": summary_canonical_sha256,
    }
    manifest_canonical_sha256 = canonical_object_sha256(manifest)

    paths = {
        "adjudication": COMMITTED_EVIDENCE_DIR / "EXP-3B-010_ADJUDICATION.json",
        "summary": COMMITTED_EVIDENCE_DIR / "EXP-3B-010_SUMMARY.json",
        "manifest": COMMITTED_EVIDENCE_DIR / "EXP-3B-010_EVIDENCE_MANIFEST.json",
    }
    paths["adjudication"].write_text(
        json.dumps(adjudication, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    paths["summary"].write_text(
        json.dumps(summary_doc, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    paths["manifest"].write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    load_and_validate_exp_3b_010_adjudication(
        adjudication, manifest=manifest, summary=summary_doc
    )
    return {
        "adjudication_canonical_sha256": adjudication_canonical_sha256,
        "summary_canonical_sha256": summary_canonical_sha256,
        "manifest_canonical_sha256": manifest_canonical_sha256,
        "hash_semantics": HASH_SEMANTICS,
    }


def regenerate_committed_evidence_from_local() -> int:
    """Offline regeneration — no network, subprocess, or GGUF access."""
    validate_probe_catalog(build_probe_catalog())
    local = load_and_validate_local_exp_3b_010_evidence(LOCAL_EVIDENCE_DIR)
    results = local["results"]
    summary = compute_campaign_summary(results)

    # Preserve historical campaign timestamp when present locally.
    timestamp_utc = "2026-08-06T12:33:22Z"
    summary_path = LOCAL_EVIDENCE_DIR / "campaign_summary_latest.json"
    if summary_path.is_file():
        try:
            prior = json.loads(summary_path.read_text(encoding="utf-8"))
            if type(prior.get("timestamp_utc")) is str and prior["timestamp_utc"]:
                timestamp_utc = prior["timestamp_utc"]
        except Exception:
            pass

    hashes = _write_committed_evidence(
        results, summary, timestamp_utc=timestamp_utc
    )
    out = {
        "mode": "regenerate_committed_evidence_from_local",
        "guarded_campaign_acceptance_met": summary["guarded_campaign_acceptance_met"],
        "pinned_baseline_model_native_json_verified": summary[
            "pinned_baseline_model_native_json_verified"
        ],
        "guarded_pass_count": summary["guarded_pass_count"],
        "guarded_failure_count": summary["guarded_failure_count"],
        "preserved_raw_hashes": 21,
        "preserved_final_hashes": 21,
        **hashes,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if summary["guarded_campaign_acceptance_met"] else 2


def run_real_campaign() -> int:
    validate_probe_catalog(build_probe_catalog())
    LOCAL_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    startup_log = LOCAL_EVIDENCE_DIR / "local_runtime_startup.log"
    shutdown_log = LOCAL_EVIDENCE_DIR / "local_runtime_shutdown.log"

    proc: Optional[subprocess.Popen] = None
    results = None
    summary: Optional[Dict[str, Any]] = None
    model_info: Optional[Dict[str, Any]] = None
    campaign_error: Optional[BaseException] = None

    try:
        _require_clean_runtime()
        model_info = verify_model_artifact()
        verify_runtime_executable()
        proc = _start_llama_server(startup_log)
        # Single-ID validation + provider binding only (no self-comparison).
        model_id = validate_single_server_model_id(ALLOWED_ENDPOINT)
        check_server_model_id(ALLOWED_ENDPOINT)  # re-check single-ID binding surface
        _set_campaign_env(model_id)
        validate_campaign_environment()

        from ssn.core.language_engine import LanguageEngine
        from ssn.core.llm_providers import get_default_provider_from_env
        from ssn.governance.identity_registry import load_approved_identity_registry
        from ssn.governance.runtime_context import GovernedContextLLMProvider

        registry = load_approved_identity_registry()
        inner = get_default_provider_from_env()
        recorder = RecordingLLMProvider(inner)
        raw_recorder = RecordingLLMProvider(inner)
        engine = LanguageEngine(provider=GovernedContextLLMProvider(recorder))

        results, summary = run_campaign(
            engine=engine,
            recorder=recorder,
            registry=registry,
            raw_provider=raw_recorder,
        )
        env_snapshot = {
            "endpoint": ALLOWED_ENDPOINT,
            "model_id_present": True,
            "model_size": model_info["size"],
            "model_sha256": model_info["sha256"],
            "runtime_version": RUNTIME_VERSION,
            "runtime_source_commit": RUNTIME_SOURCE_COMMIT,
            "ssn_offline": "1",
            "max_tokens_cap": str(MAX_OUTPUT_TOKENS),
            "server_model_id_independent_expected_match_verified": False,
            "model_artifact_size_sha256_verified": True,
        }
        write_local_evidence(
            results, summary, evidence_dir=LOCAL_EVIDENCE_DIR, env_snapshot=env_snapshot
        )
    except BaseException as exc:
        campaign_error = exc

    # Shutdown must run and be verified before committed evidence may be written.
    try:
        shutdown_method = _stop_llama_server(proc, shutdown_log)
        print(f"shutdown_method={shutdown_method}", file=sys.stderr)
    except Exception as exc:
        print(f"CAMPAIGN_FAILED:shutdown:{type(exc).__name__}", file=sys.stderr)
        return 1

    if campaign_error is not None:
        if isinstance(campaign_error, RetestError):
            print(f"CAMPAIGN_FAILED:{campaign_error}", file=sys.stderr)
        else:
            print(
                f"CAMPAIGN_FAILED:{type(campaign_error).__name__}:{campaign_error}",
                file=sys.stderr,
            )
        return 1

    assert results is not None and summary is not None
    hashes = _write_committed_evidence(results, summary)
    summary_out = dict(summary)
    summary_out.update(hashes)
    print(json.dumps(summary_out, indent=2, ensure_ascii=False))
    return 0 if summary["guarded_campaign_acceptance_met"] else 2


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="EXP-3B-010 guarded retest")
    parser.add_argument(
        "--confirm-real-model-campaign",
        action="store_true",
        help="Required explicit confirmation before contacting the local model.",
    )
    parser.add_argument(
        "--regenerate-committed-evidence-from-local",
        action="store_true",
        help="Offline regeneration from retained local complete evidence.",
    )
    args = parser.parse_args(argv)

    if args.confirm_real_model_campaign and args.regenerate_committed_evidence_from_local:
        print("CAMPAIGN_FAILED:mutually_exclusive_flags", file=sys.stderr)
        return 1
    if args.regenerate_committed_evidence_from_local:
        try:
            return regenerate_committed_evidence_from_local()
        except RetestError as exc:
            print(f"CAMPAIGN_FAILED:{exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"CAMPAIGN_FAILED:{type(exc).__name__}:{exc}", file=sys.stderr)
            return 1
    if not args.confirm_real_model_campaign:
        print("CAMPAIGN_FAILED:missing_confirm_real_model_campaign", file=sys.stderr)
        return 1
    return run_real_campaign()


if __name__ == "__main__":
    raise SystemExit(main())
