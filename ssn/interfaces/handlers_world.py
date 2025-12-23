# ssn/interfaces/handlers_world.py

from __future__ import annotations

from typing import Any, Optional

from ssn.interfaces.contracts import InterfaceRequest, InterfaceResponse
from ssn.identity.owner_verification import verify_owner, is_samson_verified


def _get_master_key(req: InterfaceRequest) -> Optional[str]:
    # Prefer meta first (AgentShell mirrors master_key into meta)
    if isinstance(req.meta, dict):
        mk = req.meta.get("master_key")
        if isinstance(mk, str) and mk.strip():
            return mk.strip()

    # Fallback to context (legacy)
    if isinstance(req.context, dict):
        mk2 = req.context.get("master_key")
        if isinstance(mk2, str) and mk2.strip():
            return mk2.strip()

    return None


def handle_world(req: InterfaceRequest, deps: Any) -> InterfaceResponse:
    """
    Read-only world state action.

    OWNER-only (verified by master key):
      - returns bounded world context + summary
      - respects req.context max_entities/max_events/include_events
    """

    master_key = _get_master_key(req)
    scores = verify_owner(master_key)
    verified = is_samson_verified(scores)

    # Force response role based on verification (do NOT trust req.role)
    resp_role = "OWNER" if verified else "GUEST"

    if not verified:
        return InterfaceResponse(
            ok=True,
            action="world",
            role=resp_role,
            data={
                "identity_verified": False,
                "role": "GUEST",
                "allowed": False,
                "final_result": "BLOCKED_BY_POLICY",
                "scores": scores,
                "world": {"available": False, "reason": "owner_not_verified"},
                "world_summary": "World: unavailable (owner_not_verified).",
            },
            error=None,
        )

    depsd = deps if isinstance(deps, dict) else {}
    orch = depsd.get("orchestrator")

    world_model = depsd.get("world_model") or (getattr(orch, "world_model", None) if orch else None)
    if world_model is None:
        return InterfaceResponse(
            ok=True,
            action="world",
            role=resp_role,
            data={
                "identity_verified": True,
                "role": "OWNER",
                "allowed": True,
                "scores": scores,
                "world": {"available": False, "reason": "world_model_not_configured"},
                "world_summary": "World: unavailable (world_model_not_configured).",
            },
            error=None,
        )

    ctx = req.context if isinstance(req.context, dict) else {}
    max_entities = int(ctx.get("max_entities", 8) or 8)
    max_events = int(ctx.get("max_events", 8) or 8)
    include_events = bool(ctx.get("include_events", True))

    # Hard bounds (production safety)
    max_entities = max(1, min(max_entities, 50))
    max_events = max(0, min(max_events, 50))

    # Lazy imports to avoid import-time bricking
    try:
        from ssn.world.world_context import WorldContextProvider, WorldContextConfig  # type: ignore
        from ssn.world.world_summary import WorldSummaryNormalizer, WorldSummaryConfig  # type: ignore
    except Exception:
        return InterfaceResponse(
            ok=True,
            action="world",
            role=resp_role,
            data={
                "identity_verified": True,
                "role": "OWNER",
                "allowed": True,
                "scores": scores,
                "world": {"available": False, "reason": "world_modules_missing"},
                "world_summary": "World: unavailable (world_modules_missing).",
            },
            error=None,
        )

    provider = WorldContextProvider(
        WorldContextConfig(
            max_entities=max_entities,
            max_events=max_events,
            max_attr_keys=10,
            include_events=include_events,
        )
    )

    # Build world context with safe signature fallback
    try:
        world_context = provider.build(
            world_model,
            include_events=include_events,
            max_entities=max_entities,
            max_events=max_events,
        )
    except TypeError:
        # Older provider signature
        world_context = provider.build(world_model)

    summarizer = WorldSummaryNormalizer(
        WorldSummaryConfig(
            max_entities=max_entities,
            max_events=max_events,
            max_attr_keys=4,
            max_chars=700,
        )
    )
    try:
        world_summary = summarizer.summarize(world_context)
    except Exception:
        world_summary = "World: summary unavailable (summarize_failed)."

    return InterfaceResponse(
        ok=True,
        action="world",
        role=resp_role,
        data={
            "identity_verified": True,
            "role": "OWNER",
            "allowed": True,
            "scores": scores,
            "world": world_context,
            "world_summary": world_summary,
        },
        error=None,
    )
