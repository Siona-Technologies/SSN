# ssn/runtime/cli.py
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

from ssn.runtime.runtime_builder import SSNRuntimeBuilder
from ssn.interfaces.front_door import handle_user_message
from ssn.interfaces.contracts import InterfaceRequest
from ssn.runtime.frontdoor_context import (
    forced_offline,
    get_env_master_key,
    mk_frontdoor_context,
    safe_context,
)


# -----------------------------
# Helpers
# -----------------------------
def _print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


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


def _render_frontdoor_output(out: dict) -> None:
    """
    Console-friendly output: answer first, then minimal structured extras.
    """
    ans = out.get("answer")
    if isinstance(ans, str) and ans.strip():
        print(ans.strip())
    else:
        print("No answer returned.")

    note = out.get("note")
    if isinstance(note, str) and note.strip():
        print(f"\n[note] {note.strip()}")

    citations = out.get("citations")
    if isinstance(citations, list) and citations:
        print("\n[citations]")
        for i, c in enumerate(citations[:10], start=1):
            if isinstance(c, dict):
                url = c.get("url") or c.get("source_url") or ""
                title = c.get("title") or ""
                quote = c.get("quote") or c.get("snippet") or ""
                line = f"{i}. {title}".strip()
                if url:
                    line += f" — {url}"
                print(line)
                if quote:
                    print(f"   {str(quote)[:300]}")
            else:
                print(f"{i}. {str(c)[:300]}")

    sources = out.get("sources")
    if isinstance(sources, list) and sources:
        print("\n[sources]")
        for i, s in enumerate(sources[:10], start=1):
            if isinstance(s, dict):
                title = s.get("title") or ""
                url = s.get("url") or ""
                print(f"{i}. {title} — {url}".strip())
            else:
                print(f"{i}. {str(s)[:200]}")


# -----------------------------
# Production Console (Front Door REPL)
# -----------------------------
def _run_console(*, runtime, master_key: Optional[str], role_default: str, offline_default: bool, strict_default: bool) -> int:
    deps = getattr(runtime.gateway, "deps", None) or {}
    if "orchestrator" not in deps:
        raise RuntimeError("Runtime gateway deps missing orchestrator; cannot run FrontDoor console.")

    session_id = f"console:{os.getpid()}"
    turn_id = 0

    role = role_default if role_default in ("OWNER", "GUEST") else "GUEST"
    offline = bool(offline_default) or forced_offline()
    strict = bool(strict_default)

    allow_tools = True
    allow_research = True

    def show_status() -> None:
        forced = forced_offline()
        eff_offline = offline or forced
        mk_loaded = bool(master_key)
        print(
            f"[session={session_id} turn={turn_id} role={role} offline={eff_offline} forced_offline={forced} strict={strict} "
            f"tools={allow_tools} research={allow_research} mk={'set' if mk_loaded else 'unset'}]"
        )

    def help_text() -> None:
        print(
            "\nCommands:\n"
            "  :help                  Show this help\n"
            "  :quit / :exit          Exit console\n"
            "  :owner                 Switch UI role to OWNER (requires SSN_MASTER_KEY set)\n"
            "  :guest                 Switch UI role to GUEST\n"
            "  :offline on|off         Toggle offline (env SSN_OFFLINE=1 always wins)\n"
            "  :strict on|off          Toggle strict (passed to FrontDoor context)\n"
            "  :tools on|off           Toggle allow_tools\n"
            "  :research on|off        Toggle allow_research\n"
            "  :raw on|off             Toggle raw JSON output in addition to answer\n"
            "\nUsage:\n"
            "  Type your message and press Enter.\n"
            "  FrontDoor routes: knowledge:, promote:, research ..., or LLM-only.\n"
        )

    raw = False
    print("\n=== SSN Production Console (FrontDoor REPL) ===")
    help_text()

    while True:
        try:
            show_status()
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[exit]")
            return 0

        if not line:
            continue

        if line.startswith(":"):
            cmd = line[1:].strip()
            if cmd in ("quit", "exit"):
                print("[exit]")
                return 0
            if cmd == "help":
                help_text()
                continue

            if cmd == "owner":
                if not master_key:
                    print("Cannot switch to OWNER: SSN_MASTER_KEY is not set in env or --master_key not provided.")
                else:
                    role = "OWNER"
                continue

            if cmd == "guest":
                role = "GUEST"
                continue

            if cmd.startswith("offline "):
                val = cmd.split(" ", 1)[1].strip().lower()
                if val in ("on", "1", "true", "yes"):
                    offline = True
                elif val in ("off", "0", "false", "no"):
                    offline = False
                else:
                    print("Usage: :offline on|off")
                continue

            if cmd.startswith("strict "):
                val = cmd.split(" ", 1)[1].strip().lower()
                if val in ("on", "1", "true", "yes"):
                    strict = True
                elif val in ("off", "0", "false", "no"):
                    strict = False
                else:
                    print("Usage: :strict on|off")
                continue

            if cmd.startswith("tools "):
                val = cmd.split(" ", 1)[1].strip().lower()
                if val in ("on", "1", "true", "yes"):
                    allow_tools = True
                elif val in ("off", "0", "false", "no"):
                    allow_tools = False
                else:
                    print("Usage: :tools on|off")
                continue

            if cmd.startswith("research "):
                val = cmd.split(" ", 1)[1].strip().lower()
                if val in ("on", "1", "true", "yes"):
                    allow_research = True
                elif val in ("off", "0", "false", "no"):
                    allow_research = False
                else:
                    print("Usage: :research on|off")
                continue

            if cmd.startswith("raw "):
                val = cmd.split(" ", 1)[1].strip().lower()
                if val in ("on", "1", "true", "yes"):
                    raw = True
                elif val in ("off", "0", "false", "no"):
                    raw = False
                else:
                    print("Usage: :raw on|off")
                continue

            print("Unknown command. Use :help")
            continue

        # Regular turn
        turn_id += 1
        ctx = mk_frontdoor_context(
            session_id=session_id,
            turn_id=turn_id,
            role=role,
            offline=offline,
            strict=strict,
            allow_tools=allow_tools,
            allow_research=allow_research,
            master_key=master_key,
        )

        out = handle_user_message(line, deps, ctx)

        print("")  # spacing
        _render_frontdoor_output(out)

        if raw:
            print("\n[raw]")
            _print_json(out)

        print("")  # spacing


# -----------------------------
# Main CLI
# -----------------------------
def main(argv: list[str] | None = None) -> int:
    # Pre-parse master_key anywhere in argv
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--master_key", default=None, help="OWNER master key (or set SSN_MASTER_KEY env var).")
    pre_args, remaining = pre.parse_known_args(argv)

    mk = pre_args.master_key
    if isinstance(mk, str) and mk.strip():
        mk = mk.strip()
    else:
        mk = get_env_master_key()

    parser = argparse.ArgumentParser(
        prog="ssn-cli",
        description="SSN console. Includes production FrontDoor REPL and internal gateway runners.",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    # -------------------------
    # Production console
    # -------------------------
    p_console = sub.add_parser("console", help="Interactive production console (REPL) calling FrontDoor.")
    p_console.add_argument("--role", default="GUEST", choices=["OWNER", "GUEST"], help="Starting role for the UI.")
    p_console.add_argument("--offline", action="store_true", help="Start with offline enabled (env SSN_OFFLINE=1 always wins).")
    p_console.add_argument("--strict", action="store_true", help="Start with strict enabled in FrontDoor context.")

    # -------------------------
    # Existing commands (kept)
    # -------------------------
    p_chat = sub.add_parser("chat", help="One-shot internal chat via runtime shell (legacy).")
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

    p_tick = sub.add_parser("sense-tick", help="Run one bounded perception tick (updates WorldModel).")
    p_tick.add_argument("--role", default="OWNER", choices=["OWNER", "GUEST"])
    p_tick.add_argument("--events", default="[]", help="JSON list of event dicts.")
    p_tick.add_argument("--max_events", type=int, default=25)

    p_tool = sub.add_parser("run-tool", help="Run a registered tool through InterfaceGateway (recommended).")
    p_tool.add_argument("--role", default="OWNER", choices=["OWNER", "GUEST"])
    p_tool.add_argument("--name", required=True, help="Tool name, e.g., tools.list, tools.public_list, world.read")
    p_tool.add_argument("--args", default="{}", help='JSON dict of tool args, e.g. \'{"max_events":2}\'')

    args = parser.parse_args(remaining)

    # =========================================================
    # Canonical runtime build (same path as production smoke)
    # =========================================================
    runtime = SSNRuntimeBuilder.build_default(default_role="GUEST", output_mode="full")

    # Ensure canonical ToolRegistry visible to gateway handlers (no split-brain)
    try:
        deps = getattr(runtime.gateway, "deps", None) or {}
        orch = deps.get("orchestrator")
        if orch is not None and getattr(orch, "tools", None) is not None:
            runtime.gateway.deps["tool_registry"] = orch.tools
    except Exception:
        pass

    # -------------------------
    # Production FrontDoor REPL
    # -------------------------
    if args.cmd == "console":
        return _run_console(
            runtime=runtime,
            master_key=mk,
            role_default=args.role,
            offline_default=bool(args.offline),
            strict_default=bool(args.strict),
        )

    # -------------------------
    # Legacy shell-based commands
    # -------------------------
    rt = runtime  # naming consistency with older code

    def mk_meta(extra: dict | None = None, *, role: str = "GUEST") -> dict:
        out = dict(extra or {})
        if mk and role == "OWNER":
            out["master_key"] = mk
        return out

    def mk_context(base: dict | None = None) -> dict:
        return safe_context(base)

    # These assume your runtime has rt.shell with handle_event (kept for compatibility)
    if args.cmd == "chat":
        ctx = mk_context(_parse_json_dict(args.context))
        resp = rt.shell.handle_event(  # type: ignore[attr-defined]
            {"type": "chat", "role": args.role, "text": args.text, "context": ctx, "meta": mk_meta(role=args.role)}
        )
        _print_json(resp.__dict__)
        return 0

    if args.cmd == "state":
        resp = rt.shell.handle_event({"type": "state", "role": args.role, "meta": mk_meta(role=args.role)})  # type: ignore[attr-defined]
        _print_json(resp.__dict__)
        return 0

    if args.cmd == "memory":
        resp = rt.shell.handle_event(  # type: ignore[attr-defined]
            {
                "type": "memory",
                "role": args.role,
                "meta": mk_meta({"trace_limit": args.trace_limit, "episodic_limit": args.episodic_limit}, role=args.role),
            }
        )
        _print_json(resp.__dict__)
        return 0

    if args.cmd == "suggest":
        resp = rt.shell.handle_event(  # type: ignore[attr-defined]
            {"type": "suggest", "role": args.role, "meta": mk_meta({"trace_limit": args.trace_limit}, role=args.role)}
        )
        _print_json(resp.__dict__)
        return 0

    if args.cmd == "world":
        ctx_in = _parse_json_dict(args.context)
        ctx_in["max_entities"] = int(args.max_entities)
        ctx_in["max_events"] = int(args.max_events)
        ctx_in["include_events"] = bool(args.include_events)

        ctx = mk_context(ctx_in)
        resp = rt.shell.handle_event(  # type: ignore[attr-defined]
            {"type": "world", "role": args.role, "text": "", "context": ctx, "meta": mk_meta(role=args.role)}
        )
        _print_json(resp.__dict__)
        return 0

    if args.cmd == "sense-tick":
        evs = _parse_json_list(args.events)
        ctx = mk_context({"events": evs, "max_events": int(args.max_events)})

        resp = rt.shell.handle_event(  # type: ignore[attr-defined]
            {"type": "sense_tick", "role": args.role, "text": "", "context": ctx, "meta": mk_meta(role=args.role)}
        )
        _print_json(resp.__dict__)
        return 0

    # Recommended: run tools through InterfaceGateway directly (matches production)
    if args.cmd == "run-tool":
        tool_args = _parse_json_dict(args.args)
        req = InterfaceRequest(
            action="run_tool",
            role=args.role,
            user_input="",
            context={"tool_name": args.name, "args": mk_context(tool_args)},
            meta={"master_key": mk} if (mk and args.role == "OWNER") else {},
        )
        resp = rt.gateway.handle(req)
        out = {
            "ok": bool(resp.ok),
            "action": resp.action,
            "role": resp.role,
            "data": resp.data,
            "error": (resp.error.__dict__ if resp.error else None),
        }
        _print_json(out)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
