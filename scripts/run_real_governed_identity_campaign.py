#!/usr/bin/env python3
"""
EXP-3B-008 — controlled real-Qwen governed identity campaign runner.

Does NOT start llama-server. Operator must start llama-server separately.

Heuristic classifications are screening aids only — not authoritative.
Operator adjudication is required before experiment acceptance.

Raw evidence is written outside Git under:
  C:\\Users\\njaji\\SIONA\\reports\\EXP-3B-008
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ssn.governance.identity_campaign import (
    ALLOWED_ENDPOINT,
    CampaignError,
    MAX_OUTPUT_TOKENS,
    NOT_CAPTURED,
    OBSERVABILITY_UNAVAILABLE,
    ProbeRecord,
    ProbeSpec,
    build_probe_catalog,
    check_server_model_id,
    classify_probe_heuristic,
    extract_provider_observability,
    sanitize_excerpt,
    validate_campaign_environment,
    verify_governed_invariants,
)

EVIDENCE_DIR = Path(r"C:\Users\njaji\SIONA\reports\EXP-3B-008")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _guest_policy_context() -> Any:
    from ssn.governance.policy import PolicyContext

    return PolicyContext(
        actor_id="guest:campaign-exp-3b-008",
        actor_authenticated=False,
        verified_owner=False,
        authorized_company_approver_ids=(),
    )


def _select_records(registry: Any, subject_ids: tuple[str, ...]) -> tuple[Any, ...]:
    if not subject_ids:
        return ()
    return registry.select_by_subject_ids(list(subject_ids))


def _run_single_probe(
    engine: Any,
    registry: Any,
    probe: ProbeSpec,
    run_index: int,
) -> ProbeRecord:
    from ssn.governance.runtime_context import (
        ContextAudience,
        GOVERNED_INPUT_KEY,
        GovernedContextInput,
    )

    selected_ids = list(probe.subject_ids)
    selected_records: tuple[Any, ...] = ()
    if probe.use_governed:
        selected_records = _select_records(registry, probe.subject_ids)
        selected_ids = [r.subject_id for r in selected_records]

    context: Dict[str, Any] = {}
    if probe.use_governed:
        context[GOVERNED_INPUT_KEY] = GovernedContextInput(
            records=selected_records,
            policy_context=_guest_policy_context(),
            audience=ContextAudience.PUBLIC_RESPONSE,
            request_id=f"{probe.probe_id}:{run_index}",
        )

    start = time.perf_counter()
    if probe.response_format == "json":
        from ssn.cognition.model_gateway.contracts import (
            MessageRole,
            ModelMessage,
            ModelRequest,
        )
        from ssn.core.llm_providers import LLMRequest
        from ssn.governance.runtime_context import prepare_llm_request

        req = LLMRequest(prompt=probe.prompt, role="GUEST", context=context or None)
        prepared, diag, _ = prepare_llm_request(req)
        model_req = ModelRequest(
            messages=[ModelMessage(role=MessageRole.USER, content=prepared.prompt)],
            role="GUEST",
            context=prepared.context,
            max_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.0,
            response_format="json",
        )
        gateway_llm = engine._provider._inner
        if hasattr(gateway_llm, "_provider") and hasattr(gateway_llm._provider, "complete"):
            model_resp = gateway_llm._provider.complete(model_req)
        elif hasattr(gateway_llm, "complete"):
            model_resp = gateway_llm.complete(model_req)
        else:
            raise CampaignError("structured_json_provider_unavailable")
        reply = model_resp.text
        meta = {
            "used_context": bool(diag and diag.get("has_context_block")),
            "fallback_used": model_resp.fallback_used,
            "engine": model_resp.provider,
            "governed_context": diag,
            **extract_provider_observability(
                {
                    "provider_tool_call_count": len(model_resp.tool_calls),
                    "provider_tool_calls_present": bool(model_resp.tool_calls),
                    "prompt_tokens": model_resp.usage.prompt_tokens,
                    "completion_tokens": model_resp.usage.completion_tokens,
                    "total_tokens": model_resp.usage.total_tokens,
                    "structured_present": model_resp.structured is not None,
                }
            ),
        }
    else:
        out = engine.process(probe.prompt, context=context or None, role="GUEST")
        reply = str(out.get("reply", ""))
        meta = dict(out)
        if "provider_tool_call_count" not in meta:
            meta.update(
                {
                    "provider_tool_call_count": NOT_CAPTURED,
                    "provider_tool_calls_present": NOT_CAPTURED,
                    "prompt_tokens": OBSERVABILITY_UNAVAILABLE,
                    "completion_tokens": OBSERVABILITY_UNAVAILABLE,
                    "total_tokens": OBSERVABILITY_UNAVAILABLE,
                    "structured_present": NOT_CAPTURED,
                }
            )

    latency_ms = (time.perf_counter() - start) * 1000.0
    governed = meta.get("governed_context") or {}
    included_ids = list(governed.get("included_ids") or [])
    heuristic_class, heuristic_reason = classify_probe_heuristic(
        probe,
        reply,
        included_ids,
        bool(meta.get("used_context")),
        governed,
        bool(meta.get("fallback_used")),
    )
    observability = extract_provider_observability(meta)
    record = ProbeRecord(
        probe_id=probe.probe_id,
        run_index=run_index,
        selected_subject_ids=selected_ids,
        governed_supplied=probe.use_governed,
        candidate_count=int(governed.get("candidate_count") or len(selected_ids)),
        included_count=int(governed.get("included_count") or len(included_ids)),
        denied_count=int(governed.get("denied_count") or 0),
        included_ids=included_ids,
        used_context=bool(meta.get("used_context")),
        provider_name=str(meta.get("engine") or ""),
        fallback_used=bool(meta.get("fallback_used")),
        model_id=os.environ.get("SSN_LOCAL_MODEL_ID", ""),
        latency_ms=latency_ms,
        heuristic_classification=heuristic_class,
        heuristic_reason=heuristic_reason,
        operator_classification=None,
        final_classification=None,
        adjudication_status="PENDING_OPERATOR_REVIEW",
        prompt_tokens=observability["prompt_tokens"],
        completion_tokens=observability["completion_tokens"],
        total_tokens=observability["total_tokens"],
        provider_tool_call_count=observability["provider_tool_call_count"],
        provider_tool_calls_present=observability["provider_tool_calls_present"],
        structured_present=observability["structured_present"],
        reply_excerpt=sanitize_excerpt(reply),
    )
    verify_governed_invariants(record, probe.subject_ids)
    return record


def _write_evidence(
    records: List[ProbeRecord],
    raw_replies: List[Dict[str, Any]],
    summary: Dict[str, Any],
) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_path = EVIDENCE_DIR / f"raw_probe_responses_{stamp}.json"
    summary_path = EVIDENCE_DIR / f"campaign_summary_{stamp}.json"
    raw_path.write_text(json.dumps(raw_replies, indent=2), encoding="utf-8")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    latest = EVIDENCE_DIR / "campaign_summary_latest.json"
    latest.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary_path


def run_campaign(
    server_check_fn: Optional[Callable[[str, str], str]] = None,
) -> Dict[str, Any]:
    validate_campaign_environment()
    endpoint = os.environ["SSN_LOCAL_MODEL_ENDPOINT"]
    env_id = os.environ.get("SSN_LOCAL_MODEL_ID", "")
    checker = server_check_fn or check_server_model_id
    checker(endpoint, env_id)

    from ssn.core.language_engine import LanguageEngine
    from ssn.governance.identity_registry import load_approved_identity_registry

    registry = load_approved_identity_registry()
    engine = LanguageEngine()
    probes = build_probe_catalog()
    records: List[ProbeRecord] = []
    raw_replies: List[Dict[str, Any]] = []

    for probe in probes:
        for run_index in range(probe.repeats):
            record = _run_single_probe(engine, registry, probe, run_index)
            records.append(record)
            raw_replies.append(
                {
                    "probe_id": probe.probe_id,
                    "run_index": run_index,
                    "subject_ids": list(probe.subject_ids),
                    "reply": record.reply_excerpt,
                    "heuristic_classification": record.heuristic_classification,
                    "heuristic_reason": record.heuristic_reason,
                }
            )

    heuristic_classes = [r.heuristic_classification for r in records]
    summary = {
        "experiment_id": "EXP-3B-008",
        "timestamp": _utc_now(),
        "endpoint": ALLOWED_ENDPOINT,
        "classification_note": (
            "Heuristic classifications are screening aids only. "
            "Operator adjudication is required before acceptance."
        ),
        "probe_count": len(records),
        "heuristic_classifications": heuristic_classes,
        "records": [
            {
                "probe_id": r.probe_id,
                "run_index": r.run_index,
                "selected_subject_ids": r.selected_subject_ids,
                "governed_supplied": r.governed_supplied,
                "candidate_count": r.candidate_count,
                "included_count": r.included_count,
                "denied_count": r.denied_count,
                "included_ids": r.included_ids,
                "used_context": r.used_context,
                "provider_name": r.provider_name,
                "fallback_used": r.fallback_used,
                "heuristic_classification": r.heuristic_classification,
                "heuristic_reason": r.heuristic_reason,
                "operator_classification": r.operator_classification,
                "final_classification": r.final_classification,
                "adjudication_status": r.adjudication_status,
                "provider_tool_call_count": r.provider_tool_call_count,
                "provider_tool_calls_present": r.provider_tool_calls_present,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "total_tokens": r.total_tokens,
                "structured_present": r.structured_present,
                "latency_ms": round(r.latency_ms, 2),
                "reply_excerpt": r.reply_excerpt,
            }
            for r in records
        ],
        "latency_ms": {
            "min": round(min(r.latency_ms for r in records), 2),
            "max": round(max(r.latency_ms for r in records), 2),
            "mean": round(sum(r.latency_ms for r in records) / len(records), 2),
        },
        "token_usage_note": (
            "Numeric zero in original text probes indicates metrics were not "
            "captured, not measured zero usage."
        ),
    }
    path = _write_evidence(records, raw_replies, summary)
    summary["summary_path"] = str(path)
    return summary


def main() -> int:
    try:
        summary = run_campaign()
    except CampaignError as exc:
        print(f"CAMPAIGN_FAILED:{exc}")
        return 1
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
