#!/usr/bin/env python3
"""
EXP-3B-011 — Gate E breadth evaluation runner.

Modes (mutually exclusive):
  --confirm-real-model-gate-e
      Start pinned llama.cpp, run the 34-item campaign once, retain local
      complete evidence (incl. startup/shutdown), verify shutdown, then write
      committed evidence under docs/evidence/.
  --validate-committed-evidence
      Offline: load and validate committed EXP-3B-011_* artifacts.
  --regenerate-committed-evidence-from-local
      Offline: validate retained local evidence and regenerate committed
      adjudication/summary/capability matrix/manifest. No network, subprocess,
      or GGUF access.
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

from ssn.evaluation.gate_e_catalog import (  # noqa: E402
    EXPERIMENT_ID,
    build_gate_e_catalog,
    validate_gate_e_catalog,
)
from ssn.evaluation.gate_e_runner import (  # noqa: E402
    ALLOWED_ENDPOINT,
    EXPECTED_MODEL_SHA256,
    EXPECTED_MODEL_SIZE,
    LOCAL_EVIDENCE_DIR,
    MAX_OUTPUT_TOKENS,
    MODEL_PATH,
    REQUIRED_ENV,
    RUNTIME_DIR,
    RUNTIME_EXE,
    RUNTIME_SOURCE_COMMIT,
    RUNTIME_VERSION,
    FakeRegistry,
    GateEError,
    RecordingLLMProvider,
    apply_provenance_to_summary,
    build_committed_artifacts,
    compute_gate_e_summary,
    load_and_validate_committed_gate_e,
    regenerate_committed_evidence_from_local as regen_from_local,
    run_gate_e_campaign,
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
        raise GateEError("port_8080_already_listening")
    if _process_matches():
        raise GateEError("preexisting_model_process")


def _set_campaign_env(model_id: str) -> None:
    os.environ["SSN_OFFLINE"] = "1"
    for key, value in REQUIRED_ENV.items():
        os.environ[key] = value
    os.environ["SSN_LOCAL_MODEL_ID"] = model_id
    os.environ["SSN_LOCAL_MODEL_TIMEOUT_S"] = "30"
    os.environ["SSN_LOCAL_MODEL_MAX_TOKENS"] = str(MAX_OUTPUT_TOKENS)


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
            raise GateEError("llama_server_exited_early")
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
    raise GateEError("llama_server_start_timeout")


def _stop_llama_server(proc: Optional[subprocess.Popen], log_path: Path) -> Dict[str, Any]:
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
        raise GateEError("model_process_still_running_after_shutdown")
    if not port_closed:
        raise GateEError("port_8080_still_open_after_shutdown")

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
    return payload


def _write_committed_evidence(
    results: Any,
    summary: Dict[str, Any],
    *,
    timestamp_utc: Optional[str] = None,
    committed_dir: Optional[Path] = None,
) -> Dict[str, str]:
    out_dir = Path(committed_dir) if committed_dir is not None else COMMITTED_EVIDENCE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    adjudication, summary_doc, matrix, manifest = build_committed_artifacts(
        results, summary, timestamp_utc=timestamp_utc
    )
    load_and_validate_committed_gate_e(adjudication, summary_doc, matrix, manifest)
    paths = {
        "adjudication": out_dir / "EXP-3B-011_ADJUDICATION.json",
        "summary": out_dir / "EXP-3B-011_SUMMARY.json",
        "capability_matrix": out_dir / "EXP-3B-011_CAPABILITY_MATRIX.json",
        "manifest": out_dir / "EXP-3B-011_EVIDENCE_MANIFEST.json",
    }
    paths["adjudication"].write_text(
        json.dumps(adjudication, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    paths["summary"].write_text(
        json.dumps(summary_doc, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    paths["capability_matrix"].write_text(
        json.dumps(matrix, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    paths["manifest"].write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "adjudication_canonical_sha256": manifest["adjudication_canonical_sha256"],
        "summary_canonical_sha256": manifest["summary_canonical_sha256"],
        "capability_matrix_canonical_sha256": manifest[
            "capability_matrix_canonical_sha256"
        ],
        "hash_semantics": manifest["hash_semantics"],
    }


def validate_committed_evidence(
    committed_dir: Optional[Path] = None,
    *,
    print_output: bool = True,
) -> int:
    src = Path(committed_dir) if committed_dir is not None else COMMITTED_EVIDENCE_DIR
    adjudication = json.loads(
        (src / "EXP-3B-011_ADJUDICATION.json").read_text(encoding="utf-8")
    )
    summary = json.loads((src / "EXP-3B-011_SUMMARY.json").read_text(encoding="utf-8"))
    matrix = json.loads(
        (src / "EXP-3B-011_CAPABILITY_MATRIX.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (src / "EXP-3B-011_EVIDENCE_MANIFEST.json").read_text(encoding="utf-8")
    )
    load_and_validate_committed_gate_e(adjudication, summary, matrix, manifest)
    out = {
        "mode": "validate_committed_evidence",
        "experiment_id": EXPERIMENT_ID,
        "ok": True,
        "registry_review_recommendation": summary.get(
            "registry_review_recommendation"
        ),
        "mandatory_safety_runtime_met": summary.get("mandatory_safety_runtime_met"),
    }
    if print_output:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def regenerate_committed_evidence_from_local(
    evidence_dir: Optional[Path] = None,
    committed_dir: Optional[Path] = None,
    *,
    print_output: bool = True,
) -> int:
    """Offline regeneration — no network, subprocess, or GGUF access."""
    validate_gate_e_catalog(build_gate_e_catalog())
    paths = regen_from_local(evidence_dir=evidence_dir, committed_dir=committed_dir)
    summary = json.loads(paths["summary"].read_text(encoding="utf-8"))
    adjudication = json.loads(paths["adjudication"].read_text(encoding="utf-8"))
    out = {
        "mode": "regenerate_committed_evidence_from_local",
        "experiment_id": EXPERIMENT_ID,
        "gate_e_execution_complete": summary.get("gate_e_execution_complete"),
        "mandatory_safety_runtime_met": summary.get("mandatory_safety_runtime_met"),
        "registry_review_recommendation": summary.get(
            "registry_review_recommendation"
        ),
        "native_text_verified_count": summary.get("native_text_verified_count"),
        "native_json_verified_count": summary.get("native_json_verified_count"),
        "governed_safety_pass_count": summary.get("governed_safety_pass_count"),
        "runtime_pass_count": summary.get("runtime_pass_count"),
        "preserved_native_hashes": len(adjudication.get("evaluations") or []),
        "preserved_final_hashes": len(adjudication.get("evaluations") or []),
    }
    if print_output:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def run_real_campaign() -> int:
    validate_gate_e_catalog(build_gate_e_catalog())
    LOCAL_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    startup_log = LOCAL_EVIDENCE_DIR / "local_runtime_startup.log"
    shutdown_json = LOCAL_EVIDENCE_DIR / "local_runtime_shutdown.json"
    startup_json_path = LOCAL_EVIDENCE_DIR / "local_runtime_startup.json"

    proc: Optional[subprocess.Popen] = None
    results = None
    summary: Optional[Dict[str, Any]] = None
    model_info: Optional[Dict[str, Any]] = None
    campaign_error: Optional[BaseException] = None
    startup_payload: Dict[str, Any] = {
        "runtime_started": False,
        "endpoint_classification": "loopback",
        "port": 8080,
    }
    shutdown_payload: Optional[Dict[str, Any]] = None

    try:
        _require_clean_runtime()
        model_info = verify_model_artifact()
        if int(model_info["size"]) != EXPECTED_MODEL_SIZE:
            raise GateEError("model_size_mismatch")
        if model_info["sha256"] != EXPECTED_MODEL_SHA256:
            raise GateEError("model_sha256_mismatch")
        verify_runtime_executable()
        proc = _start_llama_server(startup_log)
        startup_payload = {
            "runtime_started": True,
            "endpoint_classification": "loopback",
            "port": 8080,
            "runtime_version": RUNTIME_VERSION,
            "runtime_source_commit": RUNTIME_SOURCE_COMMIT,
            "started_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        startup_json_path.write_text(
            json.dumps(startup_payload, indent=2) + "\n", encoding="utf-8"
        )
        model_id = validate_single_server_model_id(ALLOWED_ENDPOINT)
        _set_campaign_env(model_id)

        from ssn.core.language_engine import LanguageEngine
        from ssn.core.llm_providers import get_default_provider_from_env
        from ssn.governance.runtime_context import GovernedContextLLMProvider

        registry = FakeRegistry()
        inner = get_default_provider_from_env()
        recorder = RecordingLLMProvider(inner)
        engine = LanguageEngine(provider=GovernedContextLLMProvider(recorder))

        results = run_gate_e_campaign(
            provider=inner,
            engine=engine,
            recorder=recorder,
            registry=registry,
            include_real_model=True,
        )
        summary = compute_gate_e_summary(results)
        summary = apply_provenance_to_summary(
            summary,
            model_artifact_verified=True,
            model_size_verified=True,
            model_sha256_verified=True,
            runtime_executable_verified=True,
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
        # Local evidence written after verified shutdown (fail-closed).
        _pending_env = env_snapshot
    except BaseException as exc:
        campaign_error = exc
        _pending_env = None

    # Shutdown must run and be verified before committed evidence may be written.
    try:
        shutdown_payload = _stop_llama_server(proc, shutdown_json)
        print(
            f"shutdown_method={shutdown_payload.get('shutdown_method')}",
            file=sys.stderr,
        )
    except Exception as exc:
        print(f"CAMPAIGN_FAILED:shutdown:{type(exc).__name__}", file=sys.stderr)
        return 1

    if campaign_error is not None:
        if isinstance(campaign_error, GateEError):
            print(f"CAMPAIGN_FAILED:{campaign_error}", file=sys.stderr)
        else:
            print(
                f"CAMPAIGN_FAILED:{type(campaign_error).__name__}:{campaign_error}",
                file=sys.stderr,
            )
        return 1

    assert results is not None and summary is not None and _pending_env is not None
    write_local_evidence(
        results,
        summary,
        evidence_dir=LOCAL_EVIDENCE_DIR,
        env_snapshot=_pending_env,
        startup_snapshot=startup_payload,
        shutdown_snapshot=shutdown_payload,
    )
    hashes = _write_committed_evidence(results, summary)
    summary_out = dict(summary)
    summary_out.update(hashes)
    summary_out["recommendation"] = summary.get("registry_review_recommendation")
    print(json.dumps(summary_out, indent=2, ensure_ascii=False))
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="EXP-3B-011 Gate E breadth evaluation")
    parser.add_argument(
        "--confirm-real-model-gate-e",
        action="store_true",
        help="Required explicit confirmation before contacting the local model.",
    )
    parser.add_argument(
        "--validate-committed-evidence",
        action="store_true",
        help="Offline validation of committed EXP-3B-011 evidence artifacts.",
    )
    parser.add_argument(
        "--regenerate-committed-evidence-from-local",
        action="store_true",
        help="Offline regeneration from retained local complete evidence.",
    )
    args = parser.parse_args(argv)

    modes = [
        args.confirm_real_model_gate_e,
        args.validate_committed_evidence,
        args.regenerate_committed_evidence_from_local,
    ]
    if sum(1 for m in modes if m) > 1:
        print("CAMPAIGN_FAILED:mutually_exclusive_flags", file=sys.stderr)
        return 1
    if args.validate_committed_evidence:
        try:
            return validate_committed_evidence()
        except GateEError as exc:
            print(f"CAMPAIGN_FAILED:{exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"CAMPAIGN_FAILED:{type(exc).__name__}:{exc}", file=sys.stderr)
            return 1
    if args.regenerate_committed_evidence_from_local:
        try:
            return regenerate_committed_evidence_from_local()
        except GateEError as exc:
            print(f"CAMPAIGN_FAILED:{exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"CAMPAIGN_FAILED:{type(exc).__name__}:{exc}", file=sys.stderr)
            return 1
    if not args.confirm_real_model_gate_e:
        print("CAMPAIGN_FAILED:missing_confirm_real_model_gate_e", file=sys.stderr)
        return 1
    return run_real_campaign()


if __name__ == "__main__":
    raise SystemExit(main())
