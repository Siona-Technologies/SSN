# scripts/smoke_net_pipeline.py
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from typing import Any, Dict, Optional

from ssn.bootstrap import create_siona
from ssn.memory import proposal_store  # canonical persistence paths


def _env_flag(name: str) -> str:
    v = os.getenv(name)
    return v if v is not None else "None"


def _bool_env(name: str) -> bool:
    return os.getenv(name) == "1"


def _print_env() -> None:
    print("\n=== ENV ===")
    print("SSN_OFFLINE:", _env_flag("SSN_OFFLINE"))
    print("SSN_LIVE_SEARCH:", _env_flag("SSN_LIVE_SEARCH"))
    print("SSN_LIVE_STRICT:", _env_flag("SSN_LIVE_STRICT"))
    print("SSN_STATE_DIR:", _env_flag("SSN_STATE_DIR"))
    print("SSN_RATE_LIMIT_PATH:", _env_flag("SSN_RATE_LIMIT_PATH"))
    print("SSN_BRAVE_API_KEY:", "set" if os.getenv("SSN_BRAVE_API_KEY") else "not-set")
    print("SSN_BRAVE_COUNTRY:", _env_flag("SSN_BRAVE_COUNTRY"))
    print("SSN_BRAVE_LANG:", _env_flag("SSN_BRAVE_LANG"))

    if not os.getenv("SSN_STATE_DIR"):
        print("\n[WARN] SSN_STATE_DIR is not set.")
        print("       State will persist under proposal_store default state_dir.")
        print("       For CI/Codespaces, prefer a repo-local dir, e.g.:")
        print("         export SSN_STATE_DIR=$(pwd)/.ssn_state")


def _print_store_paths() -> None:
    state_dir = proposal_store.get_state_dir()
    pending_path = os.path.join(state_dir, "pending_memory_proposals.json")
    history_path = os.path.join(state_dir, "memory_proposal_history.json")

    print("\n=== PERSISTENCE PATHS (CANONICAL) ===")
    print("state_dir:", state_dir)
    print("pending_path:", pending_path)
    print("history_path:", history_path)


def _run_tool(
    orch: Any,
    *,
    name: str,
    role: str,
    deps: Dict[str, Any],
    args: Dict[str, Any],
) -> Any:
    return orch.tools.run(name=name, role=role, deps=deps, args=args)


def _spawn_child(mode: str, *, pid: Optional[str] = None, query: Optional[str] = None) -> subprocess.CompletedProcess:
    """
    Spawn a fresh Python process to validate cross-process persistence.
    Inherits environment variables (SSN_STATE_DIR, SSN_LIVE_SEARCH, keys).
    """
    argv = [sys.executable, "-m", "scripts.smoke_net_pipeline", "--child", mode]
    if pid:
        argv += ["--pid", pid]
    if query:
        argv += ["--query", query]
    return subprocess.run(argv, capture_output=True, text=True, env=os.environ.copy())


# ----------------------------
# Mode resolution (production-safe)
# ----------------------------

def _effective_modes(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Resolve operational mode deterministically and safely.
    """
    forced_offline = _bool_env("SSN_OFFLINE")

    # live
    if args.live is not None:
        live = bool(args.live) and not forced_offline
    else:
        live = _bool_env("SSN_LIVE_SEARCH") and not forced_offline

    # strict
    if args.strict is not None:
        strict = bool(args.strict) and not forced_offline
    else:
        strict = _bool_env("SSN_LIVE_STRICT") and not forced_offline

    # Phase 7.3 hygiene: allow degraded proposals ONLY in forced offline mode.
    allow_degraded_for_propose = True if forced_offline else False

    return {
        "forced_offline": forced_offline,
        "live": live,
        "strict": strict,
        "allow_degraded_for_propose": allow_degraded_for_propose,
    }


# ----------------------------
# Child-mode implementations
# ----------------------------

def _child_propose(query: str) -> int:
    """
    Child-mode: create proposal, print proposal_id ONLY to stdout.
    """
    orch = create_siona()
    deps = {"role": "OWNER", "tools": orch.tools, "memory": getattr(orch, "memory", None)}

    forced_offline = _bool_env("SSN_OFFLINE")
    live = _bool_env("SSN_LIVE_SEARCH") and not forced_offline
    strict = _bool_env("SSN_LIVE_STRICT") and not forced_offline

    # Allow degraded ONLY in forced offline mode (deterministic CI).
    allow_degraded = True if forced_offline else False

    rp = _run_tool(
        orch,
        name="research.propose",
        role="OWNER",
        deps=deps,
        args={
            "query": query,
            "top_k": 2,
            "live_search": bool(live),
            "strict_live": bool(strict),
            "allow_degraded": bool(allow_degraded),

            # IMPORTANT FIX:
            # Do NOT force disambiguation here. It can turn normal queries (e.g., Python)
            # into SIONA/SSN-specific queries and trigger degraded/mock selection logic.
            # "disambiguate": True,
        },
    )

    if not rp.ok:
        err = rp.error if rp.error is not None else {"code": "UNKNOWN", "message": "research.propose failed"}
        print(f"child_propose_error={err}", file=sys.stderr)
        return 20

    pid = (rp.data or {}).get("proposal_id")
    if not isinstance(pid, str) or not pid.strip():
        print("child_propose_error=missing_proposal_id", file=sys.stderr)
        return 21

    print(pid.strip())
    return 0


def _child_commit(pid: str) -> int:
    """
    Child-mode: commit proposal_id and print status ONLY to stdout.
    """
    orch = create_siona()
    deps = {"role": "OWNER", "tools": orch.tools, "memory": getattr(orch, "memory", None)}

    mc = _run_tool(
        orch,
        name="memory.commit",
        role="OWNER",
        deps=deps,
        args={"proposal_id": pid, "approve": True},
    )
    if not mc.ok:
        err = mc.error if mc.error is not None else {"code": "UNKNOWN", "message": "memory.commit failed"}
        print(f"child_commit_error={err}", file=sys.stderr)
        return 30

    status = (mc.data or {}).get("status")
    print(str(status or "").strip())
    return 0


def _child_idempotent(pid: str) -> int:
    """
    Child-mode: commit again; should succeed via history (idempotent).
    """
    orch = create_siona()
    deps = {"role": "OWNER", "tools": orch.tools, "memory": getattr(orch, "memory", None)}

    mc2 = _run_tool(
        orch,
        name="memory.commit",
        role="OWNER",
        deps=deps,
        args={"proposal_id": pid, "approve": True},
    )
    if not mc2.ok:
        err = mc2.error if mc2.error is not None else {"code": "UNKNOWN", "message": "memory.commit(idempotent) failed"}
        print(f"child_idempotent_error={err}", file=sys.stderr)
        return 40

    status = (mc2.data or {}).get("status")
    print(str(status or "").strip())
    return 0


# ----------------------------
# Main smoke pipeline
# ----------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="SSN smoke pipeline (net + research + memory; offline-safe; live optional)"
    )
    parser.add_argument("--child", choices=["propose", "commit", "idempotent"], help="internal child mode", default=None)
    parser.add_argument("--pid", type=str, help="proposal_id for child commit/idempotent", default=None)
    parser.add_argument("--query", type=str, help="query for net.search/research.*", default="Example Domain")

    # fetch-url is an OPTIONAL override. If omitted, fetch top1 from net.search.
    parser.add_argument("--fetch-url", type=str, help="Optional override URL for fetch/sanitize/cite", default=None)

    # Optional explicit overrides (otherwise env decides)
    parser.add_argument("--live", action="store_true", help="Force live search on (ignored if SSN_OFFLINE=1)")
    parser.add_argument("--no-live", dest="live", action="store_false", help="Force live search off")
    parser.set_defaults(live=None)

    parser.add_argument("--strict", action="store_true", help="Force strict live on (ignored if SSN_OFFLINE=1)")
    parser.add_argument("--no-strict", dest="strict", action="store_false", help="Force strict live off")
    parser.set_defaults(strict=None)

    args = parser.parse_args()

    # Child-mode dispatcher
    if args.child:
        if args.child == "propose":
            return _child_propose(args.query)
        if args.child == "commit":
            if not args.pid:
                print("child_commit_error=missing_pid", file=sys.stderr)
                return 31
            return _child_commit(args.pid)
        if args.child == "idempotent":
            if not args.pid:
                print("child_idempotent_error=missing_pid", file=sys.stderr)
                return 41
            return _child_idempotent(args.pid)
        print(f"child_error=unknown_mode:{args.child}", file=sys.stderr)
        return 99

    started = time.time()
    _print_env()
    _print_store_paths()

    modes = _effective_modes(args)
    print("\n=== EFFECTIVE MODE ===")
    print("forced_offline:", modes["forced_offline"])
    print("live:", modes["live"])
    print("strict:", modes["strict"])
    print("allow_degraded_for_propose:", modes["allow_degraded_for_propose"])

    orch = create_siona()
    deps = {"role": "OWNER", "tools": orch.tools, "memory": getattr(orch, "memory", None)}

    # ----------------------------------------
    # 0) net.search
    # ----------------------------------------
    print("\n=== 0) net.search ===")
    ns_args: Dict[str, Any] = {
        "query": args.query,
        "top_k": 5,
        "debug": True,
        "timeout_s": 10,
        "live": bool(modes["live"]),
        "strict": bool(modes["strict"]),
    }

    ns = _run_tool(
        orch,
        name="net.search",
        role="OWNER",
        deps=deps,
        args=ns_args,
    )
    print("ok:", ns.ok)
    if not ns.ok:
        print("err:", ns.error)
        return 1

    d = ns.data or {}
    print("provider:", d.get("provider"))
    print("degraded:", d.get("degraded", False))
    print("providers_tried:", d.get("providers_tried"))
    if d.get("provider_debug"):
        print("provider_debug:", d.get("provider_debug"))
    print("result_count:", d.get("result_count"))

    results = d.get("results") or []
    top1_url: Optional[str] = None
    if results:
        r0 = results[0] or {}
        print("top1:", r0.get("source"), r0.get("title"), r0.get("url"))
        u = r0.get("url")
        if isinstance(u, str) and u.strip():
            top1_url = u.strip()

    # Decide URL for fetch/sanitize/cite
    if isinstance(args.fetch_url, str) and args.fetch_url.strip():
        selected_url = args.fetch_url.strip()
    elif isinstance(top1_url, str) and top1_url.strip():
        selected_url = top1_url.strip()
    else:
        selected_url = "https://example.com/"  # last resort fallback

    print("fetch_url_selected:", selected_url)

    # ----------------------------------------
    # 1) net.fetch
    # ----------------------------------------
    print("\n=== 1) net.fetch ===")
    fr = _run_tool(
        orch,
        name="net.fetch",
        role="OWNER",
        deps=deps,
        args={"url": selected_url, "max_bytes": 50_000, "timeout_s": 10},
    )
    print("ok:", fr.ok)
    if not fr.ok:
        print("err:", fr.error)
        return 2

    fdat = fr.data or {}
    print("note:", fdat.get("note"))
    print("content_type:", fdat.get("content_type"))
    print("bytes:", fdat.get("content_bytes"))
    print("preview:", (fdat.get("content") or "")[:160])

    # ----------------------------------------
    # 2) net.sanitize
    # ----------------------------------------
    print("\n=== 2) net.sanitize ===")
    sr = _run_tool(
        orch,
        name="net.sanitize",
        role="OWNER",
        deps=deps,
        args={
            "url": fdat.get("url") or selected_url,
            "content_type": fdat.get("content_type") or "text/html",
            "content": fdat.get("content") or "",
            "max_bytes": 50_000,
        },
    )
    print("ok:", sr.ok)
    if not sr.ok:
        print("err:", sr.error)
        return 3

    sdat = sr.data or {}
    print("note:", sdat.get("note"))
    print("clean_bytes:", sdat.get("clean_bytes"))
    print("preview:", (sdat.get("clean_text") or "")[:160])

    # ----------------------------------------
    # 3) net.cite
    # ----------------------------------------
    print("\n=== 3) net.cite ===")
    cr = _run_tool(
        orch,
        name="net.cite",
        role="OWNER",
        deps=deps,
        args={
            "url": fdat.get("url") or selected_url,
            "clean_text": sdat.get("clean_text") or "",
            "title": "SmokeTest Source",
            "snippet": "",
            "retrieved_at": fdat.get("fetched_at", 0),
            "content_type": fdat.get("content_type") or "text/html",
        },
    )
    print("ok:", cr.ok)
    if not cr.ok:
        print("err:", cr.error)
        return 4

    cdat = cr.data or {}
    print("citation_count:", cdat.get("citation_count"))
    print("keys:", sorted(list(cdat.keys())))

    # ----------------------------------------
    # 4) research.answer
    # ----------------------------------------
    print("\n=== 4) research.answer ===")
    ra = _run_tool(
        orch,
        name="research.answer",
        role="OWNER",
        deps=deps,
        args={
            "query": args.query,
            "top_k": 2,
            "live": bool(modes["live"]),
            "strict": bool(modes["strict"]),
        },
    )
    print("ok:", ra.ok)
    if not ra.ok:
        print("err:", ra.error)
        return 5

    rad = ra.data or {}
    print("degraded:", rad.get("degraded"))
    print("answer_preview:", (rad.get("answer") or "")[:200])
    print("sources:", len(rad.get("sources") or []))
    print("citations:", len(rad.get("citations") or []))

    # ----------------------------------------
    # 5/6) CROSS-PROCESS: propose -> commit -> idempotent commit
    # ----------------------------------------
    print("\n=== 5) CROSS-PROCESS memory approval flow ===")

    p = _spawn_child("propose", query=args.query)
    if p.returncode != 0:
        print("child propose failed rc:", p.returncode)
        if p.stdout:
            print("child stdout:", p.stdout.strip())
        if p.stderr:
            print("child stderr:", p.stderr.strip())
        return 6

    pid = (p.stdout or "").strip().splitlines()[-1].strip()
    print("proposal_id:", pid)

    c = _spawn_child("commit", pid=pid)
    if c.returncode != 0:
        print("child commit failed rc:", c.returncode)
        if c.stdout:
            print("child stdout:", c.stdout.strip())
        if c.stderr:
            print("child stderr:", c.stderr.strip())
        return 7
    print("commit_status:", (c.stdout or "").strip())

    i = _spawn_child("idempotent", pid=pid)
    if i.returncode != 0:
        print("child idempotent failed rc:", i.returncode)
        if i.stdout:
            print("child stdout:", i.stdout.strip())
        if i.stderr:
            print("child stderr:", i.stderr.strip())
        return 8
    print("second_commit_status:", (i.stdout or "").strip())

    elapsed_ms = int((time.time() - started) * 1000)
    print("\n=== SUMMARY ===")
    print("PASS: net.search → net.fetch → net.sanitize → net.cite → research.answer → cross-process propose/commit/idempotent")
    print("elapsed_ms:", elapsed_ms)
    return 0


if __name__ == "__main__":
    sys.exit(main())
