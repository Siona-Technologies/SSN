# ssn/interfaces/handlers_world.py

from __future__ import annotations

from typing import Any, Dict, Optional

from ssn.interfaces.contracts import InterfaceRequest, InterfaceResponse
from ssn.identity.owner_verification import verify_owner, is_samson_verified
from ssn.world.world_context import WorldContextProvider, WorldContextConfig
from ssn.world.world_summary import WorldSummaryNormalizer, WorldSummaryConfig


def _get_master_key(req: InterfaceRequest) -> Optional[str]:
    if isinstance(req.meta, dict):
        mk = req.meta.get("master_key")
        if isinstance(mk, str) and mk.strip():
            return mk.strip()

    ctx = req.context if isinstance(req.context, dict) else {}
    mk2 = ctx.get("master_key")
    if isinstance(mk2, str) and mk2.strip():
        return mk2.strip()

    return None


def handle_world(req: InterfaceRequest, deps: Any) -> InterfaceResponse:
    """
    Phase 5.9 — read-only world state action.

    OWNER-only:
      - verifies using meta["master_key"] (fallback: context["master_key"])
      - returns bounded world_context + world_summary
      - never returns raw sensor payloads
    """
    ctx = req.context or {}
    master_key = _get_master_key(req)

    scores = verify_owner(master_key)
    verified = is_samson_verified(scores)

    if not verified:
        return InterfaceResponse(
            ok=True,
            action="world",
            role=req.role,
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
    world_model = depsd.get("world_model")
    orch = depsd.get("orchestrator")
    if world_model is None and orch is not None:
        world_model = getattr(orch, "world_model", None)

    if world_model is None:
        return InterfaceResponse(
            ok=True,
            action="world",
            role=req.role,
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

    max_entities = int(ctx.get("max_entities", 8) or 8)
    max_events = int(ctx.get("max_events", 8) or 8)
    include_events = bool(ctx.get("include_events", True))

    provider = depsd.get("world_context_provider")
    if provider is None and orch is not None:
        provider = getattr(orch, "world_context_provider", None)

    if provider is None:
        provider = WorldContextProvider(
            WorldContextConfig(
                max_entities=max(1, min(max_entities, 50)),
                max_events=max(0, min(max_events, 50)),
                max_attr_keys=10,
                include_events=include_events,
            )
        )

    world_context = provider.build(world_model)

    summarizer = WorldSummaryNormalizer(
        WorldSummaryConfig(
            max_entities=min(12, max(1, max_entities)),
            max_events=min(12, max(0, max_events)),
            max_attr_keys=4,
            max_chars=700,
        )
    )
    world_summary = summarizer.summarize(world_context)

    return InterfaceResponse(
        ok=True,
        action="world",
        role=req.role,
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
