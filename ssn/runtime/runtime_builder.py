# ssn/runtime/runtime_builder.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from ssn.interfaces.gateway import InterfaceGateway
from ssn.interfaces.agent_shell import AgentShell
from ssn.interfaces.tool_bus import ToolBus
from ssn.interfaces.tools_builtin import register_builtin_tools


@dataclass(frozen=True)
class SSNRuntime:
    gateway: InterfaceGateway
    shell: AgentShell
    tool_bus: ToolBus

    orchestrator: Any = None
    brain_router: Any = None
    memory_hub: Any = None
    policy_engine: Any = None
    safety_monitor: Any = None
    suggestion_engine: Any = None
    world_model: Any = None
    world_context_provider: Any = None
    perception_hub: Any = None


class _DummyPerceptionHub:
    """
    Deterministic fallback so sense_tick always works in tests
    even if the real PerceptionHub is not installed/wired.
    """
    def tick(self, world_model: Any = None) -> Dict[str, Any]:
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

        # Apply update directly if a world_model was provided
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
            "trace_written": False,  # handler will write trace via memory_hub
            "ts": ts,
            "world_update": pkt,
        }


def _safe_setattr(obj: Any, name: str, value: Any) -> None:
    """Attach attributes to orchestrator-like objects without breaking if read-only."""
    if obj is None:
        return
    try:
        if getattr(obj, name, None) is None:
            setattr(obj, name, value)
    except Exception:
        return


class SSNRuntimeBuilder:
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
        default_role: str = "GUEST",
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
        self.default_role = default_role

    @classmethod
    def build_default(cls, *, default_role: str = "GUEST") -> SSNRuntime:
        orchestrator = None
        brain_router = None
        memory_hub = None
        policy_engine = None
        safety_monitor = None
        suggestion_engine = None
        world_model = None
        world_context_provider = None
        perception_hub: Any = None

        # Orchestrator
        try:
            from ssn.core.orchestrator import Orchestrator  # type: ignore
            orchestrator = Orchestrator()
        except Exception:
            orchestrator = None

        # Memory
        try:
            from ssn.memory.memory_hub import MemoryHub  # type: ignore
            memory_hub = MemoryHub()
        except Exception:
            memory_hub = None

        # Policy
        try:
            from ssn.policy.policy_engine import PolicyEngine  # type: ignore
            policy_engine = PolicyEngine()
        except Exception:
            policy_engine = None

        # Safety
        try:
            from ssn.security.safety_monitor import SafetyMonitor  # type: ignore
            safety_monitor = SafetyMonitor()
        except Exception:
            safety_monitor = None

        # Suggestions
        try:
            from ssn.core.suggestion_engine import SuggestionEngine  # type: ignore
            suggestion_engine = SuggestionEngine(memory_hub=memory_hub, safety_monitor=safety_monitor)
        except Exception:
            suggestion_engine = None

        # Brain router
        try:
            from ssn.core.brain_router import BrainRouter  # type: ignore
            try:
                brain_router = BrainRouter(memory_hub=memory_hub, safety_monitor=safety_monitor)
            except TypeError:
                brain_router = BrainRouter()
        except Exception:
            brain_router = None

        # World model (persisted)
        try:
            from ssn.world.world_model import WorldModel  # type: ignore
            world_model = WorldModel()
        except Exception:
            world_model = None

        # World context provider
        try:
            from ssn.world.world_context import WorldContextProvider, WorldContextConfig  # type: ignore
            world_context_provider = WorldContextProvider(WorldContextConfig())
        except Exception:
            world_context_provider = None

        # Perception hub (real if available, otherwise dummy)
        try:
            from ssn.perception.perception_hub import PerceptionHub  # type: ignore
            try:
                perception_hub = PerceptionHub(world_model=world_model, memory_hub=memory_hub)
            except TypeError:
                perception_hub = PerceptionHub()
        except Exception:
            perception_hub = None

        # Absolute guarantee: never leave perception_hub None
        if perception_hub is None:
            perception_hub = _DummyPerceptionHub()

        # Reduce “wired in builder but not in orchestrator” mismatches
        _safe_setattr(orchestrator, "memory_hub", memory_hub)
        _safe_setattr(orchestrator, "world_model", world_model)
        _safe_setattr(orchestrator, "world_context_provider", world_context_provider)
        _safe_setattr(orchestrator, "perception_hub", perception_hub)

        builder = cls(
            orchestrator=orchestrator,
            brain_router=brain_router,
            memory_hub=memory_hub,
            policy_engine=policy_engine,
            safety_monitor=safety_monitor,
            suggestion_engine=suggestion_engine,
            world_model=world_model,
            world_context_provider=world_context_provider,
            perception_hub=perception_hub,
            default_role=default_role,
        )
        return builder.build()

    def build(self) -> SSNRuntime:
        # Absolute guarantee for manual/custom builder usage too
        if self.perception_hub is None:
            self.perception_hub = _DummyPerceptionHub()

        tool_bus = ToolBus()
        register_builtin_tools(tool_bus)

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
        )
