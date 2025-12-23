# ssn/runtime/frontdoor_cli.py

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict

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


def _get_env_master_key() -> str | None:
    mk = os.environ.get("SSN_MASTER_KEY")
    if isinstance(mk, str) and mk.strip():
        return mk.strip()
    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ssn-frontdoor", description="Production-style Front Door CLI.")
    p.add_argument("--text", default=None, help="Single message to send. If omitted, starts a REPL.")
    p.add_argument("--context", default="{}", help='JSON dict, e.g. \'{"offline":true,"allow_tools":true}\'')
    p.add_argument("--offline", action="store_true", help="Force offline mode for deterministic tests.")
    p.add_argument("--json", action="store_true", help="Print full envelope JSON (default).")
    p.add_argument("--answer_only", action="store_true", help="Print answer only.")
    p.add_argument("--master_key", default=None, help="OWNER master key (or set SSN_MASTER_KEY env var).")
    args = p.parse_args(argv)

    mk = args.master_key.strip() if isinstance(args.master_key, str) and args.master_key.strip() else (_get_env_master_key() or "")

    # Canonical build
    orch = create_siona(output_mode="full")
    rt = SSNRuntimeBuilder(orchestrator=orch, default_role="GUEST").build()

    deps = dict(getattr(rt.gateway, "deps", {}) or {})
    # Hard invariant: front_door must use the shared registry
    deps["tool_registry"] = getattr(orch, "tools", None)

    base_ctx = _parse_json_dict(args.context)
    if args.offline:
        base_ctx["offline"] = True

    # Production rule: provide secrets only via context["meta"]["master_key"] (FrontDoor extracts then scrubs)
    if mk:
        meta = base_ctx.get("meta")
        if not isinstance(meta, dict):
            meta = {}
        meta["master_key"] = mk
        base_ctx["meta"] = meta

    def send(text: str, turn_id: int) -> Dict[str, Any]:
        ctx = dict(base_ctx)
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
            print(_print_json(out))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
