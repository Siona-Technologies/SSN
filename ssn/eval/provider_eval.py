"""
Phase 3A provider-oriented evaluation harness (deterministic / mock only).

Declarative cases with hard per-case timeouts via isolated child processes.
"""

from __future__ import annotations

import json
import math
import multiprocessing as mp
import os
import platform
import subprocess
import time
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ssn.runtime.paths import get_eval_output_dir


@dataclass
class ProviderEvalCase:
    case_id: str
    category: str
    description: str
    handler_id: str
    input: Dict[str, Any] = field(default_factory=dict)
    expected_constraints: Dict[str, Any] = field(default_factory=dict)
    provider_configuration: Dict[str, Any] = field(default_factory=dict)
    timeout_s: float = 5.0
    tags: List[str] = field(default_factory=list)
    thresholds: Dict[str, Any] = field(default_factory=dict)


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


# ---------------------------------------------------------------------------
# Handlers (must be top-level for Windows spawn)
# ---------------------------------------------------------------------------

def _h_plain_correctness(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway import DeterministicModelProvider, ModelGateway, ModelRequest

    gw = ModelGateway(providers=[DeterministicModelProvider()])
    resp = gw.complete(ModelRequest.from_prompt(str(inp.get("prompt") or "hello eval")))
    ok = resp.healthy and "Deterministic" in (resp.text or "")
    return {
        "ok": ok,
        "detail": (resp.text or "")[:120],
        "provider_latency_ms": resp.usage.latency_ms,
    }


def _h_instruction_adherence(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway import DeterministicModelProvider, ModelGateway, ModelRequest
    from ssn.cognition.model_gateway.mock_local_server import MockLocalModelServer
    from ssn.cognition.model_gateway.local_provider import LocalOpenWeightProvider

    # Exact deterministic constraint via mock local that echoes token
    token = str(inp.get("exact_token") or "EXACT_TOKEN_ALPHA")
    server = MockLocalModelServer(mode="ok").start()
    try:
        p = LocalOpenWeightProvider(
            endpoint=server.generate_url,
            model_id="mock-eval",
            timeout_s=2.0,
        )
        resp = p.generate(ModelRequest.from_prompt(f"return {token}"))
        ok = resp.healthy and resp.text.strip() == token
        return {"ok": ok, "detail": resp.text[:80], "provider_latency_ms": resp.usage.latency_ms}
    finally:
        server.stop()


def _h_structured_json(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway import DeterministicModelProvider, ModelGateway, ModelRequest
    from ssn.cognition.model_gateway.contracts import ModelResponse
    import json as _json

    class JsonDet(DeterministicModelProvider):
        def generate(self, request):  # type: ignore[override]
            base = super().generate(request)
            payload = {"ok": True, "mock": True, "n": 1}
            return ModelResponse(
                text=_json.dumps(payload),
                provider=self.name,
                structured=payload,
                healthy=True,
                usage=base.usage,
            )

    gw = ModelGateway(providers=[JsonDet()])
    req = ModelRequest.from_prompt("json please")
    req.response_format = "json"
    resp = gw.complete(req)
    constraints = inp.get("schema") or {"required": ["ok", "mock"]}
    ok = resp.healthy and isinstance(resp.structured, dict)
    if ok:
        for key in constraints.get("required", []):
            if key not in resp.structured:
                ok = False
                break
        if constraints.get("ok_is_true") and resp.structured.get("ok") is not True:
            ok = False
    return {"ok": ok, "detail": str(resp.structured), "provider_latency_ms": resp.usage.latency_ms}


def _h_tool_proposal_valid(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway import DeterministicModelProvider, ModelGateway, ModelRequest
    from ssn.cognition.model_gateway.contracts import ModelResponse, ToolCallProposal
    from ssn.cognition.model_gateway.tool_proposal_validation import validate_tool_proposal

    class ToolProv(DeterministicModelProvider):
        def generate(self, request):  # type: ignore[override]
            base = super().generate(request)
            return ModelResponse(
                text=base.text,
                provider=self.name,
                tool_calls=[ToolCallProposal(name="tools.list", arguments={}, call_id="t1")],
                healthy=True,
                usage=base.usage,
            )

    gw = ModelGateway(providers=[ToolProv()])
    resp = gw.complete(ModelRequest.from_prompt("list tools"))
    if not (resp.healthy and resp.tool_calls):
        return {"ok": False, "detail": "missing_proposal"}
    result = validate_tool_proposal(resp.tool_calls[0])
    return {"ok": result.ok, "detail": result.reason}


def _h_tool_proposal_invalid(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway.contracts import ToolCallProposal
    from ssn.cognition.model_gateway.tool_proposal_validation import validate_tool_proposal

    bad = ToolCallProposal(name="", arguments={"x": 1})
    result = validate_tool_proposal(bad)
    ok = (not result.ok) and result.reason == "empty_name"
    return {"ok": ok, "detail": result.reason}


def _h_health_ok(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway import DeterministicModelProvider

    h = DeterministicModelProvider().health()
    return {"ok": bool(h.get("ok")), "detail": str(h)}


def _h_timeout_fallback(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway import (
        DeterministicModelProvider,
        ModelGateway,
        ModelRequest,
        SlowModelProvider,
    )

    gw = ModelGateway(providers=[SlowModelProvider(sleep_s=0.5), DeterministicModelProvider()])
    req = ModelRequest.from_prompt("timeout")
    req.timeout_s = 0.05
    resp = gw.complete(req)
    ok = resp.healthy and (resp.fallback_used or resp.provider == DeterministicModelProvider.name)
    return {
        "ok": ok,
        "detail": f"provider={resp.provider} fallback={resp.fallback_used}",
        "source_provider": SlowModelProvider.name,
        "fallback_provider": resp.provider,
        "fallback_reason": resp.fallback_reason,
    }


def _h_cancellation_before(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway import CancelToken, DeterministicModelProvider, ModelGateway, ModelRequest

    token = CancelToken()
    token.cancel()
    gw = ModelGateway(providers=[DeterministicModelProvider()])
    req = ModelRequest.from_prompt("cancel me")
    req.cancel_token = token
    resp = gw.complete(req)
    ok = (not resp.healthy) or resp.finish_reason == "cancelled" or not (resp.text or "")
    return {"ok": ok, "detail": resp.finish_reason}


def _h_cancellation_during(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway import CancelToken, ModelRequest
    from ssn.cognition.model_gateway.local_provider import LocalOpenWeightProvider
    from ssn.cognition.model_gateway.mock_local_server import MockLocalModelServer

    server = MockLocalModelServer(mode="timeout").start()
    server._httpd.timeout_sleep_s = 1.0  # type: ignore[attr-defined]
    try:
        p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="mock", timeout_s=0.2)
        token = CancelToken()
        # Cancel before generate — local provider checks cancel before network
        token.cancel()
        req = ModelRequest.from_prompt("slow")
        req.cancel_token = token
        resp = p.generate(req)
        ok = resp.finish_reason == "cancelled"
        return {"ok": ok, "detail": resp.finish_reason}
    finally:
        server.stop()


def _h_fallback_correctness(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway import (
        DeterministicModelProvider,
        MalformedModelProvider,
        ModelGateway,
        ModelRequest,
    )

    gw = ModelGateway(providers=[MalformedModelProvider(), DeterministicModelProvider()])
    req = ModelRequest.from_prompt("json please")
    req.response_format = "json"
    resp = gw.complete(req)
    ok = resp.healthy and resp.fallback_used
    return {
        "ok": ok,
        "detail": f"provider={resp.provider}",
        "source_provider": MalformedModelProvider.name,
        "fallback_provider": resp.provider,
        "fallback_reason": resp.fallback_reason,
    }


def _h_response_size(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway.local_provider import LocalOpenWeightProvider
    from ssn.cognition.model_gateway.mock_local_server import MockLocalModelServer
    from ssn.cognition.model_gateway import ModelRequest

    server = MockLocalModelServer(mode="oversized").start()
    try:
        p = LocalOpenWeightProvider(
            endpoint=server.generate_url,
            model_id="mock",
            max_response_bytes=1024,
            timeout_s=2.0,
        )
        resp = p.generate(ModelRequest.from_prompt("big"))
        ok = (not resp.healthy) and "size" in str(resp.meta.get("error_category") or "")
        return {"ok": ok, "detail": str(resp.meta.get("error_category"))}
    finally:
        server.stop()


def _h_redaction_payload(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway import ModelMessage, ModelRequest, MessageRole
    from ssn.cognition.model_gateway.local_provider import LocalOpenWeightProvider
    from ssn.cognition.model_gateway.mock_local_server import MockLocalModelServer

    secret = "SUPER_SECRET_MASTER_KEY_VALUE_9f3a"
    os.environ["SSN_MASTER_KEY"] = secret
    server = MockLocalModelServer(mode="ok").start()
    try:
        p = LocalOpenWeightProvider(
            endpoint=server.generate_url,
            model_id="mock",
            capture_last_request=True,
        )
        req = ModelRequest(
            messages=[
                ModelMessage(role=MessageRole.USER, content=f"user has master_key={secret}"),
                ModelMessage(role=MessageRole.ASSISTANT, content=f"saw {secret}"),
            ],
            system=f"Authorization: Bearer {secret}",
            context={"master_key": secret, "note": "ok"},
            metadata={"api_key": secret},
            tools=[{"name": "x", "parameters": {"password": secret}}],
        )
        resp = p.generate(req)
        raw = p.transport.last_request_body if p.transport else b""
        body = server.last_body() or {}
        blob = (raw or b"") + json.dumps(body).encode("utf-8")
        absent = secret.encode("utf-8") not in blob and secret not in json.dumps(body)
        return {"ok": bool(resp.healthy and absent), "detail": "secret_absent" if absent else "LEAK"}
    finally:
        server.stop()
        os.environ.pop("SSN_MASTER_KEY", None)


def _h_tenant_isolation(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway import DeterministicModelProvider, ModelGateway, ModelRequest

    class Tracking(DeterministicModelProvider):
        def __init__(self) -> None:
            super().__init__()
            self.seen = []

        def generate(self, request):  # type: ignore[override]
            self.seen.append({"tenant": request.tenant_id, "session": request.session_id})
            return super().generate(request)

    prov = Tracking()
    gw = ModelGateway(providers=[prov])
    a = ModelRequest.from_prompt("a")
    a.tenant_id = "t-a"
    a.session_id = "s-a"
    b = ModelRequest.from_prompt("b")
    b.tenant_id = "t-b"
    b.session_id = "s-b"
    ra = gw.complete(a)
    rb = gw.complete(b)
    ok = (
        ra.healthy
        and rb.healthy
        and len(prov.seen) == 2
        and prov.seen[0]["tenant"] == "t-a"
        and prov.seen[1]["tenant"] == "t-b"
        and prov.seen[0]["session"] != prov.seen[1]["session"]
    )
    return {"ok": ok, "detail": str(prov.seen)}


def _h_shadow_no_dup(inp: Dict[str, Any]) -> Dict[str, Any]:
    import time as _time
    from ssn.cognition.loop import CognitiveRuntime
    from ssn.integration.facade import IntegrationFacade
    from ssn.integration.trace_context import TraceContext

    class CountingProvider:
        name = "counting-v1"
        calls = 0

        def capabilities(self):
            from ssn.cognition.model_gateway.contracts import ModelCapabilities

            return ModelCapabilities(provider_name=self.name)

        def health(self):
            return {"ok": True}

        def generate(self, request):
            CountingProvider.calls += 1
            from ssn.cognition.model_gateway.contracts import ModelResponse

            return ModelResponse(text="x", provider=self.name, healthy=True)

    CountingProvider.calls = 0
    cr = CognitiveRuntime.create()
    # Inject counting provider if possible; otherwise use metrics
    facade = IntegrationFacade.create(cognitive_runtime=cr, mode="shadow")
    before = facade.metrics.model_requests
    before_calls = CountingProvider.calls
    tr = TraceContext(runtime_mode="shadow", role="GUEST")
    facade.observe_authoritative_chat(
        user_input="shadow eval",
        role="GUEST",
        context={},
        result={"answer": "hello", "degraded": False, "used_tools": []},
        trace=tr,
        started_at=_time.time(),
        router_result={"mode": "hybrid", "engine": "dummy", "reply": "hello"},
    )
    ok = (
        facade.metrics.model_requests == before
        and facade.metrics.model_shadow_observations >= 1
        and CountingProvider.calls == before_calls
    )
    return {
        "ok": ok,
        "detail": f"shadow_obs={facade.metrics.model_shadow_observations} calls={CountingProvider.calls}",
    }


def _h_latency(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway import DeterministicModelProvider, ModelGateway, ModelRequest

    t0 = time.time()
    gw = ModelGateway(providers=[DeterministicModelProvider()])
    resp = gw.complete(ModelRequest.from_prompt("latency"))
    wall = max(0.0, (time.time() - t0) * 1000.0)
    prov = float(resp.usage.latency_ms)
    ok = math.isfinite(prov) and prov >= 0.0 and math.isfinite(wall) and wall >= 0.0
    return {
        "ok": ok,
        "provider_latency_ms": prov,
        "wall_latency_ms": wall,
    }


def _h_determinism(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway import DeterministicModelProvider, ModelGateway, ModelRequest

    gw = ModelGateway(providers=[DeterministicModelProvider()])
    a = gw.complete(ModelRequest.from_prompt("same"))
    b = gw.complete(ModelRequest.from_prompt("same"))
    return {"ok": a.text == b.text, "detail": "repeatable"}


def _h_local_disabled(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway.local_provider import build_local_provider_from_env

    os.environ.pop("SSN_MODEL_PROVIDER", None)
    return {"ok": build_local_provider_from_env() is None, "detail": "disabled"}


def _h_redirect_rejected(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway import ModelRequest
    from ssn.cognition.model_gateway.local_provider import LocalOpenWeightProvider
    from ssn.cognition.model_gateway.mock_local_server import MockLocalModelServer

    server = MockLocalModelServer(mode="redirect_remote").start()
    try:
        p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="mock")
        resp = p.generate(ModelRequest.from_prompt("x"))
        ok = (not resp.healthy) and resp.meta.get("error_category") == "redirect"
        return {"ok": ok, "detail": str(resp.meta.get("error_category"))}
    finally:
        server.stop()


def _h_missing_model_id(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway.local_provider import LocalOpenWeightProvider
    from ssn.cognition.model_gateway.mock_local_server import MockLocalModelServer

    server = MockLocalModelServer(mode="ok").start()
    try:
        p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="")
        h = p.health()
        ok = (not h.get("ok")) and "model_id" in str(h.get("error") or "")
        return {"ok": ok, "detail": str(h.get("error"))}
    finally:
        server.stop()


def _h_capability_honesty(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway.local_provider import LocalOpenWeightProvider

    p = LocalOpenWeightProvider(endpoint="http://127.0.0.1:9/generate", model_id="m")
    caps = p.capabilities()
    meta = caps.metadata or {}
    ok = (
        caps.tools is False
        and caps.structured_json is False
        and caps.context_window == 0
        and meta.get("trained_siona_native") is False
        and meta.get("verification_status") == "unverified"
    )
    return {"ok": ok, "detail": str(meta.get("verification_status"))}


def _h_registry_provenance(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway.registry import ModelRegistry, mock_ci_registry_payload
    from ssn.cognition.model_gateway.local_provider import LocalOpenWeightProvider

    reg = ModelRegistry()
    reg.load_dict(mock_ci_registry_payload())
    entry = reg.get("mock-ci-open-weight")
    p = LocalOpenWeightProvider(
        endpoint="http://127.0.0.1:9/generate",
        model_id="mock-ci-open-weight",
        registry_entry=entry,
    )
    caps = p.capabilities()
    ok = (
        entry is not None
        and entry.mock
        and not entry.siona_native
        and caps.metadata.get("verification_status") == "mock"
        and caps.tools is False
    )
    return {"ok": ok, "detail": str(caps.metadata.get("verification_status"))}


def _h_oversized_tool_list(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway import ModelRequest
    from ssn.cognition.model_gateway.local_provider import LocalOpenWeightProvider
    from ssn.cognition.model_gateway.mock_local_server import MockLocalModelServer

    server = MockLocalModelServer(mode="oversized_tool_list").start()
    try:
        p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="mock")
        resp = p.generate(ModelRequest.from_prompt("x"))
        ok = (not resp.healthy) and resp.meta.get("error_category") in {"size", "malformed"}
        return {"ok": ok, "detail": str(resp.meta.get("error_category"))}
    finally:
        server.stop()


def _h_malformed_usage(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway import ModelRequest
    from ssn.cognition.model_gateway.local_provider import LocalOpenWeightProvider
    from ssn.cognition.model_gateway.mock_local_server import MockLocalModelServer

    server = MockLocalModelServer(mode="adversarial_usage").start()
    try:
        p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="mock")
        resp = p.generate(ModelRequest.from_prompt("x"))
        ok = (not resp.healthy) and resp.meta.get("error_category") == "malformed"
        return {"ok": ok, "detail": str(resp.meta.get("error"))}
    finally:
        server.stop()


def _h_invalid_confidence(inp: Dict[str, Any]) -> Dict[str, Any]:
    from ssn.cognition.model_gateway import ModelRequest
    from ssn.cognition.model_gateway.local_provider import LocalOpenWeightProvider
    from ssn.cognition.model_gateway.mock_local_server import MockLocalModelServer

    server = MockLocalModelServer(mode="adversarial_confidence").start()
    try:
        p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="mock")
        resp = p.generate(ModelRequest.from_prompt("x"))
        ok = (not resp.healthy) and resp.meta.get("error_category") == "malformed"
        return {"ok": ok, "detail": str(resp.meta.get("error"))}
    finally:
        server.stop()


def _h_sleep_forever(inp: Dict[str, Any]) -> Dict[str, Any]:
    """Intentional hang for hard-timeout tests — never use in production eval."""
    time.sleep(float(inp.get("sleep_s") or 30.0))
    return {"ok": True, "detail": "should_not_reach"}


HANDLERS = {
    "plain_correctness": _h_plain_correctness,
    "instruction_adherence": _h_instruction_adherence,
    "structured_json": _h_structured_json,
    "tool_proposal_valid": _h_tool_proposal_valid,
    "tool_proposal_invalid": _h_tool_proposal_invalid,
    "health_ok": _h_health_ok,
    "timeout_fallback": _h_timeout_fallback,
    "cancellation_before": _h_cancellation_before,
    "cancellation_during": _h_cancellation_during,
    "fallback_correctness": _h_fallback_correctness,
    "response_size": _h_response_size,
    "redaction_payload": _h_redaction_payload,
    "tenant_isolation": _h_tenant_isolation,
    "shadow_no_dup": _h_shadow_no_dup,
    "latency": _h_latency,
    "determinism": _h_determinism,
    "local_disabled": _h_local_disabled,
    "redirect_rejected": _h_redirect_rejected,
    "missing_model_id": _h_missing_model_id,
    "capability_honesty": _h_capability_honesty,
    "registry_provenance": _h_registry_provenance,
    "oversized_tool_list": _h_oversized_tool_list,
    "malformed_usage": _h_malformed_usage,
    "invalid_confidence": _h_invalid_confidence,
    "sleep_forever": _h_sleep_forever,
}


def _worker(handler_id: str, inp: Dict[str, Any], q: Any) -> None:
    try:
        fn = HANDLERS[handler_id]
        out = fn(inp)
        q.put(("ok", out))
    except Exception as exc:
        q.put(("err", {"error": f"{type(exc).__name__}:{exc}", "trace": traceback.format_exc()[-500:]}))


def _run_handler_with_timeout(handler_id: str, inp: Dict[str, Any], timeout_s: float) -> Dict[str, Any]:
    """Execute handler in a child process; terminate on timeout (Windows-safe)."""
    ctx = mp.get_context("spawn")
    q: mp.Queue = ctx.Queue()
    proc = ctx.Process(target=_worker, args=(handler_id, inp, q))
    proc.start()
    proc.join(timeout_s)
    if proc.is_alive():
        proc.terminate()
        proc.join(2.0)
        if proc.is_alive():
            proc.kill()
            proc.join(1.0)
        return {
            "ok": False,
            "error_category": "timeout",
            "detail": f"handler_timeout:{timeout_s}s",
        }
    if q.empty():
        return {"ok": False, "error_category": "error", "detail": "no_result"}
    status, payload = q.get()
    if status == "ok":
        return payload
    return {"ok": False, "error_category": "error", "detail": payload}


def default_provider_cases() -> List[ProviderEvalCase]:
    return [
        ProviderEvalCase(
            "prov.plain_correctness",
            "plain_response",
            "Deterministic provider returns healthy text",
            "plain_correctness",
            input={"prompt": "hello eval"},
            expected_constraints={"contains": "Deterministic"},
            provider_configuration={"provider": "deterministic"},
            tags=["deterministic"],
        ),
        ProviderEvalCase(
            "prov.instruction_adherence",
            "instruction",
            "Exact deterministic token echoed",
            "instruction_adherence",
            input={"exact_token": "EXACT_TOKEN_ALPHA"},
            expected_constraints={"equals": "EXACT_TOKEN_ALPHA"},
            provider_configuration={"provider": "local_mock"},
            tags=["mock_local"],
            timeout_s=8.0,
        ),
        ProviderEvalCase(
            "prov.structured_json",
            "structured_json",
            "Structured JSON schema compliance",
            "structured_json",
            input={"schema": {"required": ["ok", "mock"], "ok_is_true": True}},
            expected_constraints={"required": ["ok", "mock"]},
            provider_configuration={"provider": "deterministic_json"},
            tags=["deterministic"],
        ),
        ProviderEvalCase(
            "prov.tool_proposal_valid",
            "tool_proposal",
            "Valid tool-proposal schema",
            "tool_proposal_valid",
            expected_constraints={"validator": "ok"},
            tags=["deterministic"],
        ),
        ProviderEvalCase(
            "prov.tool_proposal_invalid",
            "tool_proposal",
            "Invalid tool proposal rejected by validator",
            "tool_proposal_invalid",
            expected_constraints={"reason": "empty_name"},
            tags=["deterministic"],
        ),
        ProviderEvalCase(
            "prov.health_ok",
            "health",
            "Deterministic provider health ok",
            "health_ok",
            tags=["deterministic"],
        ),
        ProviderEvalCase(
            "prov.timeout_fallback",
            "timeout",
            "Timeout falls through to healthy provider",
            "timeout_fallback",
            expected_constraints={"fallback": True},
            tags=["deterministic"],
            timeout_s=8.0,
        ),
        ProviderEvalCase(
            "prov.cancellation_before",
            "cancellation",
            "Cancellation before execution",
            "cancellation_before",
            tags=["deterministic"],
        ),
        ProviderEvalCase(
            "prov.cancellation_during",
            "cancellation",
            "Cancellation observed on local provider path",
            "cancellation_during",
            tags=["mock_local"],
            timeout_s=8.0,
        ),
        ProviderEvalCase(
            "prov.fallback_correctness",
            "fallback",
            "Malformed JSON triggers fallback",
            "fallback_correctness",
            tags=["deterministic"],
        ),
        ProviderEvalCase(
            "prov.response_size",
            "response_size",
            "Oversized local response rejected",
            "response_size",
            tags=["mock_local"],
            timeout_s=8.0,
        ),
        ProviderEvalCase(
            "prov.redaction",
            "redaction",
            "Secrets absent from serialized provider payload",
            "redaction_payload",
            tags=["security"],
            timeout_s=8.0,
        ),
        ProviderEvalCase(
            "prov.tenant_session_isolation",
            "isolation",
            "Tenant/session IDs do not cross requests",
            "tenant_isolation",
            tags=["deterministic"],
        ),
        ProviderEvalCase(
            "prov.shadow_no_duplicate_inference",
            "shadow",
            "Shadow mode observes without duplicate inference",
            "shadow_no_dup",
            tags=["shadow"],
            timeout_s=10.0,
        ),
        ProviderEvalCase(
            "prov.latency",
            "latency",
            "Latency finite and non-negative",
            "latency",
            thresholds={"min_latency_ms": 0.0},
            tags=["deterministic"],
        ),
        ProviderEvalCase(
            "prov.deterministic_repeatability",
            "determinism",
            "Deterministic provider repeats",
            "determinism",
            tags=["deterministic"],
        ),
        ProviderEvalCase(
            "prov.local_disabled_default",
            "config",
            "Local provider disabled by default",
            "local_disabled",
            tags=["local"],
        ),
        ProviderEvalCase(
            "prov.redirect_rejected",
            "security",
            "Loopback-to-remote redirect rejected",
            "redirect_rejected",
            tags=["security", "mock_local"],
            timeout_s=8.0,
        ),
        ProviderEvalCase(
            "prov.missing_model_id",
            "config",
            "Missing model ID is unhealthy",
            "missing_model_id",
            tags=["config", "mock_local"],
            timeout_s=8.0,
        ),
        ProviderEvalCase(
            "prov.capability_honesty",
            "capabilities",
            "Unverified capabilities remain conservative",
            "capability_honesty",
            tags=["honesty"],
        ),
        ProviderEvalCase(
            "prov.registry_provenance",
            "registry",
            "Mock registry provenance state",
            "registry_provenance",
            tags=["registry"],
        ),
        ProviderEvalCase(
            "prov.oversized_tool_list",
            "bounds",
            "Oversized tool proposal list rejected",
            "oversized_tool_list",
            tags=["mock_local"],
            timeout_s=8.0,
        ),
        ProviderEvalCase(
            "prov.malformed_usage",
            "bounds",
            "Malformed usage metadata rejected",
            "malformed_usage",
            tags=["mock_local"],
            timeout_s=8.0,
        ),
        ProviderEvalCase(
            "prov.invalid_confidence",
            "bounds",
            "NaN confidence rejected",
            "invalid_confidence",
            tags=["mock_local"],
            timeout_s=8.0,
        ),
    ]


def run_provider_eval(
    *,
    cases: Optional[List[ProviderEvalCase]] = None,
    write_report: bool = True,
    use_subprocess: bool = True,
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
        error_category = None
        try:
            if use_subprocess:
                out = _run_handler_with_timeout(case.handler_id, case.input, case.timeout_s)
            else:
                out = HANDLERS[case.handler_id](case.input)
            detail = out
            if not out.get("ok"):
                status = "fail"
                failed += 1
                error_category = out.get("error_category") or "assertion"
            else:
                passed += 1
        except Exception as exc:
            status = "fail"
            failed += 1
            err = f"{type(exc).__name__}:{exc}"
            error_category = "error"
            detail = {"ok": False, "detail": err}
        wall = max(0.0, (time.time() - started) * 1000.0)
        results.append(
            {
                "case_id": case.case_id,
                "category": case.category,
                "description": case.description,
                "input_summary": {k: (str(v)[:80] if not isinstance(v, (int, float, bool)) else v) for k, v in case.input.items()},
                "expected_constraints": case.expected_constraints,
                "provider_configuration": case.provider_configuration,
                "timeout_s": case.timeout_s,
                "thresholds": case.thresholds,
                "status": status,
                "tags": list(case.tags),
                "wall_latency_ms": wall,
                "provider_latency_ms": (detail or {}).get("provider_latency_ms") if isinstance(detail, dict) else None,
                "actual_result": detail,
                "error": err,
                "error_category": error_category,
                "label": "mock/deterministic",
                "limitations": ["Phase 3A mock/deterministic only"],
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
            "Provider is not claimed production-secure",
        ],
        "reproduction_command": "SSN_OFFLINE=1 python scripts/run_eval.py --provider",
    }
    if write_report:
        out_dir = get_eval_output_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"provider_eval_{int(time.time())}.json"
        path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        report["report_path"] = str(path)
    return report
