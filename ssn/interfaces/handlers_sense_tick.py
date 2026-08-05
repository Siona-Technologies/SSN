# ssn/interfaces/handlers_sense_tick.py

from __future__ import annotations

import time
from typing import Any, Dict, Optional, List

from ssn.interfaces.contracts import InterfaceRequest, InterfaceResponse, ErrorInfo
from ssn.identity.owner_verification import verify_owner, is_samson_verified


def _get_master_key(req: InterfaceRequest) -> Optional[str]:
    if isinstance(req.meta, dict):
        mk = req.meta.get("master_key")
        if isinstance(mk, str) and mk.strip():
            return mk.strip()

    ctx = req.context if isinstance(req.context, dict) else {}
    mk2 = ctx.get("master_key")
    if isinstance(mk2, str) and mk2.strip():
        return mk2.strip()

    return None


def _call_first(obj: Any, names: list[str], *args, **kwargs):
    for n in names:
        fn = getattr(obj, n, None)
        if callable(fn):
            return fn(*args, **kwargs)
    raise AttributeError(f"No compatible method found on {type(obj).__name__}: {names}")


def _coerce_events(ctx: Dict[str, Any], *, max_events: int = 25) -> List[Dict[str, Any]]:
    raw = ctx.get("events", [])
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for it in raw[: max(0, int(max_events))]:
        if isinstance(it, dict):
            out.append(it)
    return out


def _apply_world_update(world_model: Any, pkt: Dict[str, Any]) -> bool:
    if world_model is None:
        return False
    apply_fn = getattr(world_model, "apply_update", None) or getattr(world_model, "update", None)
    if callable(apply_fn):
        try:
            apply_fn(pkt)
            return True
        except Exception:
            return False
    return False


def _synthetic_tick(*, world_model: Any = None, events: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    ts = time.time()

    evs: List[Dict[str, Any]] = []
    if isinstance(events, list) and events:
        for e in events[:25]:
            if isinstance(e, dict):
                et = e.get("type") or "event"
                try:
                    tsf = float(e.get("ts", ts) or ts)
                except Exception:
                    tsf = ts
                try:
                    cf = float(e.get("confidence", 0.6) or 0.6)
                except Exception:
                    cf = 0.6
                evs.append({"type": str(et), "ts": tsf, "confidence": cf})

    if not evs:
        evs = [
            {"type": "vision_detection", "ts": ts, "confidence": 0.7},
            {"type": "motion_event", "ts": ts, "confidence": 0.6},
        ]

    pkt = {
        "type": "world_update",
        "ts": ts,
        "source": "sense_tick",
        "entities": [
            {
                "id": "person:synthetic",
                "entity": "person",
                "status": "present",
                "confidence": 0.7,
                "attributes": {"zone": "front"},
            }
        ],
        "events": evs,
    }

    updated = _apply_world_update(world_model, pkt)

    return {
        "ok": True,
        "processed": len(evs),
        "skipped": 0,
        "world_updated": bool(updated),
        "trace_written": False,
        "ts": ts,
        "world_update": pkt,
        "note": "Fallback synthetic tick used (PerceptionHub not wired).",
    }


def handle_sense_tick(req: InterfaceRequest, deps: Any) -> InterfaceResponse:
    ts0 = time.time()
    depsd = deps if isinstance(deps, dict) else {}

    master_key = _get_master_key(req)
    scores = verify_owner(master_key)
    verified = is_samson_verified(scores)

    # Force response role (do NOT trust req.role)
    resp_role = "OWNER" if verified else "GUEST"

    if not verified:
        return InterfaceResponse(
            ok=True,
            action="sense_tick",
            role=resp_role,
            data={
                "identity_verified": False,
                "role": "GUEST",
                "allowed": False,
                "final_result": "BLOCKED_BY_POLICY",
                "scores": scores,
            },
            error=None,
        )

    orch = depsd.get("orchestrator")

    world_model = depsd.get("world_model") or (getattr(orch, "world_model", None) if orch else None)
    memory_hub = (
        depsd.get("memory_hub")
        or (getattr(orch, "memory_hub", None) if orch else None)
        or (getattr(orch, "memory", None) if orch else None)
    )
    perception_hub = depsd.get("perception_hub") or (getattr(orch, "perception_hub", None) if orch else None)

    if world_model is None:
        try:
            from ssn.world.world_model import WorldModel  # type: ignore
            world_model = WorldModel()
        except Exception:
            world_model = None

    report: Dict[str, Any] = {
        "ok": True,
        "processed": 0,
        "skipped": 0,
        "world_updated": False,
        "trace_written": False,
        "ts": ts0,
        "note": "Phase 6.0 perception tick completed (bounded, internal-only).",
    }

    ctx = req.context if isinstance(req.context, dict) else {}
    max_events = int(ctx.get("max_events", 25) or 25)
    max_events = max(0, min(max_events, 50))
    evs = _coerce_events(ctx, max_events=max_events)

    out: Dict[str, Any] = {}
    try:
        if perception_hub is None:
            out = _synthetic_tick(world_model=world_model, events=evs)
        else:
            try:
                out = _call_first(
                    perception_hub,
                    ["tick", "run_tick", "run_once", "step", "process"],
                    world_model=world_model,
                    events=evs,
                )
            except TypeError:
                try:
                    out = _call_first(
                        perception_hub,
                        ["tick", "run_tick", "run_once", "step", "process"],
                        world_model=world_model,
                    )
                except TypeError:
                    out = _call_first(perception_hub, ["tick", "run_tick", "run_once", "step", "process"])
    except Exception as e:
        report["ok"] = False
        report["note"] = f"PerceptionHub error: {e}"
        return InterfaceResponse(
            ok=False,
            action="sense_tick",
            role=resp_role,
            data={
                "identity_verified": True,
                "role": "OWNER",
                "allowed": True,
                "scores": scores,
                "report": report,
            },
            error=ErrorInfo(code="SENSE_TICK_FAILED", message=str(e), details={}),
        )

    if isinstance(out, dict):
        report["ok"] = bool(out.get("ok", report["ok"]))
        report["processed"] = int(out.get("processed", report["processed"]) or report["processed"])
        report["skipped"] = int(out.get("skipped", report["skipped"]) or report["skipped"])
        report["world_updated"] = bool(out.get("world_updated", report["world_updated"]))
        report["trace_written"] = bool(out.get("trace_written", report["trace_written"]))
        report["ts"] = float(out.get("ts", report["ts"]) or report["ts"])
        if isinstance(out.get("note"), str) and out.get("note"):
            report["note"] = out["note"]

        pkt = out.get("world_update")
        if isinstance(pkt, dict) and not report["world_updated"]:
            if _apply_world_update(world_model, pkt):
                report["world_updated"] = True

    # Trace (best-effort, bounded)
    if memory_hub is not None:
        trace = (
            getattr(memory_hub, "add_trace", None)
            or getattr(memory_hub, "write_trace", None)
            or getattr(memory_hub, "log_trace", None)
        )
        if callable(trace):
            try:
                trace(
                    {
                        "type": "sense_tick",
                        "ts": report["ts"],
                        "source": "sense_tick",
                        "event_count": int(report["processed"]) + int(report["skipped"]),
                        "processed": int(report["processed"]),
                        "skipped": int(report["skipped"]),
                        "world_updated": bool(report["world_updated"]),
                        "note": str(report.get("note", ""))[:200],
                    }
                )
                report["trace_written"] = True
            except Exception:
                pass

    # Phase 2 observation (non-authoritative; does not change tick result)
    try:
        integration = depsd.get("integration")
        if integration is not None:
            from ssn.integration.trace_context import TraceContext
            from ssn.integration.runtime_modes import get_runtime_mode

            mode = get_runtime_mode()
            if mode.value != "legacy":
                # Derive from this InterfaceRequest only — never shared deps trace state.
                tr = TraceContext.extract_or_create(
                    context=req.context if isinstance(req.context, dict) else {},
                    meta=req.meta if isinstance(getattr(req, "meta", None), dict) else {},
                    deps=depsd,
                    role=resp_role,
                    source="sense_tick",
                    runtime_mode=mode.value,
                )
                tick_payload = dict(report)
                if isinstance(out, dict) and isinstance(out.get("world_update"), dict):
                    tick_payload["world_update"] = out.get("world_update")
                fallback = (
                    "Fallback synthetic" in str(report.get("note") or "")
                    or perception_hub is None
                )
                integration.observe_sense_tick(
                    tick_result=tick_payload,
                    trace=tr,
                    fallback=bool(fallback),
                )
    except Exception:
        pass
    return InterfaceResponse(
        ok=bool(report["ok"]),
        action="sense_tick",
        role=resp_role,
        data={
            "identity_verified": True,
            "role": "OWNER",
            "allowed": True,
            "scores": scores,
            "report": report,
        },
        error=None if report["ok"] else ErrorInfo(code="SENSE_TICK_FAILED", message=str(report.get("note", "")), details={}),
    )
