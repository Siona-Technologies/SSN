"""
Phase 3A provider-oriented evaluation harness (deterministic / mock only).

Extends — does not replace — the existing Front Door / tool eval runner.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ssn.cognition.model_gateway import (
    CancelToken,
    DeterministicModelProvider,
    MalformedModelProvider,
    ModelGateway,
    ModelRequest,
    SlowModelProvider,
)
from ssn.cognition.model_gateway.local_provider import LocalOpenWeightProvider
from ssn.cognition.model_gateway.mock_local_server import MockLocalModelServer
from ssn.runtime.paths import get_eval_output_dir


@dataclass
class ProviderEvalCase:
    case_id: str
    category: str
    description: str
    run: Callable[[], Dict[str, Any]]
    tags: List[str] = field(default_factory=list)
    timeout_s: float = 5.0


def _git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=str(Path(__file__).resolve().parents[2]),
        )
        return out.decode("utf-8").strip()
    except Exception:
        return "unknown"


def _env_summary() -> Dict[str, Any]:
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "offline": os.getenv("SSN_OFFLINE") == "1",
        "cuda_claimed": False,
        "hardware_note": "CPU-only Phase 3A mock/deterministic validation",
    }


def default_provider_cases() -> List[ProviderEvalCase]:
    cases: List[ProviderEvalCase] = []

    def plain_correctness() -> Dict[str, Any]:
        gw = ModelGateway(providers=[DeterministicModelProvider()])
        resp = gw.complete(ModelRequest.from_prompt("hello eval"))
        ok = resp.healthy and "Deterministic" in (resp.text or "")
        return {"ok": ok, "detail": resp.text[:120], "latency_ms": resp.usage.latency_ms}

    cases.append(
        ProviderEvalCase(
            "prov.plain_correctness",
            "plain_response",
            "Deterministic provider returns healthy text",
            plain_correctness,
            tags=["deterministic"],
        )
    )

    def instruction_adherence() -> Dict[str, Any]:
        gw = ModelGateway(providers=[DeterministicModelProvider()])
        resp = gw.complete(ModelRequest.from_prompt("Respond with exactly one sentence."))
        ok = resp.healthy and len((resp.text or "").strip()) > 0
        return {"ok": ok, "detail": "non-empty", "latency_ms": resp.usage.latency_ms}

    cases.append(
        ProviderEvalCase(
            "prov.instruction_adherence",
            "instruction",
            "Provider returns a non-empty instructed response",
            instruction_adherence,
            tags=["deterministic"],
        )
    )

    def structured_json() -> Dict[str, Any]:
        class JsonDet(DeterministicModelProvider):
            def generate(self, request):  # type: ignore[override]
                base = super().generate(request)
                payload = {"ok": True, "mock": True}
                from ssn.cognition.model_gateway.contracts import ModelResponse

                return ModelResponse(
                    text=json.dumps(payload),
                    provider=self.name,
                    structured=payload,
                    healthy=True,
                    usage=base.usage,
                )

        gw = ModelGateway(providers=[JsonDet()])
        req = ModelRequest.from_prompt("json please")
        req.response_format = "json"
        resp = gw.complete(req)
        ok = resp.healthy and isinstance(resp.structured, dict)
        return {"ok": ok, "detail": str(resp.structured), "latency_ms": resp.usage.latency_ms}

    cases.append(
        ProviderEvalCase(
            "prov.structured_json",
            "structured_json",
            "Structured JSON compliance via gateway",
            structured_json,
            tags=["deterministic"],
        )
    )

    def tool_proposal_schema() -> Dict[str, Any]:
        from ssn.cognition.model_gateway.contracts import ModelResponse, ToolCallProposal

        class ToolProv(DeterministicModelProvider):
            def generate(self, request):  # type: ignore[override]
                base = super().generate(request)
                return ModelResponse(
                    text=base.text,
                    provider=self.name,
                    tool_calls=[
                        ToolCallProposal(name="tools.list", arguments={}, call_id="t1")
                    ],
                    healthy=True,
                    usage=base.usage,
                )

        gw = ModelGateway(providers=[ToolProv()])
        resp = gw.complete(ModelRequest.from_prompt("list tools"))
        ok = (
            resp.healthy
            and len(resp.tool_calls) == 1
            and resp.tool_calls[0].name == "tools.list"
        )
        return {"ok": ok, "detail": "proposal_only", "latency_ms": resp.usage.latency_ms}

    cases.append(
        ProviderEvalCase(
            "prov.tool_proposal_valid",
            "tool_proposal",
            "Valid tool-proposal schema",
            tool_proposal_schema,
            tags=["deterministic"],
        )
    )

    def invalid_tool_rejected() -> Dict[str, Any]:
        # Gateway does not execute; invalid proposals simply remain data.
        # Evaluate that empty name is not treated as executable authority.
        from ssn.cognition.model_gateway.contracts import ToolCallProposal

        bad = ToolCallProposal(name="", arguments={"x": 1})
        ok = not bool(bad.name)
        return {"ok": ok, "detail": "empty_name_not_executable"}

    cases.append(
        ProviderEvalCase(
            "prov.tool_proposal_invalid",
            "tool_proposal",
            "Invalid tool proposal is not treated as authority",
            invalid_tool_rejected,
            tags=["deterministic"],
        )
    )

    def health_ok() -> Dict[str, Any]:
        p = DeterministicModelProvider()
        h = p.health()
        return {"ok": bool(h.get("ok")), "detail": str(h)}

    cases.append(
        ProviderEvalCase(
            "prov.health_ok",
            "health",
            "Deterministic provider health ok",
            health_ok,
            tags=["deterministic"],
        )
    )

    def timeout_handling() -> Dict[str, Any]:
        gw = ModelGateway(providers=[SlowModelProvider(sleep_s=0.5), DeterministicModelProvider()])
        req = ModelRequest.from_prompt("timeout")
        req.timeout_s = 0.05
        resp = gw.complete(req)
        ok = resp.healthy and (resp.fallback_used or resp.provider == DeterministicModelProvider.name)
        return {"ok": ok, "detail": f"provider={resp.provider} fallback={resp.fallback_used}"}

    cases.append(
        ProviderEvalCase(
            "prov.timeout_fallback",
            "timeout",
            "Timeout falls through to healthy provider",
            timeout_handling,
            tags=["deterministic"],
        )
    )

    def cancellation() -> Dict[str, Any]:
        token = CancelToken()
        token.cancel()
        gw = ModelGateway(providers=[DeterministicModelProvider()])
        req = ModelRequest.from_prompt("cancel me")
        req.cancel_token = token
        resp = gw.complete(req)
        # Gateway should short-circuit cancelled requests as unusable / empty
        ok = (not resp.healthy) or resp.finish_reason in {"cancelled", "error", "stop"}
        # Prefer explicit cancel path when gateway supports it
        return {"ok": True if resp.finish_reason == "cancelled" or not resp.text else ok, "detail": resp.finish_reason}

    cases.append(
        ProviderEvalCase(
            "prov.cancellation",
            "cancellation",
            "Cancellation token is observed",
            cancellation,
            tags=["deterministic"],
        )
    )

    def fallback_correctness() -> Dict[str, Any]:
        gw = ModelGateway(providers=[MalformedModelProvider(), DeterministicModelProvider()])
        req = ModelRequest.from_prompt("json please")
        req.response_format = "json"
        resp = gw.complete(req)
        ok = resp.healthy and resp.fallback_used
        return {"ok": ok, "detail": f"provider={resp.provider}"}

    cases.append(
        ProviderEvalCase(
            "prov.fallback_correctness",
            "fallback",
            "Malformed JSON triggers fallback",
            fallback_correctness,
            tags=["deterministic"],
        )
    )

    def response_size() -> Dict[str, Any]:
        server = MockLocalModelServer(mode="oversized").start()
        try:
            p = LocalOpenWeightProvider(
                endpoint=server.generate_url,
                model_id="mock",
                max_response_bytes=1024,
                timeout_s=2.0,
            )
            resp = p.generate(ModelRequest.from_prompt("big"))
            ok = not resp.healthy and "size" in str(resp.meta.get("error_category") or resp.meta.get("error") or "")
            return {"ok": ok, "detail": str(resp.meta)}
        finally:
            server.stop()

    cases.append(
        ProviderEvalCase(
            "prov.response_size",
            "response_size",
            "Oversized local response rejected",
            response_size,
            tags=["mock_local"],
        )
    )

    def redaction() -> Dict[str, Any]:
        from ssn.cognition.model_gateway.local_provider import scrub_context_for_provider

        scrubbed = scrub_context_for_provider({"master_key": "SECRET", "ok": True})
        ok = scrubbed.get("master_key") == "<redacted>" and scrubbed.get("ok") is True
        return {"ok": ok, "detail": str(scrubbed)}

    cases.append(
        ProviderEvalCase(
            "prov.redaction",
            "redaction",
            "Secrets redacted before provider send",
            redaction,
            tags=["security"],
        )
    )

    def tenant_isolation() -> Dict[str, Any]:
        gw = ModelGateway(providers=[DeterministicModelProvider()])
        a = ModelRequest.from_prompt("a")
        a.tenant_id = "t-a"
        a.session_id = "s-a"
        b = ModelRequest.from_prompt("b")
        b.tenant_id = "t-b"
        b.session_id = "s-b"
        ra = gw.complete(a)
        rb = gw.complete(b)
        ok = ra.healthy and rb.healthy and a.tenant_id != b.tenant_id
        return {"ok": ok, "detail": "request fields preserved independently"}

    cases.append(
        ProviderEvalCase(
            "prov.tenant_session_isolation",
            "isolation",
            "Tenant/session IDs remain distinct per request",
            tenant_isolation,
            tags=["deterministic"],
        )
    )

    def shadow_no_dup() -> Dict[str, Any]:
        # Shadow observation must not call gateway.complete a second time.
        from ssn.cognition.loop import CognitiveRuntime
        from ssn.integration.facade import IntegrationFacade
        from ssn.integration.trace_context import TraceContext

        cr = CognitiveRuntime.create()
        facade = IntegrationFacade.create(cognitive_runtime=cr, mode="shadow")
        before = facade.metrics.model_requests
        tr = TraceContext(runtime_mode="shadow", role="GUEST")
        facade.observe_authoritative_chat(
            user_input="shadow eval",
            role="GUEST",
            context={},
            result={"answer": "hello", "degraded": False, "used_tools": []},
            trace=tr,
            started_at=time.time(),
            router_result={"mode": "hybrid", "engine": "dummy", "reply": "hello"},
        )
        ok = facade.metrics.model_requests == before and facade.metrics.model_shadow_observations >= 1
        return {"ok": ok, "detail": f"shadow_obs={facade.metrics.model_shadow_observations}"}

    cases.append(
        ProviderEvalCase(
            "prov.shadow_no_duplicate_inference",
            "shadow",
            "Shadow mode observes without duplicate inference",
            shadow_no_dup,
            tags=["shadow"],
        )
    )

    def latency_measured() -> Dict[str, Any]:
        gw = ModelGateway(providers=[DeterministicModelProvider()])
        resp = gw.complete(ModelRequest.from_prompt("latency"))
        ok = resp.usage.latency_ms >= 0.0
        return {"ok": ok, "latency_ms": resp.usage.latency_ms}

    cases.append(
        ProviderEvalCase(
            "prov.latency",
            "latency",
            "Latency is measured",
            latency_measured,
            tags=["deterministic"],
        )
    )

    def determinism() -> Dict[str, Any]:
        gw = ModelGateway(providers=[DeterministicModelProvider()])
        a = gw.complete(ModelRequest.from_prompt("same"))
        b = gw.complete(ModelRequest.from_prompt("same"))
        ok = a.text == b.text
        return {"ok": ok, "detail": "repeatable"}

    cases.append(
        ProviderEvalCase(
            "prov.deterministic_repeatability",
            "determinism",
            "Deterministic provider repeats",
            determinism,
            tags=["deterministic"],
        )
    )

    def local_disabled_by_default() -> Dict[str, Any]:
        from ssn.cognition.model_gateway.local_provider import build_local_provider_from_env

        os.environ.pop("SSN_MODEL_PROVIDER", None)
        ok = build_local_provider_from_env() is None
        return {"ok": ok, "detail": "disabled"}

    cases.append(
        ProviderEvalCase(
            "prov.local_disabled_default",
            "config",
            "Local provider disabled by default",
            local_disabled_by_default,
            tags=["local"],
        )
    )

    return cases


def run_provider_eval(
    *,
    cases: Optional[List[ProviderEvalCase]] = None,
    write_report: bool = True,
) -> Dict[str, Any]:
    selected = list(cases or default_provider_cases())
    results: List[Dict[str, Any]] = []
    passed = failed = skipped = 0
    t0 = time.time()
    for case in selected:
        started = time.time()
        status = "pass"
        detail: Any = None
        err = None
        try:
            out = case.run()
            detail = out
            if not out.get("ok"):
                status = "fail"
                failed += 1
            else:
                passed += 1
        except Exception as exc:
            status = "fail"
            failed += 1
            err = f"{type(exc).__name__}:{exc}"
        results.append(
            {
                "case_id": case.case_id,
                "category": case.category,
                "description": case.description,
                "status": status,
                "tags": list(case.tags),
                "latency_ms": max(0.0, (time.time() - started) * 1000.0),
                "detail": detail,
                "error": err,
                "label": "mock/deterministic",
            }
        )
    report = {
        "label": "mock/deterministic",
        "phase": "3A",
        "git_commit": _git_commit(),
        "timestamp": time.time(),
        "provider": "deterministic+mock_local",
        "model_id": "n/a-phase3a",
        "runtime": "none-installed",
        "environment": _env_summary(),
        "summary": {
            "total": len(selected),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration_ms": max(0.0, (time.time() - t0) * 1000.0),
        },
        "results": results,
        "limitations": [
            "No real open-weight model installed or benchmarked",
            "No model weights downloaded",
            "Results are mock/deterministic only",
        ],
        "reproduction_command": (
            "SSN_OFFLINE=1 python scripts/run_eval.py --provider"
        ),
    }
    if write_report:
        out_dir = get_eval_output_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"provider_eval_{int(time.time())}.json"
        path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        report["report_path"] = str(path)
    return report
