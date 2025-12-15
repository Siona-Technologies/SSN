# ssn/runtime/cli.py

from __future__ import annotations

import argparse
import json
import os
from typing import Any

from ssn.runtime.runtime_builder import SSNRuntimeBuilder


def _print_json(obj: Any) -> None:
    import json as _json
    print(_json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _get_env_master_key() -> str | None:
    env = os.environ.get("SSN_MASTER_KEY")
    if isinstance(env, str) and env.strip():
        return env.strip()
    return None


def _parse_json_dict(s: str) -> dict:
    try:
        out = json.loads(s)
        return out if isinstance(out, dict) else {}
    except Exception:
        return {}


def _parse_json_list(s: str) -> list:
    try:
        out = json.loads(s)
        return out if isinstance(out, list) else []
    except Exception:
        return []


def main(argv: list[str] | None = None) -> int:
    # Pre-parse master_key anywhere in argv
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--master_key", default=None, help="OWNER master key (or set SSN_MASTER_KEY env var).")
    pre_args, remaining = pre.parse_known_args(argv)

    mk = pre_args.master_key
    if isinstance(mk, str) and mk.strip():
        mk = mk.strip()
    else:
        mk = _get_env_master_key()

    parser = argparse.ArgumentParser(
        prog="ssn-cli",
        description="SSN internal console. Internal-only actions via InterfaceGateway.",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_chat = sub.add_parser("chat", help="Run internal cognition (think) via AgentShell.")
    p_chat.add_argument("--role", default="OWNER", choices=["OWNER", "GUEST"])
    p_chat.add_argument("--text", required=True)
    p_chat.add_argument("--context", default="{}", help='JSON dict, e.g. \'{"topic":"memory"}\'')

    p_state = sub.add_parser("state", help="Explain internal state (read-only).")
    p_state.add_argument("--role", default="OWNER", choices=["OWNER", "GUEST"])

    p_memory = sub.add_parser("memory", help="Summarize memory (read-only).")
    p_memory.add_argument("--role", default="OWNER", choices=["OWNER", "GUEST"])
    p_memory.add_argument("--trace_limit", type=int, default=30)
    p_memory.add_argument("--episodic_limit", type=int, default=10)

    p_suggest = sub.add_parser("suggest", help="Generate suggestions (advisory, read-only output).")
    p_suggest.add_argument("--role", default="OWNER", choices=["OWNER", "GUEST"])
    p_suggest.add_argument("--trace_limit", type=int, default=150)

    p_world = sub.add_parser("world", help="Show world state (bounded + redacted, read-only).")
    p_world.add_argument("--role", default="OWNER", choices=["OWNER", "GUEST"])
    p_world.add_argument("--max_entities", type=int, default=8)
    p_world.add_argument("--max_events", type=int, default=8)
    p_world.add_argument("--include_events", action="store_true", help="Include recent events in output.")
    p_world.add_argument("--context", default="{}", help="JSON dict of extra context to pass.")

    # Phase 6.0 — Perception tick
    p_tick = sub.add_parser("sense-tick", help="Run one bounded perception tick (updates WorldModel).")
    p_tick.add_argument("--role", default="OWNER", choices=["OWNER", "GUEST"])
    p_tick.add_argument("--events", default="[]", help="JSON list of event dicts. If empty, a small synthetic batch is used.")
    p_tick.add_argument("--max_events", type=int, default=25)

    args = parser.parse_args(remaining)

    rt = SSNRuntimeBuilder.build_default(default_role="GUEST")

    # Only attach master_key when role == OWNER.
    # This prevents leaking OWNER credentials into GUEST requests.
    def mk_meta(extra: dict | None = None, *, role: str = "GUEST") -> dict:
        out = dict(extra or {})
        if mk and role == "OWNER":
            out["master_key"] = mk
        return out

    def mk_context(base: dict | None = None, *, role: str = "GUEST") -> dict:
        ctx = dict(base or {})
        if mk and role == "OWNER":
            # Handlers_world / sense_tick use context["master_key"] for verification.
            ctx["master_key"] = mk
        else:
            # Hard safety: never carry master_key in guest context.
            ctx.pop("master_key", None)
            auth = ctx.get("auth")
            if isinstance(auth, dict):
                auth2 = dict(auth)
                auth2.pop("master_key", None)
                ctx["auth"] = auth2
        return ctx

    if args.cmd == "chat":
        ctx = mk_context(_parse_json_dict(args.context), role=args.role)

        resp = rt.shell.handle_event(
            {
                "type": "chat",
                "role": args.role,
                "text": args.text,
                "context": ctx,
                "meta": mk_meta(role=args.role),
            }
        )
        _print_json(resp.__dict__)
        return 0

    if args.cmd == "state":
        resp = rt.shell.handle_event(
            {"type": "state", "role": args.role, "meta": mk_meta(role=args.role)}
        )
        _print_json(resp.__dict__)
        return 0

    if args.cmd == "memory":
        resp = rt.shell.handle_event(
            {
                "type": "memory",
                "role": args.role,
                "meta": mk_meta(
                    {"trace_limit": args.trace_limit, "episodic_limit": args.episodic_limit},
                    role=args.role,
                ),
            }
        )
        _print_json(resp.__dict__)
        return 0

    if args.cmd == "suggest":
        resp = rt.shell.handle_event(
            {
                "type": "suggest",
                "role": args.role,
                "meta": mk_meta({"trace_limit": args.trace_limit}, role=args.role),
            }
        )
        _print_json(resp.__dict__)
        return 0

    if args.cmd == "world":
        ctx_in = _parse_json_dict(args.context)
        ctx_in["max_entities"] = int(args.max_entities)
        ctx_in["max_events"] = int(args.max_events)
        ctx_in["include_events"] = bool(args.include_events)

        ctx = mk_context(ctx_in, role=args.role)

        resp = rt.shell.handle_event(
            {"type": "world", "role": args.role, "text": "", "context": ctx, "meta": mk_meta(role=args.role)}
        )
        _print_json(resp.__dict__)
        return 0

    if args.cmd == "sense-tick":
        evs = _parse_json_list(args.events)
        ctx = mk_context({"events": evs, "max_events": int(args.max_events)}, role=args.role)

        resp = rt.shell.handle_event(
            {"type": "sense_tick", "role": args.role, "text": "", "context": ctx, "meta": mk_meta(role=args.role)}
        )
        _print_json(resp.__dict__)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
