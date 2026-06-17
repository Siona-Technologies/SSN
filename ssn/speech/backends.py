from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import wave
from typing import Any, Dict, Optional

_DEFAULT_SAMPLE_RATE = 16000
_DEFAULT_RECORD_SEC = 5.0


def get_stt_backend() -> str:
    return (os.environ.get("SSN_STT_BACKEND") or "dummy").strip().lower()


def get_tts_backend() -> str:
    return (os.environ.get("SSN_TTS_BACKEND") or "dummy").strip().lower()


def _ok_payload(**fields: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"ok": True}
    out.update(fields)
    return out


def _err_payload(code: str, message: str, **fields: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"ok": False, "error": {"code": code, "message": message}}
    out.update(fields)
    return out


def _record_wav(*, duration_sec: float, sample_rate: int) -> Optional[str]:
    try:
        import sounddevice as sd  # type: ignore
        import numpy as np  # type: ignore
    except Exception:
        return None

    duration = max(0.5, min(float(duration_sec), 30.0))
    frames = int(duration * sample_rate)
    try:
        audio = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="int16")
        sd.wait()
    except Exception:
        return None

    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(np.asarray(audio, dtype="int16").tobytes())
        return path
    except Exception:
        try:
            os.remove(path)
        except Exception:
            pass
        return None


def _run_subprocess(cmd: list[str], *, timeout: float = 120.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _whisper_cli_transcribe(audio_path: str, *, language: str) -> Dict[str, Any]:
    cli = (os.environ.get("SSN_WHISPER_CLI") or "").strip() or shutil.which("whisper")
    if not cli:
        return _err_payload(
            "WHISPER_CLI_MISSING",
            "whisper CLI not found; set SSN_WHISPER_CLI or install whisper.cpp main.",
            backend="whisper_cli",
        )

    extra = (os.environ.get("SSN_WHISPER_ARGS") or "").strip()
    cmd = [cli, "-f", audio_path, "-l", language]
    if extra:
        cmd.extend(extra.split())

    proc = _run_subprocess(cmd)
    if proc.returncode != 0:
        return _err_payload(
            "WHISPER_CLI_FAILED",
            (proc.stderr or proc.stdout or "whisper CLI failed").strip()[:300],
            backend="whisper_cli",
        )

    text = (proc.stdout or "").strip()
    if not text and proc.stderr:
        text = proc.stderr.strip()
    if not text:
        return _err_payload("NO_TRANSCRIPT", "whisper CLI returned empty transcript.", backend="whisper_cli")

    return _ok_payload(backend="whisper_cli", transcript=text, language=language)


def _faster_whisper_transcribe(audio_path: str, *, language: str) -> Dict[str, Any]:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception:
        return _err_payload(
            "FASTER_WHISPER_MISSING",
            "Install faster-whisper (see requirements-voice.txt).",
            backend="faster_whisper",
        )

    model_name = (os.environ.get("SSN_WHISPER_MODEL") or "base").strip()
    try:
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments, _info = model.transcribe(audio_path, language=language or None)
        parts = [seg.text.strip() for seg in segments if getattr(seg, "text", "").strip()]
        text = " ".join(parts).strip()
    except Exception as exc:
        return _err_payload("FASTER_WHISPER_FAILED", str(exc)[:300], backend="faster_whisper")

    if not text:
        return _err_payload("NO_TRANSCRIPT", "No speech detected.", backend="faster_whisper")

    return _ok_payload(backend="faster_whisper", transcript=text, language=language, model=model_name)


def stt_listen(
    *,
    language: str = "en",
    text_override: Optional[str] = None,
    audio_path: Optional[str] = None,
    record_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Offline STT entry point. Default backend is CI-safe (no mic).
    """
    lang = (language or "en").strip()[:16] or "en"
    backend = get_stt_backend()

    if isinstance(text_override, str) and text_override.strip():
        return _ok_payload(
            backend="text",
            transcript=text_override.strip(),
            language=lang,
            note="Transcript supplied directly (text bypass).",
        )

    env_text = (os.environ.get("SSN_STT_TEXT") or "").strip()
    if env_text:
        return _ok_payload(
            backend="text",
            transcript=env_text,
            language=lang,
            note="Transcript from SSN_STT_TEXT.",
        )

    if backend == "dummy":
        return _ok_payload(
            backend="dummy",
            transcript=None,
            language=lang,
            spoken=False,
            note="STT dummy backend: no microphone I/O. Set SSN_STT_BACKEND or pass text/audio_path.",
        )

    if backend == "text":
        return _err_payload(
            "TEXT_REQUIRED",
            "SSN_STT_BACKEND=text requires --text, args.text, or SSN_STT_TEXT.",
            backend="text",
            language=lang,
        )

    path = (audio_path or "").strip() or None
    cleanup = False
    if not path:
        dur = float(record_seconds if record_seconds is not None else _DEFAULT_RECORD_SEC)
        path = _record_wav(duration_sec=dur, sample_rate=_DEFAULT_SAMPLE_RATE)
        cleanup = bool(path)
        if not path:
            return _err_payload(
                "MIC_UNAVAILABLE",
                "Microphone capture unavailable. Install sounddevice or pass audio_path / --text.",
                backend=backend,
                language=lang,
            )

    try:
        if backend == "whisper_cli":
            return _whisper_cli_transcribe(path, language=lang)
        if backend in ("faster_whisper", "whisper"):
            return _faster_whisper_transcribe(path, language=lang)
        return _err_payload("UNKNOWN_BACKEND", f"Unknown STT backend: {backend}", backend=backend)
    finally:
        if cleanup and path:
            try:
                os.remove(path)
            except Exception:
                pass


def _piper_speak(*, text: str, voice: str, language: str) -> Dict[str, Any]:
    cli = (os.environ.get("SSN_PIPER_CLI") or "").strip() or shutil.which("piper")
    if not cli:
        return _err_payload(
            "PIPER_MISSING",
            "piper CLI not found; set SSN_PIPER_CLI or install piper.",
            backend="piper_cli",
        )

    model = (os.environ.get("SSN_PIPER_MODEL") or voice or "default").strip()
    fd, out_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    cmd = [cli, "--output_file", out_path]
    if model and model != "default":
        cmd.extend(["--model", model])

    try:
        proc = subprocess.run(
            cmd,
            input=text,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if proc.returncode != 0:
            return _err_payload(
                "PIPER_FAILED",
                (proc.stderr or proc.stdout or "piper failed").strip()[:300],
                backend="piper_cli",
            )

        played = _play_wav(out_path)
        return _ok_payload(
            backend="piper_cli",
            spoken=played,
            text=text,
            voice=voice,
            language=language,
            note="Spoken via piper CLI." if played else "Audio generated; playback unavailable.",
        )
    finally:
        try:
            os.remove(out_path)
        except Exception:
            pass


def _play_wav(path: str) -> bool:
    if sys.platform == "win32":
        try:
            import winsound

            winsound.PlaySound(path, winsound.SND_FILENAME)
            return True
        except Exception:
            return False
    player = shutil.which("ffplay") or shutil.which("aplay")
    if not player:
        return False
    cmd = [player, path]
    if player.endswith("ffplay"):
        cmd = [player, "-nodisp", "-autoexit", path]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=120, check=False)
        return proc.returncode == 0
    except Exception:
        return False


def _pyttsx3_speak(*, text: str, voice: str, language: str) -> Dict[str, Any]:
    try:
        import pyttsx3  # type: ignore
    except Exception:
        return _err_payload(
            "PYTTSX3_MISSING",
            "Install pyttsx3 (see requirements-voice.txt).",
            backend="pyttsx3",
        )

    try:
        engine = pyttsx3.init()
        if voice and voice != "default":
            for v in engine.getProperty("voices") or []:
                name = getattr(v, "name", "") or ""
                if voice.lower() in name.lower():
                    engine.setProperty("voice", v.id)
                    break
        engine.say(text)
        engine.runAndWait()
        return _ok_payload(backend="pyttsx3", spoken=True, text=text, voice=voice, language=language)
    except Exception as exc:
        return _err_payload("PYTTSX3_FAILED", str(exc)[:300], backend="pyttsx3")


def tts_speak(*, text: str, voice: str = "default", language: str = "en") -> Dict[str, Any]:
    """
    Offline TTS entry point. Default backend is CI-safe (no speaker I/O).
    """
    msg = (text or "").strip()
    if not msg:
        return _err_payload("BAD_REQUEST", "text is required")

    lang = (language or "en").strip()[:16] or "en"
    v = (voice or "default").strip()[:32] or "default"
    backend = get_tts_backend()

    if backend == "dummy":
        return _ok_payload(
            backend="dummy",
            spoken=False,
            text=msg,
            voice=v,
            language=lang,
            note="TTS dummy backend: no audio output. Set SSN_TTS_BACKEND=stdout|pyttsx3|piper_cli.",
        )

    if backend == "stdout":
        print(f"[TTS:{lang}] {msg}", flush=True)
        return _ok_payload(
            backend="stdout",
            spoken=True,
            text=msg,
            voice=v,
            language=lang,
            note="Printed to stdout (CI-safe audible simulation).",
        )

    if backend == "pyttsx3":
        return _pyttsx3_speak(text=msg, voice=v, language=lang)

    if backend in ("piper", "piper_cli"):
        return _piper_speak(text=msg, voice=v, language=lang)

    return _err_payload("UNKNOWN_BACKEND", f"Unknown TTS backend: {backend}", backend=backend)
