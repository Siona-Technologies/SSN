#!/usr/bin/env python3
"""
EXP-3B-010 — controlled real-Qwen guarded-path retest runner.

Requires explicit --confirm-real-model-campaign.
Starts/stops the pinned llama.cpp server, runs the 21-probe campaign once,
writes complete local evidence outside Git, and emits sanitized committed
evidence under docs/evidence/.
"""

from __future__ import annotations

import argparse
import hashlib
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
    canonical_json_bytes,
    check_server_model_id,
    compute_campaign_summary,
    load_and_validate_exp_3b_010_adjudication,
    run_campaign,
    validate_campaign_environment,
    validate_probe_catalog,
    verify_model_artifact,
    verify_runtime_executable,
    write_local_evidence,
)

COMMITTED_EVIDENCE_DIR = ROOT / "docs" / "evidence"


def _port_open(host: str = "127.0.0.1", port: int = 8080) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def _server_accepting(host: str = "127.0.0.1", port: int = 8080) -> bool:
    """True only when a listener answers HTTP on the endpoint."""
    if not _port_open(host, port):
        return False
    try:
        with urllib.request.urlopen(
            f"http://{host}:{port}/v1/models", timeout=1
        ) as resp:
            return resp.status == 200
    except Exception:
        return False


def _process_matches(patterns: tuple[str, ...]) -> bool:
    try:
        out = subprocess.check_output(
            ["tasklist"], text=True, stderr=subprocess.DEVNULL
        )
    except Exception:
        return False
    lower = out.lower()
    return any(p.lower() in lower for p in patterns)


def _require_clean_runtime() -> None:
    if _port_open():
        raise RetestError("port_8080_already_listening")
    if _process_matches(("llama-server", "llama.cpp", "qwen")):
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
    if proc is None:
        return "not_started"
    try:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            method = "forced_after_bounded_graceful_wait"
            proc.kill()
            proc.wait(timeout=10)
    finally:
        fh = getattr(proc, "_ssn_log_fh", None)
        if fh is not None:
            try:
                fh.close()
            except Exception:
                pass
        log_path.write_text(
            log_path.read_text(encoding="utf-8", errors="replace")
            + f"\nshutdown_method={method}\n",
            encoding="utf-8",
        )
    deadline = time.time() + 15
    while time.time() < deadline:
        if not _server_accepting() and not _process_matches(("llama-server",)):
            break
        time.sleep(0.5)
    if _process_matches(("llama-server",)):
        raise RetestError("llama_process_still_running")
    if _server_accepting():
        raise RetestError("port_8080_still_listening_after_shutdown")
    return method


def _resolve_model_id() -> str:
    with urllib.request.urlopen(ALLOWED_ENDPOINT + "/v1/models", timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    data = payload.get("data")
    if type(data) is not list or len(data) != 1 or not isinstance(data[0], dict):
        raise RetestError("malformed_model_list")
    model_id = data[0].get("id")
    if type(model_id) is not str or not model_id.strip():
        raise RetestError("malformed_model_id")
    return model_id


def _write_committed_evidence(
    results: Any,
    summary: Dict[str, Any],
) -> Dict[str, str]:
    COMMITTED_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    adjudication = build_committed_adjudication(results, summary)
    summary_doc = dict(summary)
    summary_doc["timestamp_utc"] = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    summary_doc["runtime_version"] = RUNTIME_VERSION
    summary_doc["runtime_source_commit"] = RUNTIME_SOURCE_COMMIT
    summary_doc["model_filename"] = MODEL_PATH.name
    summary_doc["model_size"] = EXPECTED_MODEL_SIZE
    summary_doc["model_sha256"] = EXPECTED_MODEL_SHA256

    summary_bytes = canonical_json_bytes(summary_doc)
    summary_sha = hashlib.sha256(summary_bytes).hexdigest()
    adjudication["summary_sha256"] = summary_sha

    # Hash adjudication before attaching circular manifest linkage.
    adjudication_sha = hashlib.sha256(canonical_json_bytes(adjudication)).hexdigest()
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "evidence_directory": "docs/evidence",
        "complete_responses_retained_locally": True,
        "complete_responses_committed": False,
        "committed_response_type": "SANITIZED_TRUNCATED_RESPONSE_EXCERPTS",
        "committed_excerpt_limit": 240,
        "adjudication_scope": summary["adjudication_scope"],
        "local_evidence_directory": str(LOCAL_EVIDENCE_DIR),
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
        "summary_sha256": summary_sha,
        "adjudication_sha256": adjudication_sha,
    }
    manifest_sha = hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
    # Store manifest hash on adjudication only after manifest is finalized.
    adjudication["manifest_sha256"] = manifest_sha
    # Re-hash adjudication including manifest_sha256 for the on-disk file; keep
    # the pre-link adjudication_sha256 in the manifest as the content hash of
    # the adjudication body excluding the manifest back-pointer.
    adjudication_for_disk = dict(adjudication)

    paths = {
        "adjudication": COMMITTED_EVIDENCE_DIR / "EXP-3B-010_ADJUDICATION.json",
        "summary": COMMITTED_EVIDENCE_DIR / "EXP-3B-010_SUMMARY.json",
        "manifest": COMMITTED_EVIDENCE_DIR / "EXP-3B-010_EVIDENCE_MANIFEST.json",
    }
    paths["adjudication"].write_text(
        json.dumps(adjudication_for_disk, indent=2, ensure_ascii=False) + "\n",
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

    # Validator compares manifest hash against manifest without requiring the
    # adjudication file hash to include the back-pointer.
    load_and_validate_exp_3b_010_adjudication(
        adjudication_for_disk, manifest=manifest, summary=summary_doc
    )
    return {
        "adjudication_sha256": adjudication_sha,
        "summary_sha256": summary_sha,
        "manifest_sha256": manifest_sha,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="EXP-3B-010 guarded retest")
    parser.add_argument(
        "--confirm-real-model-campaign",
        action="store_true",
        help="Required explicit confirmation before contacting the local model.",
    )
    args = parser.parse_args(argv)
    if not args.confirm_real_model_campaign:
        print("CAMPAIGN_FAILED:missing_confirm_real_model_campaign", file=sys.stderr)
        return 1

    validate_probe_catalog(build_probe_catalog())
    LOCAL_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    startup_log = LOCAL_EVIDENCE_DIR / "local_runtime_startup.log"
    shutdown_log = LOCAL_EVIDENCE_DIR / "local_runtime_shutdown.log"

    proc: Optional[subprocess.Popen] = None
    shutdown_method = "not_started"
    try:
        _require_clean_runtime()
        model_info = verify_model_artifact()
        verify_runtime_executable()
        proc = _start_llama_server(startup_log)
        model_id = _resolve_model_id()
        check_server_model_id(ALLOWED_ENDPOINT, model_id)
        _set_campaign_env(model_id)
        validate_campaign_environment()

        from ssn.core.language_engine import LanguageEngine
        from ssn.core.llm_providers import get_default_provider_from_env
        from ssn.governance.identity_registry import load_approved_identity_registry
        from ssn.governance.runtime_context import GovernedContextLLMProvider

        registry = load_approved_identity_registry()
        inner = get_default_provider_from_env()
        recorder = RecordingLLMProvider(inner)
        # Separate raw-control provider shares the same inner endpoint but a
        # distinct recorder so call counts stay separated.
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
        }
        write_local_evidence(
            results, summary, evidence_dir=LOCAL_EVIDENCE_DIR, env_snapshot=env_snapshot
        )
        hashes = _write_committed_evidence(results, summary)
        summary_out = dict(summary)
        summary_out.update(hashes)
        print(json.dumps(summary_out, indent=2, ensure_ascii=False))
        return 0 if summary["guarded_campaign_acceptance_met"] else 2
    except RetestError as exc:
        print(f"CAMPAIGN_FAILED:{exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"CAMPAIGN_FAILED:{type(exc).__name__}:{exc}", file=sys.stderr)
        return 1
    finally:
        try:
            shutdown_method = _stop_llama_server(proc, shutdown_log)
        except Exception as exc:
            shutdown_log.write_text(
                f"shutdown_error={type(exc).__name__}:{exc}\n", encoding="utf-8"
            )
            shutdown_method = "shutdown_error"
        print(f"shutdown_method={shutdown_method}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
