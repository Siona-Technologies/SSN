# ssn/runtime/voice_once.py
"""
Phase 4 — one-shot voice loop: STT → Front Door → TTS (OWNER).
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from ssn.interfaces.contracts import InterfaceRequest
from ssn.interfaces.front_door import handle_user_message
from ssn.runtime.frontdoor_context import forced_offline, mk_frontdoor_context, mk_tool_request_context


def run_voice_once(
    *,
    runtime: Any,
    master_key: Optional[str],
    text: Optional[str] = None,
    language: str = "en",
    offline: bool = True,
    speak: bool = True,
    strict: bool = False,
) -> Dict[str, Any]:
    """
    Run one bounded voice interaction. When ``text`` is provided, STT is skipped.
    """
    if not master_key or not str(master_key).strip():
        return {
            "ok": False,
            "stage": "auth",
            "error": {"code": "MASTER_KEY_REQUIRED", "message": "OWNER master key required (SSN_MASTER_KEY)."},
        }

    mk = str(master_key).strip()
    deps = getattr(getattr(runtime, "gateway", None), "deps", None) or {}
    if "orchestrator" not in deps:
        return {
            "ok": False,
            "stage": "runtime",
            "error": {"code": "ORCHESTRATOR_MISSING", "message": "Runtime gateway deps missing orchestrator."},
        }

    session_id = f"voice-{os.getpid()}"
    turn_id = 1
    eff_offline = bool(offline) or forced_offline()
    lang = (language or "en").strip()[:16] or "en"

    transcript = (text or "").strip() or None
    stt_payload: Optional[Dict[str, Any]] = None

    if not transcript:
        stt_ctx = mk_tool_request_context(
            session_id=session_id,
            turn_id=turn_id,
            tool_name="speech.stt.listen",
            args={"language": lang},
            role="OWNER",
            offline=eff_offline,
            strict=strict,
            allow_tools=True,
            allow_research=False,
            master_key=mk,
        )
        stt_req = InterfaceRequest(
            action="run_tool",
            role="OWNER",
            user_input="",
            context=stt_ctx,
            meta={"master_key": mk},
        )
        stt_resp = runtime.gateway.handle(stt_req)
        stt_data = stt_resp.data if isinstance(stt_resp.data, dict) else {}
        stt_payload = {
            "ok": bool(stt_resp.ok),
            "result": stt_data.get("result"),
            "error": stt_data.get("error"),
        }
        result = stt_data.get("result")
        if isinstance(result, dict):
            tr = result.get("transcript")
            if isinstance(tr, str) and tr.strip():
                transcript = tr.strip()

    if not transcript:
        return {
            "ok": False,
            "stage": "stt",
            "stt": stt_payload,
            "error": {
                "code": "NO_TRANSCRIPT",
                "message": "No transcript. Pass --text, set SSN_STT_TEXT, or install voice deps.",
            },
        }

    fd_ctx = mk_frontdoor_context(
        session_id=session_id,
        turn_id=turn_id + 1,
        role="OWNER",
        offline=eff_offline,
        strict=strict,
        allow_tools=True,
        allow_research=False,
        master_key=mk,
    )

    try:
        fd_out = handle_user_message(transcript, deps, fd_ctx)
    except Exception as exc:
        return {
            "ok": False,
            "stage": "front_door",
            "transcript": transcript,
            "stt": stt_payload,
            "error": {"code": "FRONT_DOOR_FAILED", "message": str(exc)[:300]},
        }

    answer = fd_out.get("answer") if isinstance(fd_out, dict) else None
    answer_s = answer.strip() if isinstance(answer, str) else ""

    tts_payload: Optional[Dict[str, Any]] = None
    if speak and answer_s:
        tts_ctx = mk_tool_request_context(
            session_id=session_id,
            turn_id=turn_id + 2,
            tool_name="speech.tts.speak",
            args={"text": answer_s[:500], "language": lang},
            role="OWNER",
            offline=eff_offline,
            strict=strict,
            allow_tools=True,
            allow_research=False,
            master_key=mk,
            confirm=True,
        )
        tts_req = InterfaceRequest(
            action="run_tool",
            role="OWNER",
            user_input="",
            context=tts_ctx,
            meta={"master_key": mk},
        )
        tts_resp = runtime.gateway.handle(tts_req)
        tts_data = tts_resp.data if isinstance(tts_resp.data, dict) else {}
        tts_payload = {
            "ok": bool(tts_resp.ok),
            "result": tts_data.get("result"),
            "error": tts_data.get("error"),
            "approval": tts_data.get("approval"),
        }

    return {
        "ok": True,
        "transcript": transcript,
        "answer": answer_s or None,
        "stt": stt_payload,
        "tts": tts_payload,
        "front_door": fd_out,
    }
