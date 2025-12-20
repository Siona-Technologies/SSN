# manual_live_check.py
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, Optional, Tuple

from ssn.bootstrap import create_siona


def _as_tool_fields(r: Any) -> Tuple[Optional[bool], str, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Normalize ToolResult-like objects and dict responses.

    Returns: (ok, tool_name, data, error)
    """
    ok = getattr(r, "ok", None)
    tool = getattr(r, "tool", None)
    data = getattr(r, "data", None)
    error = getattr(r, "error", None)

    if isinstance(ok, bool) and isinstance(tool, str):
        if not isinstance(data, dict) and data is not None:
            data = {"_data": data}
        if not isinstance(error, dict) and error is not None:
            error = {"_error": error}
        return ok, tool, data if isinstance(data, dict) else None, error if isinstance(error, dict) else None

    if isinstance(r, dict):
        if "error" in r and isinstance(r["error"], dict):
            return False, "unknown", None, r["error"]
        return True, "unknown", r, None

    return None, "unknown", None, {"code": "UNKNOWN_RESULT", "message": f"Unexpected result type: {type(r)}"}


def _print_env():
    print("\n=== ENV ===")
    print("SSN_OFFLINE:", os.getenv("SSN_OFFLINE"))
    print("SSN_LIVE_SEARCH:", os.getenv("SSN_LIVE_SEARCH"))
    print("SSN_LIVE_STRICT:", os.getenv("SSN_LIVE_STRICT"))


def _print_result(label: str, r: Any, *, json_mode: bool = False) -> Dict[str, Any]:
    ok, tool, data, error = _as_tool_fields(r)

    print(f"\n=== {label} ===")
    if json_mode:
        payload = {"ok": ok, "tool": tool, "data": data, "error": error}
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"ok: {ok} | tool: {tool}")
        if error:
            print("error:", error)
        if data:
            provider = data.get("provider") if isinstance(data, dict) else None

            degraded = None
            if isinstance(data, dict):
                degraded = data.get("degraded")
                if degraded is None and isinstance(data.get("search"), dict):
                    degraded = data["search"].get("degraded")

            if provider is not None:
                print("provider:", provider)
            if degraded is not None:
                print("degraded:", degraded)

            preview_keys = ("query", "effective_query", "result_count", "proposal_id")
            preview = {k: data.get(k) for k in preview_keys if isinstance(data.get(k), (str, int, float, bool))}
            if preview:
                print("preview:", preview)

    return {"ok": ok, "tool": tool, "data": data, "error": error}


def main() -> int:
    p = argparse.ArgumentParser(description="SSN research pipeline manual smoke check (developer-only).")
    p.add_argument(
        "--query",
        default='SIONA "Samson Sibona Njaji" SSN hybrid brain orchestrator toolregistry',
        help="Search query to run through net.search -> research.ingest -> research.propose",
    )
    p.add_argument("--top-k", type=int, default=3)
    p.add_argument("--timeout-s", type=int, default=12)
    p.add_argument("--max-bytes", type=int, default=40000)
    p.add_argument("--max-answer-chars", type=int, default=800)
    p.add_argument("--max-facts", type=int, default=5)
    p.add_argument("--fact-len", type=int, default=180)

    p.add_argument("--json", action="store_true")
    p.add_argument("--fail-fast", action="store_true")

    # Tri-state flags: default None means "use env"
    live_group = p.add_mutually_exclusive_group()
    live_group.add_argument("--live", dest="live", action="store_true", help="Force live search ON")
    live_group.add_argument("--no-live", dest="live", action="store_false", help="Force live search OFF")
    p.set_defaults(live=None)

    strict_group = p.add_mutually_exclusive_group()
    strict_group.add_argument("--strict-live", dest="strict_live", action="store_true", help="Force strict live ON")
    strict_group.add_argument("--no-strict-live", dest="strict_live", action="store_false", help="Force strict live OFF")
    p.set_defaults(strict_live=None)

    # Degraded policy override
    p.add_argument("--allow-degraded", action="store_true", help="Allow proposals even if search degrades to mock")

    args = p.parse_args()

    siona = create_siona()
    deps = {"tools": siona.tools, "role": "OWNER", "memory": siona.memory}

    _print_env()

    forced_offline = os.getenv("SSN_OFFLINE") == "1"
    env_live = os.getenv("SSN_LIVE_SEARCH") == "1"
    env_strict = os.getenv("SSN_LIVE_STRICT") == "1"

    effective_live = env_live if args.live is None else bool(args.live)
    effective_strict = env_strict if args.strict_live is None else bool(args.strict_live)

    if forced_offline:
        effective_live = False
        effective_strict = False

    # Default for dev smoke: allow degraded unless strict is ON
    allow_degraded = bool(args.allow_degraded) if effective_strict else True

    # 1) net.search
    r1 = siona.tools.run(
        name="net.search",
        role="OWNER",
        deps=deps,
        args={
            "query": args.query,
            "top_k": int(args.top_k),
            "live": bool(effective_live),
            "strict": bool(effective_strict),
            "timeout_s": int(args.timeout_s),
        },
    )
    s1 = _print_result("1) net.search", r1, json_mode=args.json)
    if s1["ok"] is not True:
        return 10

    # 2) research.ingest
    r2 = siona.tools.run(
        name="research.ingest",
        role="OWNER",
        deps=deps,
        args={
            "query": args.query,
            "top_k": int(args.top_k),
            "max_bytes": int(args.max_bytes),
            "max_answer_chars": int(args.max_answer_chars),
            "live_search": bool(effective_live),
            "strict_live": bool(effective_strict),
            "timeout_s": int(args.timeout_s),
        },
    )
    s2 = _print_result("2) research.ingest", r2, json_mode=args.json)
    if s2["ok"] is not True:
        return 20 if args.fail_fast else 20

    # 3) research.propose (dev mode)
    r3 = siona.tools.run(
        name="research.propose",
        role="OWNER",
        deps=deps,
        args={
            "query": args.query,
            "top_k": int(args.top_k),
            "max_bytes": int(args.max_bytes),
            "max_answer_chars": int(args.max_answer_chars),
            "max_facts": int(args.max_facts),
            "fact_len": int(args.fact_len),
            "live_search": bool(effective_live),
            "strict_live": False,
            "allow_degraded": bool(allow_degraded),
            "timeout_s": int(args.timeout_s),
        },
    )
    s3 = _print_result("3) research.propose (dev mode)", r3, json_mode=args.json)
    if s3["ok"] is not True:
        return 30 if args.fail_fast else 30

    # 4) research.propose (strict live)
    r4 = siona.tools.run(
        name="research.propose",
        role="OWNER",
        deps=deps,
        args={
            "query": args.query,
            "top_k": int(args.top_k),
            "max_bytes": int(args.max_bytes),
            "max_answer_chars": int(args.max_answer_chars),
            "max_facts": int(args.max_facts),
            "fact_len": int(args.fact_len),
            "live_search": True,
            "strict_live": True,
            "allow_degraded": False,
            "timeout_s": int(args.timeout_s),
        },
    )
    s4 = _print_result("4) research.propose (strict live)", r4, json_mode=args.json)

    # If strict was requested (via env or CLI), strict propose failing is expected in captcha/blocked environments.
    print("\n=== SUMMARY ===")
    print("effective_live:", effective_live)
    print("effective_strict:", effective_strict)
    print("dev_propose_ok:", s3["ok"])
    print("strict_live_ok:", s4["ok"])
    print("note: strict live may fail if providers block/captcha; that is expected in some environments.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
