# ssn/tools/media_tools.py

from __future__ import annotations

from typing import Any, Dict

from ssn.tools.contracts import ToolSpec


_MAX_PROMPT_LEN = 500
_MAX_STYLE_LEN = 100


def _safe_str(v: Any, *, max_len: int) -> str:
    if not isinstance(v, str):
        return ""
    return v.strip()[:max_len]


# --------------------------------------------------
# Handlers (placeholders – no real generation yet)
# --------------------------------------------------

def _image_generate_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    prompt = _safe_str(args.get("prompt"), max_len=_MAX_PROMPT_LEN)
    if not prompt:
        return {
            "ok": False,
            "error": {"code": "BAD_REQUEST", "message": "prompt is required"},
        }

    style = _safe_str(args.get("style", ""), max_len=_MAX_STYLE_LEN)

    return {
        "ok": True,
        "prompt": prompt,
        "style": style,
        "image": None,
        "note": "media.image.generate placeholder – generator not wired yet",
    }


def _image_edit_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    instruction = _safe_str(args.get("instruction"), max_len=_MAX_PROMPT_LEN)
    if not instruction:
        return {
            "ok": False,
            "error": {"code": "BAD_REQUEST", "message": "instruction is required"},
        }

    return {
        "ok": True,
        "instruction": instruction,
        "image": None,
        "note": "media.image.edit placeholder – editor not wired yet",
    }


# --------------------------------------------------
# Registration
# --------------------------------------------------

def register_media_tools(registry) -> None:
    registry.register(
        ToolSpec(
            name="media.image.generate",
            description="Generate an image or diagram from a prompt (read-only output).",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=False,
            external_effect=False,
            max_calls_per_minute=10,
            input_schema={
                "prompt": {"type": "string", "required": True, "max_length": _MAX_PROMPT_LEN},
                "style": {"type": "string", "required": False, "max_length": _MAX_STYLE_LEN},
            },
            handler=_image_generate_handler,
        )
    )

    registry.register(
        ToolSpec(
            name="media.image.edit",
            description="Edit an image using instructions (read-only output).",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=False,
            external_effect=False,
            max_calls_per_minute=10,
            input_schema={
                "instruction": {"type": "string", "required": True, "max_length": _MAX_PROMPT_LEN},
            },
            handler=_image_edit_handler,
        )
    )
