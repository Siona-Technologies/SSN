# ssn/tools/identity_tools.py

from __future__ import annotations

from typing import Any, Dict, List

from ssn.identity.identity_profile import IdentityProfileStore, verify_profile


def identity_view_tool(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool: identity.view
    Read-only. Returns profile + signature_valid (if master_key provided).
    """
    store = IdentityProfileStore()
    out = store.view()
    if not out.get("available"):
        return out

    prof = out.get("profile", {})
    mk = args.get("master_key", "")
    sig_ok = False
    if isinstance(prof, dict) and isinstance(mk, str) and mk.strip():
        try:
            sig_ok = bool(verify_profile(prof, mk.strip()))
        except Exception:
            sig_ok = False

    return {
        "available": True,
        "path": out.get("path"),
        "signature_valid": sig_ok,
        "profile": prof,
    }


def identity_enroll_tool(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool: identity.enroll
    State-changing. Creates/overwrites identity profile.
    Requires master_key.
    """
    mk = args.get("master_key", "")
    if not isinstance(mk, str) or not mk.strip():
        return {"ok": False, "code": "MASTER_KEY_MISSING", "message": "master_key is required for enrollment."}

    owner_name = args.get("owner_name") or "Samson Sibona Njaji"
    creator_name = args.get("creator_name") or "Samson Sibona Njaji"
    system_name = args.get("system_name") or "SSN"
    mission = args.get("mission") or "Owner-bound hybrid human-like brain system."

    laws = args.get("laws")
    if not isinstance(laws, list) or not laws:
        laws = [
            "SSN is bound to Samson Sibona Njaji as owner and creator.",
            "SSN must verify OWNER identity before executing privileged actions.",
            "SSN must not leak secrets (master keys, credentials, private memory) to unverified roles.",
            "SSN must keep outputs bounded, deterministic where required, and policy/safety constrained.",
            "SSN must log privileged actions to trace memory where applicable.",
        ]

    # sanitize laws
    safe_laws: List[str] = [str(x) for x in laws]

    force = bool(args.get("force", False))

    store = IdentityProfileStore()
    return store.enroll(
        master_key=mk.strip(),
        owner_name=str(owner_name),
        creator_name=str(creator_name),
        system_name=str(system_name),
        mission=str(mission),
        laws=safe_laws,
        force=force,
    )
