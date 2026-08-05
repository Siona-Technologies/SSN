# ssn/runtime/runtime_builder.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from ssn.interfaces.gateway import InterfaceGateway
from ssn.interfaces.agent_shell import AgentShell

# Legacy/optional: InterfaceGateway action="tool"
# Real execution path is ToolRegistry via orchestrator.tools (run-tool, research.*, net.*, etc.)
from ssn.interfaces.tool_bus import ToolBus


@dataclass(frozen=True)
class SSNRuntime:
    gateway: InterfaceGateway
    shell: AgentShell
    tool_bus: ToolBus  # legacy/optional; ToolRegistry lives on orchestrator.tools

    orchestrator: Any = None
    brain_router: Any = None
    memory_hub: Any = None
    policy_engine: Any = None
    safety_monitor: Any = None
    suggestion_engine: Any = None
    world_model: Any = None
    world_context_provider: Any = None
    perception_hub: Any = None
    tool_registry: Any = None
    # Phase-1 cognitive foundation (additive; does not replace Orchestrator)
    cognitive_runtime: Any = None
    # Phase-2 integration facade (observation / experimental)
    integration: Any = None

    async def shutdown(self, *, timeout_s: float = 5.0) -> None:
        """Drain/cancel pending observation tasks on teardown."""
        integ = self.integration
        if integ is not None:
            fn = getattr(integ, "shutdown", None)
            if callable(fn):
                await fn(timeout_s=timeout_s)

    def shutdown_sync(self, *, timeout_s: float = 5.0) -> None:
        """
        Sync teardown for callers without a running event loop.
        Inside a running loop, raises — use ``await runtime.shutdown()``.
        """
        import asyncio

        from ssn.integration.event_bridge import EventBridgeShutdownInAsyncContextError

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None and loop.is_running():
            raise EventBridgeShutdownInAsyncContextError(
                "shutdown_sync() cannot be called inside a running event loop; "
                "use await runtime.shutdown()"
            )
        asyncio.run(self.shutdown(timeout_s=timeout_s))


class _DummyPerceptionHub:
    """
    Deterministic fallback so sense_tick always works (tests / minimal installs).
    """

    def tick(self, world_model: Any = None, events: Any = None) -> Dict[str, Any]:
        import time

        ts = time.time()
        pkt = {
            "type": "world_update",
            "ts": ts,
            "source": "sense_tick",
            "entities": [
                {
                    "id": "person:synthetic",
                    "entity": "person",
                    "status": "present",
                    "confidence": 0.7,
                    "attributes": {"zone": "front"},
                }
            ],
            "events": [
                {"type": "vision_detection", "ts": ts, "confidence": 0.7},
                {"type": "motion_event", "ts": ts, "confidence": 0.6},
            ],
        }

        if world_model is not None:
            fn = getattr(world_model, "apply_update", None) or getattr(world_model, "update", None)
            if callable(fn):
                try:
                    fn(pkt)
                except Exception:
                    pass

        return {
            "ok": True,
            "processed": 2,
            "skipped": 0,
            "world_updated": True,
            "trace_written": False,
            "ts": ts,
            "world_update": pkt,
        }


def _safe_setattr(obj: Any, name: str, value: Any) -> None:
    """
    Attach attributes without overriding existing ones.
    Prevents accidentally replacing orchestrator-owned wiring.
    """
    if obj is None:
        return
    try:
        if getattr(obj, name, None) is None:
            setattr(obj, name, value)
    except Exception:
        return


def _try_load_world_model() -> Any:
    try:
        from ssn.world.world_model import WorldModel  # type: ignore

        return WorldModel()
    except Exception:
        return None


def _try_import_create_siona():
    """
    Try bootstrap module locations and return create_siona if found.
    Preferred is ssn.bootstrap.
    """
    candidates = (
        "ssn.bootstrap",  # preferred
        "ssn.boot",
        "ssn.core.bootstrap",
        "ssn.bootstrap_siona",
        "ssn.siona_bootstrap",
    )
    for mod in candidates:
        try:
            m = __import__(mod, fromlist=["create_siona"])
            fn = getattr(m, "create_siona", None)
            if callable(fn):
                return fn
        except Exception:
            continue
    return None


def _build_orchestrator_via_bootstrap(*, output_mode: str, world_model: Any = None) -> Any:
    """
    Preferred: construct orchestrator through canonical bootstrap path.
    Fallback: minimal orchestrator + builtin tools (best-effort but deterministic).
    """
    create_siona = _try_import_create_siona()
    if callable(create_siona):
        return create_siona(output_mode=output_mode, world_model=world_model)

    # Fallback (rare): still produce a usable orchestrator instance.
    from ssn.core.orchestrator import Orchestrator  # type: ignore

    orch = Orchestrator(output_mode=output_mode, world_model=world_model)

    # Best-effort: register builtin tools if ToolRegistry exists
    try:
        tools = getattr(orch, "tools", None) or getattr(orch, "tool_registry", None)
        if tools is not None:
            from ssn.tools.builtin_tools import register_builtin_tools  # type: ignore

            register_builtin_tools(tools)
    except Exception:
        pass

    return orch


class SSNRuntimeBuilder:
    """
    Builds an SSNRuntime wrapper around the canonical Orchestrator instance.

    Hard rules:
      - Orchestrator is the single authority for memory/policy/router/tools.
      - Do not instantiate parallel MemoryHub / ToolRegistry here.
    """

    def __init__(
        self,
        *,
        orchestrator: Any = None,
        brain_router: Any = None,
        memory_hub: Any = None,
        policy_engine: Any = None,
        safety_monitor: Any = None,
        suggestion_engine: Any = None,
        world_model: Any = None,
        world_context_provider: Any = None,
        perception_hub: Any = None,
        tool_registry: Any = None,
        default_role: str = "GUEST",
        output_mode: str = "full",
    ):
        self.orchestrator = orchestrator
        self.brain_router = brain_router
        self.memory_hub = memory_hub
        self.policy_engine = policy_engine
        self.safety_monitor = safety_monitor
        self.suggestion_engine = suggestion_engine
        self.world_model = world_model
        self.world_context_provider = world_context_provider
        self.perception_hub = perception_hub
        self.tool_registry = tool_registry
        self.default_role = default_role if default_role in ("OWNER", "GUEST") else "GUEST"
        self.output_mode = output_mode if output_mode in ("full", "minimal") else "full"

    @classmethod
    def build_default(cls, *, default_role: str = "GUEST", output_mode: str = "full") -> SSNRuntime:
        world_model = _try_load_world_model()
        orch = _build_orchestrator_via_bootstrap(output_mode=output_mode, world_model=world_model)
        return cls(
            orchestrator=orch,
            world_model=world_model,
            default_role=default_role,
            output_mode=output_mode,
        ).build()

    def _pull_from_orchestrator(self) -> None:
        orch = self.orchestrator
        if orch is None:
            return

        # Tool registry is canonical on orch.tools
        self.tool_registry = self.tool_registry or getattr(orch, "tools", None) or getattr(orch, "tool_registry", None)

        # Memory hub: orch may expose memory_hub or memory
        self.memory_hub = self.memory_hub or getattr(orch, "memory_hub", None) or getattr(orch, "memory", None)

        # Policy engine: orch may expose policy_engine or policy
        self.policy_engine = self.policy_engine or getattr(orch, "policy_engine", None) or getattr(orch, "policy", None)

        # Brain router: orch may expose brain_router or router
        self.brain_router = self.brain_router or getattr(orch, "brain_router", None) or getattr(orch, "router", None)

        # Prefer orchestrator's world_model if it already has one
        orch_wm = getattr(orch, "world_model", None)
        if orch_wm is not None:
            self.world_model = orch_wm
        else:
            self.world_model = self.world_model or _try_load_world_model()

        self.world_context_provider = self.world_context_provider or getattr(orch, "world_context_provider", None)

        # Safety monitor usually hangs off policy
        if self.safety_monitor is None and self.policy_engine is not None:
            self.safety_monitor = getattr(self.policy_engine, "safety_monitor", None)

        # Suggestion engine (optional)
        if self.suggestion_engine is None:
            self.suggestion_engine = getattr(orch, "suggestion_engine", None)
        if self.suggestion_engine is None:
            try:
                from ssn.core.suggestion_engine import SuggestionEngine  # type: ignore

                self.suggestion_engine = SuggestionEngine(
                    memory_hub=self.memory_hub,
                    safety_monitor=self.safety_monitor,
                )
            except Exception:
                self.suggestion_engine = None

        # Compatibility aliases back onto orchestrator (ONLY if missing)
        _safe_setattr(orch, "tool_registry", self.tool_registry)
        _safe_setattr(orch, "memory_hub", self.memory_hub)
        _safe_setattr(orch, "memory", self.memory_hub)
        _safe_setattr(orch, "policy_engine", self.policy_engine)
        _safe_setattr(orch, "policy", self.policy_engine)
        _safe_setattr(orch, "brain_router", self.brain_router)
        _safe_setattr(orch, "world_model", self.world_model)
        _safe_setattr(orch, "world_context_provider", self.world_context_provider)
        _safe_setattr(orch, "suggestion_engine", self.suggestion_engine)

    def _build_perception_hub(self) -> Any:
        if self.perception_hub is not None:
            return self.perception_hub

        orch = self.orchestrator
        if orch is not None:
            ph = getattr(orch, "perception_hub", None)
            if ph is not None:
                return ph

        try:
            from ssn.senses.perception_hub import PerceptionHub  # type: ignore

            try:
                return PerceptionHub(world_model=self.world_model, memory_hub=self.memory_hub)
            except TypeError:
                return PerceptionHub()
        except Exception:
            return _DummyPerceptionHub()

    def build(self) -> SSNRuntime:
        if self.orchestrator is None:
            wm = self.world_model if self.world_model is not None else _try_load_world_model()
            self.world_model = wm
            self.orchestrator = _build_orchestrator_via_bootstrap(output_mode=self.output_mode, world_model=wm)

        self._pull_from_orchestrator()

        if self.tool_registry is None:
            raise RuntimeError(
                "ToolRegistry not wired (orchestrator.tools/tool_registry is None). "
                "Bootstrap must construct Orchestrator with a ToolRegistry."
            )

        self.perception_hub = self._build_perception_hub()
        _safe_setattr(self.orchestrator, "perception_hub", self.perception_hub)

        # Legacy tool bus — keep empty/legacy-safe
        tool_bus = ToolBus()

        gateway = InterfaceGateway(
            orchestrator=self.orchestrator,
            brain_router=self.brain_router,
            policy_engine=self.policy_engine,
            safety_monitor=self.safety_monitor,
            memory_hub=self.memory_hub,
            suggestion_engine=self.suggestion_engine,
            tool_bus=tool_bus,
            world_model=self.world_model,
            world_context_provider=self.world_context_provider,
            perception_hub=self.perception_hub,
        )

        # OPTIONAL but useful for later phases: let orchestrator know its canonical interface gateway
        _safe_setattr(self.orchestrator, "interface_gateway", gateway)

        # Ensure deps exists
        deps = getattr(gateway, "deps", None)
        if deps is None:
            try:
                setattr(gateway, "deps", {})
                deps = gateway.deps
            except Exception:
                deps = None

        # CRITICAL: ensure interface handlers share the SAME deps (no split-brain)
        if isinstance(deps, dict):
            deps["orchestrator"] = self.orchestrator

            # Provide gateway aliases so FrontDoor (and future interfaces) can reuse it without manual injection
            deps["gateway"] = gateway
            deps["interface_gateway"] = gateway

            # Tool registry aliases used across handlers/frontdoor
            deps["tool_registry"] = self.tool_registry
            deps["tools"] = self.tool_registry

            # Memory aliases used across tools/handlers
            deps["memory_hub"] = self.memory_hub
            deps["memory"] = self.memory_hub

            # World/perception
            deps["world_model"] = self.world_model
            deps["world_context_provider"] = self.world_context_provider
            deps["perception_hub"] = self.perception_hub

            # Policy/safety/suggestions
            deps["policy_engine"] = self.policy_engine
            deps["policy"] = self.policy_engine
            deps["safety_monitor"] = self.safety_monitor
            deps["suggestion_engine"] = self.suggestion_engine

            # OFFLINE propagation (single source of truth for tools)
            # - env SSN_OFFLINE=1 still works
            # - FrontDoor/CLI can set deps["offline"]=True and tools will honor it
            deps.setdefault("offline", False)

        # Additive cognitive foundation (event bus / workspace / gateways).
        # Does not replace Orchestrator, BrainRouter, policy, or owner-control paths.
        cognitive_runtime = None
        integration = None
        try:
            from ssn.cognition.loop import CognitiveRuntime  # type: ignore
            from ssn.cognition.model_gateway import ModelGateway  # type: ignore
            from ssn.integration.facade import IntegrationFacade  # type: ignore
            from ssn.integration.runtime_modes import get_runtime_mode  # type: ignore

            # Reuse a single model gateway instance for the cognitive path.
            shared_gateway = ModelGateway.for_tests()
            cognitive_runtime = CognitiveRuntime.create(
                memory_hub=self.memory_hub,
                world_model=self.world_model,
                model_gateway=shared_gateway,
            )
            # Ensure memory/world boundaries point at orchestrator-owned backends.
            cognitive_runtime.memory._hub = self.memory_hub
            cognitive_runtime.world._world = self.world_model

            integration = IntegrationFacade.create(
                cognitive_runtime=cognitive_runtime,
                orchestrator=self.orchestrator,
                mode=get_runtime_mode().value,
            )
            _safe_setattr(self.orchestrator, "cognitive_runtime", cognitive_runtime)
            _safe_setattr(self.orchestrator, "integration", integration)

            # Canonical routing.selected is emitted once from
            # IntegrationFacade.observe_authoritative_chat (same Front Door TraceContext).
            # Do not attach BrainRouter.integration_observer — that duplicated events
            # with a fresh unrelated trace_id.

            if isinstance(deps, dict):
                deps["cognitive_runtime"] = cognitive_runtime
                deps["integration"] = integration
                deps["cognitive_mode"] = integration.mode.value
                deps["model_gateway"] = shared_gateway
        except Exception:
            cognitive_runtime = None
            integration = None

        shell = AgentShell(gateway=gateway, default_role=self.default_role)

        return SSNRuntime(
            gateway=gateway,
            shell=shell,
            tool_bus=tool_bus,
            orchestrator=self.orchestrator,
            brain_router=self.brain_router,
            memory_hub=self.memory_hub,
            policy_engine=self.policy_engine,
            safety_monitor=self.safety_monitor,
            suggestion_engine=self.suggestion_engine,
            world_model=self.world_model,
            world_context_provider=self.world_context_provider,
            perception_hub=self.perception_hub,
            tool_registry=self.tool_registry,
            cognitive_runtime=cognitive_runtime,
            integration=integration,
        )
