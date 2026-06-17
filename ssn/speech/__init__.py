"""Optional offline speech backends (STT/TTS). CI-safe defaults; real I/O via env + optional deps."""

from ssn.speech.backends import get_stt_backend, get_tts_backend, stt_listen, tts_speak

__all__ = ["get_stt_backend", "get_tts_backend", "stt_listen", "tts_speak"]
