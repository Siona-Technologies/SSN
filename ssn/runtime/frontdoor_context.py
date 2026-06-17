# ssn/runtime/frontdoor_context.py
"""
Shared Front Door context builders for CLI and HTTP entry points.
"""

from __future__ import annotations

import os
import re
import uuid
from typing import Any, Dict, Optional

_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9._:-]{1,128}$")
_UNSAFE_FILENAME_RE = re.compile(r'[<>:"/\\|?*]+')


def forced_offline() -> bool:
    return os.getenv("SSN_OFFLINE") == "1"


def get_env_master_key() -> Optional[str]:
    env = os.environ.get("SSN_MASTER_KEY")
    if isinstance(env, str) and env.strip():
        return env.strip()
    return None


def normalize_session_id(session_id: Optional[str]) -> str:
    if isinstance(session_id, str) and session_id.strip() and _SESSION_ID_RE.match(session_id.strip()):
        return session_id.strip()
    return f"http-{uuid.uuid4().hex}"


def normalize_role(role: Any) -> str:
    r = str(role or "GUEST").upper().strip()
    return r if r in ("OWNER", "GUEST") else "GUEST"


def safe_context(base: Optional[dict] = None, *, keep_meta_master_key: bool = False) -> dict:
    """
    Never carry master_key at top-level; optionally preserve meta.master_key for Front Door.
    """
    ctx = dict(base or {})
    ctx.pop("master_key", None)
    ctx.pop("ssn_master_key", None)

    auth = ctx.get("auth")
    if isinstance(auth, dict):
        auth2 = dict(auth)
        auth2.pop("master_key", None)
        auth2.pop("ssn_master_key", None)
        ctx["auth"] = auth2

    meta = ctx.get("meta")
    if isinstance(meta, dict):
        meta2 = dict(meta)
        if not keep_meta_master_key:
            meta2.pop("master_key", None)
            meta2.pop("ssn_master_key", None)
        else:
            meta2.pop("ssn_master_key", None)
        ctx["meta"] = meta2

    return ctx


def mk_frontdoor_context(
    *,
    session_id: str,
    turn_id: int,
    role: str,
    offline: bool,
    strict: bool,
    allow_tools: bool,
    allow_research: bool,
    master_key: Optional[str],
    extra_context: Optional[dict] = None,
) -> dict:
    ctx: Dict[str, Any] = {
        "session_id": session_id,
        "turn_id": str(turn_id),
        "offline": bool(offline) or forced_offline(),
        "strict": bool(strict),
        "allow_tools": bool(allow_tools),
        "allow_research": bool(allow_research),
        "role": normalize_role(role),
    }

    if isinstance(extra_context, dict):
        for k, v in extra_context.items():
            if k in ("master_key", "ssn_master_key", "meta", "auth"):
                continue
            ctx[k] = v

    if normalize_role(role) == "OWNER" and master_key:
        meta = dict(ctx.get("meta") or {})
        meta["master_key"] = master_key
        ctx["meta"] = meta

    return safe_context(ctx, keep_meta_master_key=True)


def mk_tool_request_context(
    *,
    session_id: str,
    turn_id: int,
    tool_name: str,
    args: Optional[dict],
    role: str,
    offline: bool,
    strict: bool,
    allow_tools: bool,
    allow_research: bool,
    master_key: Optional[str],
    confirm: bool = False,
    extra_context: Optional[dict] = None,
) -> dict:
    ctx = mk_frontdoor_context(
        session_id=session_id,
        turn_id=turn_id,
        role=role,
        offline=offline,
        strict=strict,
        allow_tools=allow_tools,
        allow_research=allow_research,
        master_key=master_key,
        extra_context=extra_context,
    )
    ctx["tool_name"] = tool_name
    ctx["args"] = dict(args or {})
    if confirm:
        ctx["confirm"] = True
    return ctx
