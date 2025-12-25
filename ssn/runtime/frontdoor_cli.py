# ssn/runtime/frontdoor_cli.py

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, Optional

from ssn.bootstrap import create_siona
from ssn.runtime.runtime_builder import SSNRuntimeBuilder
from ssn.interfaces.front_door import handle_user_message


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _parse_json_dict(s: str) -> dict:
    try:
        out = json.loads(s)
        return out if isinstance(out, dict) else {}
    except Exception:
        return {}


def _get_env_master_key() -> Optional[str]:
    mk = os.environ.get("SSN_MASTER_KEY")
    if isinstance(mk, str) and mk.strip():
        return mk.strip()
    return None


def _forced_offline() -> bool:
    return os.getenv("SSN_OFFLINE") == "1"


def _safe_ctx(base: Optional[dict] = None) -> dict:
    """
    Safety rule: never carry master_key in context (top-level or nested),
    except in context["meta"]["master_key"] which FrontDoor is allowed to read.
    """
    ctx = dict(base or {})

    # remove top-level secrets
    ctx.pop("master_key", None)
    ctx.pop("ssn_master_key", None)

    # remove nested auth.* secrets
    auth = ctx.get("auth")
    if isinstance(auth, dict):
        auth2 = dict(auth)
        auth2.pop("master_key", None)
        auth2.pop("ssn_master_key", None)
        ctx["auth"] = auth2

    # ensure meta does not accidentally contain other secret keys besides master_key
    meta = ctx.get("meta")
    if isinstance(meta, dict):
        meta2 = dict(meta)
        meta2.pop("ssn_master_key", None)
        ctx["meta"] = meta2

    return ctx


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ssn-frontdoor", description="Production-style Front Door CLI.")
    p.add_argument("--text", default=None, help="Single message to send. If omitted, starts a REPL.")
    p.add_argument("--context", default="{}", help='JSON dict, e.g. \'{"offline":true,"allow_tools":true}\'')
    p.add_argument("--offline", action="store_true", help="Force offline mode for deterministic tests.")
    p.add_argument("--json", action="store_true", help="Print full envelope JSON (default).")
    p.add_argument("--answer_only", action="store_true", help="Print answer only.")
    p.add_argument("--master_key", default=None, help="OWNER master key (or set SSN_MASTER_KEY env var).")
    args = p.parse_args(argv)

    mk = (
        args.master_key.strip()
        if isinstance(args.master_key, str) and args.master_key.strip()
        else (_get_env_master_key() or None)
    )

    # Canonical build
    orch = create_siona(output_mode="full")
    rt = SSNRuntimeBuilder(orchestrator=orch, default_role="GUEST").build()

    deps = dict(getattr(rt.gateway, "deps", {}) or {})
    deps.setdefault("orchestrator", orch)

    # ADD THIS (so FrontDoor can reuse InterfaceGateway "think" path):
    deps["gateway"] = rt.gateway

    # Hard invariant: FrontDoor must use the shared registry
    if getattr(orch, "tools", None) is not None:
        deps["tool_registry"] = orch.tools

    base_ctx = _parse_json_dict(args.context)
    base_ctx = _safe_ctx(base_ctx)

    # Apply offline flags (env wins)
    if _forced_offline():
        base_ctx["offline"] = True
    elif args.offline:
        base_ctx["offline"] = True

    # Production rule: provide secrets only via context["meta"]["master_key"]
    if mk:
        meta = base_ctx.get("meta")
        if not isinstance(meta, dict):
            meta = {}
        meta["master_key"] = mk
        base_ctx["meta"] = meta

    def send(text: str, turn_id: int) -> Dict[str, Any]:
        ctx = _safe_ctx(dict(base_ctx))
        ctx.setdefault("session_id", "frontdoor-cli")
        ctx["turn_id"] = str(turn_id)
        return handle_user_message(text, deps, ctx)

    # Single-shot
    if isinstance(args.text, str) and args.text.strip():
        out = send(args.text.strip(), 1)
        if args.answer_only and isinstance(out, dict):
            print(str(out.get("answer", "")))
        else:
            _print_json(out)
        return 0

    # REPL
    turn = 0
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not line:
            continue
        if line.lower() in {"exit", "quit"}:
            return 0

        turn += 1
        out = send(line, turn)

        if args.answer_only and isinstance(out, dict):
            print(f"siona> {out.get('answer', '')}")
        else:
            _print_json(out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
