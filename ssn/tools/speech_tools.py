from __future__ import annotations

from typing import Any, Dict

from ssn.tools.contracts import ToolSpec


_MAX_TEXT_LEN = 500
_MAX_LANG_LEN = 16


def _safe_str(v: Any, *, max_len: int) -> str:
    if not isinstance(v, str):
        return ""
    return v.strip()[:max_len]


# --------------------------------------------------
# Handlers (stubbed – no real I/O yet)
# --------------------------------------------------

def _speech_stt_listen_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Read-only stub for speech-to-text.
    No microphone access yet.
    """
    lang = _safe_str(args.get("language", "en"), max_len=_MAX_LANG_LEN)

    return {
        "ok": True,
        "language": lang,
        "transcript": None,
        "note": "speech.stt.listen placeholder – microphone not wired yet",
    }


def _speech_tts_speak_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stub for text-to-speech.
    This is treated as a state-changing external effect and
    must be approval-gated by the tool execution layer.
    """
    text = _safe_str(args.get("text"), max_len=_MAX_TEXT_LEN)
    if not text:
        return {
            "ok": False,
            "error": {"code": "BAD_REQUEST", "message": "text is required"},
        }

    voice = _safe_str(args.get("voice", "default"), max_len=32)
    lang = _safe_str(args.get("language", "en"), max_len=_MAX_LANG_LEN)

    return {
        "ok": True,
        "spoken": False,
        "text": text,
        "voice": voice,
        "language": lang,
        "note": "speech.tts.speak placeholder – audio output disabled",
    }


# --------------------------------------------------
# Registration
# --------------------------------------------------

def register_speech_tools(registry) -> None:
    # Read-only STT
    registry.register(
        ToolSpec(
            name="speech.stt.listen",
            description="Listen and transcribe speech (read-only stub).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=False,
            max_calls_per_minute=10,
            input_schema={
                "language": {"type": "string", "required": False, "max_length": _MAX_LANG_LEN},
            },
            handler=_speech_stt_listen_handler,
        )
    )

    # Approval-gated TTS (state-changing)
    registry.register(
        ToolSpec(
            name="speech.tts.speak",
            description="Speak text aloud (approval-gated; stub).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=True,   # ← THIS is what triggers approval upstream
            max_calls_per_minute=5,
            input_schema={
                "text": {"type": "string", "required": True, "max_length": _MAX_TEXT_LEN},
                "voice": {"type": "string", "required": False},
                "language": {"type": "string", "required": False},
                "confirm": {"type": "boolean", "required": False},
            },
            handler=_speech_tts_speak_handler,
        )
    )
