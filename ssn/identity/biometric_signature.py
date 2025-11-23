"""
SSN Identity Module: Biometric Signature (Phase 1 stub)

This module provides the interface for biometric identity checks:
- face embedding
- voice embedding
- gait signature
- typing rhythm

In Phase 1, these functions return simple placeholder values.
In Phase 3, they will integrate real ML/SNN encoders.

Design goals:
- Simple, safe, deterministic placeholder behavior
- No external dependencies during Phase 1
- Easy to replace with real models later
"""

from __future__ import annotations
import hashlib
from typing import Dict, Optional


# -----------------------------
# Internal helper
# -----------------------------
def _hash_biometric_stub(data: str) -> str:
    """
    Create a deterministic hash of any biometric input.
    This is ONLY a stub for early system logic.

    Real biometric embeddings will replace this later.
    """
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# -----------------------------
# Public API
# -----------------------------
def extract_face_embedding(image_bytes: Optional[bytes]) -> str:
    """
    Extract a placeholder face embedding from image bytes.

    Phase 1: returns a hash of the bytes length.
    Phase 3: will return vector embedding from a real model.
    """
    if image_bytes is None:
        return ""
    return _hash_biometric_stub(f"face:{len(image_bytes)}")


def extract_voice_embedding(audio_bytes: Optional[bytes]) -> str:
    """
    Extract a placeholder voice embedding.

    Phase 1: returns a hash of length.
    Phase 3: will use spectrogram + encoders.
    """
    if audio_bytes is None:
        return ""
    return _hash_biometric_stub(f"voice:{len(audio_bytes)}")


def extract_gait_signature(sensor_data: Optional[str]) -> str:
    """
    Extract placeholder gait signature.
    In the future: integrate IMU + SNN pipeline.
    """
    if not sensor_data:
        return ""
    return _hash_biometric_stub(f"gait:{sensor_data}")


def extract_typing_pattern(text_timing: Optional[str]) -> str:
    """
    Extract placeholder typing rhythm signature.
    """
    if not text_timing:
        return ""
    return _hash_biometric_stub(f"typing:{text_timing}")


# -----------------------------
# Combined Check
# -----------------------------
def generate_biometric_fingerprint(
    face: Optional[bytes] = None,
    voice: Optional[bytes] = None,
    gait: Optional[str] = None,
    typing: Optional[str] = None,
) -> Dict[str, str]:
    """
    Generate a combined biometric fingerprint.

    This is used by owner_verification.py to match
    Samson's multi-modal identity.
    """
    return {
        "face": extract_face_embedding(face),
        "voice": extract_voice_embedding(voice),
        "gait": extract_gait_signature(gait),
        "typing": extract_typing_pattern(typing),
    }
