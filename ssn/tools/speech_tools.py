from __future__ import annotations

from typing import Any, Dict

from ssn.speech.backends import stt_listen, tts_speak
from ssn.tools.contracts import ToolSpec


_MAX_TEXT_LEN = 500
_MAX_LANG_LEN = 16


def _safe_str(v: Any, *, max_len: int) -> str:
    if not isinstance(v, str):
        return ""
    return v.strip()[:max_len]


def _speech_stt_listen_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Offline speech-to-text (optional mic / whisper backends).
    """
    lang = _safe_str(args.get("language", "en"), max_len=_MAX_LANG_LEN) or "en"
    text_bypass = _safe_str(args.get("text"), max_len=_MAX_TEXT_LEN) or None
    audio_path = _safe_str(args.get("audio_path"), max_len=512) or None

    record_seconds = args.get("record_seconds")
    rs = None
    if isinstance(record_seconds, (int, float)):
        rs = float(record_seconds)

    out = stt_listen(
        language=lang,
        text_override=text_bypass,
        audio_path=audio_path,
        record_seconds=rs,
    )
    return out


def _speech_tts_speak_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Offline text-to-speech. External effect; approval-gated upstream.
    """
    text = _safe_str(args.get("text"), max_len=_MAX_TEXT_LEN)
    if not text:
        return {
            "ok": False,
            "error": {"code": "BAD_REQUEST", "message": "text is required"},
        }

    voice = _safe_str(args.get("voice", "default"), max_len=32) or "default"
    lang = _safe_str(args.get("language", "en"), max_len=_MAX_LANG_LEN) or "en"

    return tts_speak(text=text, voice=voice, language=lang)


def register_speech_tools(registry) -> None:
    registry.register(
        ToolSpec(
            name="speech.stt.listen",
            description="Listen and transcribe speech (offline backends; optional deps).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=False,
            max_calls_per_minute=10,
            input_schema={
                "language": {"type": "string", "required": False, "max_length": _MAX_LANG_LEN},
                "text": {"type": "string", "required": False, "max_length": _MAX_TEXT_LEN},
                "audio_path": {"type": "string", "required": False},
                "record_seconds": {"type": "number", "required": False},
            },
            handler=_speech_stt_listen_handler,
        )
    )

    registry.register(
        ToolSpec(
            name="speech.tts.speak",
            description="Speak text aloud (approval-gated; offline TTS backends).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=True,
            external_effect=True,
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
