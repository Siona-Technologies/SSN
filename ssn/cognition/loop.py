"""
Cognitive loop skeleton.

Coordinates:
  input → (existing identity/policy path) → event publish → workspace
  → memory/world context → model and/or neuromorphic → structured proposals
  → (validation by existing control layers) → observation → response

Does NOT implement unrestricted autonomy.
Does NOT let models execute tools/actuators directly.
Preserves request-response compatibility with LanguageEngine-style replies.
Owner-control / policy semantics are NOT modified here — callers must
continue to use Orchestrator / Front Door for authoritative identity+policy.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ssn.cognition.attention import AttentionDecision
from ssn.cognition.contracts import CognitiveLoopResult, CognitiveProposal, ProposalKind
from ssn.cognition.event_bus import AsyncEventBus
from ssn.cognition.events import CognitiveEvent, EventPriority
from ssn.cognition.memory.contracts import MemoryKind, MemoryServiceBoundary
from ssn.cognition.metrics import CognitionMetrics
from ssn.cognition.model_gateway.contracts import ModelRequest
from ssn.cognition.model_gateway.gateway import ModelGateway
from ssn.cognition.neuromorphic.providers import (
    DeterministicNeuromorphicProvider,
    data_to_neuromorphic_event,
)
from ssn.cognition.workspace import GlobalCognitiveWorkspace, TaskState
from ssn.cognition.world.contracts import WorldModelServiceBoundary
from ssn.embodiment.mock_adapter import MockEmbodimentAdapter


@dataclass
class CognitiveRuntime:
    """Bundled foundation components for DI / tests / optional wiring."""

    bus: AsyncEventBus = field(default_factory=AsyncEventBus)
    workspace: GlobalCognitiveWorkspace = field(default_factory=GlobalCognitiveWorkspace)
    model_gateway: ModelGateway = field(default_factory=ModelGateway.for_tests)
    neuromorphic: Any = field(default_factory=DeterministicNeuromorphicProvider)
    memory: MemoryServiceBoundary = field(default_factory=MemoryServiceBoundary)
    world: WorldModelServiceBoundary = field(default_factory=WorldModelServiceBoundary)
    embodiment: MockEmbodimentAdapter = field(default_factory=MockEmbodimentAdapter)
    metrics: CognitionMetrics = field(default_factory=CognitionMetrics)

    @classmethod
    def create(
        cls,
        *,
        memory_hub: Any = None,
        world_model: Any = None,
        model_gateway: Optional[ModelGateway] = None,
    ) -> "CognitiveRuntime":
        return cls(
            memory=MemoryServiceBoundary(memory_hub),
            world=WorldModelServiceBoundary(world_model),
            model_gateway=model_gateway or ModelGateway.for_tests(),
        )


class CognitiveLoop:
    """
    High-level orchestration skeleton.

    `process_text` mirrors LanguageEngine-style request/response while
    publishing events and updating the workspace. Tool/embodiment actions
    remain proposals only.
    """

    def __init__(self, runtime: Optional[CognitiveRuntime] = None) -> None:
        self.rt = runtime or CognitiveRuntime.create()

    async def process_text_async(
        self,
        text: str,
        *,
        role: str = "GUEST",
        context: Optional[Dict[str, Any]] = None,
        session_id: str = "",
        tenant_id: str = "default",
        use_neuromorphic: bool = True,
    ) -> CognitiveLoopResult:
        ctx = dict(context or {})
        trace_id = str(uuid.uuid4())
        proposals: List[CognitiveProposal] = []
        events_published = 0

        # 1) Input event
        event = CognitiveEvent.text_input(
            text,
            role=role,
            session_id=session_id,
            tenant_id=tenant_id,
            priority=EventPriority.HIGH if role == "OWNER" else EventPriority.NORMAL,
            trace_id=trace_id,
        )
        if not self.rt.bus.is_running:
            # Direct dispatch path for loop without long-lived worker
            ok = self.rt.bus.publish_nowait(event)
        else:
            ok = await self.rt.bus.publish(event)
        if ok:
            events_published += 1

        # 2) Neuromorphic salience (optional)
        salience = 0.5
        novelty = 0.5
        anomaly = 0.0
        if use_neuromorphic:
            neuro_event = data_to_neuromorphic_event(
                {"text": text, "modality": "text"},
                metadata={"role": role, "trace_id": trace_id},
            )
            neuro_out = self.rt.neuromorphic.process_event(neuro_event)
            salience = neuro_out.salience.score
            novelty = neuro_out.novelty
            anomaly = neuro_out.anomaly_score
            self.rt.metrics.neuromorphic_events += 1
            self.rt.metrics.spike_count += int(neuro_out.spikes_detected)
            if neuro_out.reflex_proposal:
                proposals.append(
                    CognitiveProposal(
                        proposal_id=str(uuid.uuid4()),
                        kind=ProposalKind.REFLEX,
                        payload=dict(neuro_out.reflex_proposal),
                        reason="neuromorphic_reflex",
                        confidence=float(neuro_out.salience.score),
                        requires_confirmation=True,
                        trace_id=trace_id,
                        source=getattr(self.rt.neuromorphic, "name", "neuromorphic"),
                    )
                )

        # 3) Workspace update
        self.rt.workspace.ingest_event(
            event,
            salience=salience,
            novelty=novelty,
            anomaly=anomaly,
        )
        self.rt.workspace.set_task(
            TaskState(task_id=trace_id, name="process_text", status="running", progress=0.3)
        )
        self.rt.workspace.update_context(
            {
                "role": role,
                "session_id": session_id,
                "last_user_text": text[:500],
                **{k: ctx[k] for k in list(ctx.keys())[:16]},
            }
        )

        # Memory / world refs (read-only context)
        for fact in self.rt.memory.recall_facts()[:5]:
            key = str(fact.get("key") or fact.get("id") or fact)[:64]
            self.rt.workspace.add_memory_ref(f"semantic:{key}")
        world_snap = self.rt.world.snapshot(include_events=False) if self.rt.world.world_model else {}
        if world_snap:
            self.rt.workspace.add_world_ref("world:snapshot")

        decision: AttentionDecision = self.rt.workspace.select_attention()
        if decision.selected is not None:
            self.rt.metrics.attention_selections += 1
        else:
            self.rt.metrics.attention_rejections += 1

        # 4) Model reasoning → reply + optional tool proposals
        model_req = ModelRequest.from_prompt(text, role=role, context=ctx)
        model_req.trace_id = trace_id
        model_req.session_id = session_id
        model_req.tenant_id = tenant_id
        model_resp = self.rt.model_gateway.complete(model_req)

        for tc in model_resp.tool_calls:
            proposals.append(
                CognitiveProposal(
                    proposal_id=str(uuid.uuid4()),
                    kind=ProposalKind.TOOL_CALL,
                    payload=tc.to_dict(),
                    reason=tc.reason or "model_tool_proposal",
                    confidence=tc.confidence,
                    requires_confirmation=True,
                    trace_id=trace_id,
                    source=model_resp.provider,
                )
            )
            self.rt.metrics.tool_proposals += 1

        # 5) Memory proposal (never auto-commit)
        mem_prop = self.rt.memory.propose(
            MemoryKind.EPISODIC,
            {"text": text[:500], "role": role, "reply_preview": model_resp.text[:200]},
            reason="cognitive_loop_turn",
            source="cognitive_loop",
            session_id=session_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
        )
        proposals.append(
            CognitiveProposal(
                proposal_id=mem_prop.proposal_id,
                kind=ProposalKind.MEMORY_WRITE,
                payload=mem_prop.to_dict(),
                reason=mem_prop.reason,
                requires_confirmation=mem_prop.requires_owner_approval,
                trace_id=trace_id,
                source="cognitive_loop",
            )
        )
        self.rt.metrics.memory_proposals += 1

        # 6) Workspace finalize
        self.rt.workspace.add_tool_observation(
            {
                "type": "model_response",
                "provider": model_resp.provider,
                "fallback_used": model_resp.fallback_used,
            }
        )
        self.rt.workspace.set_task(
            TaskState(task_id=trace_id, name="process_text", status="done", progress=1.0)
        )
        snap = self.rt.workspace.snapshot()
        self.rt.metrics.workspace_active_events = snap.capacity.get("active_events", 0)
        self.rt.metrics.workspace_capacity = snap.capacity.get("max_active_events", 0)
        self.rt.metrics.merge_bus(self.rt.bus.metrics.snapshot())

        return CognitiveLoopResult(
            reply=model_resp.text,
            role=role,
            proposals=proposals,
            workspace_snapshot=snap.to_dict(),
            events_published=events_published,
            engine="cognitive-loop-v1",
            metadata={
                "trace_id": trace_id,
                "attention": decision.to_dict(),
                "model_provider": model_resp.provider,
                "fallback_used": model_resp.fallback_used,
                "neuromorphic": use_neuromorphic,
                "note": "Proposals require existing policy/tool validation before side effects.",
            },
        )

    def process_text(
        self,
        text: str,
        *,
        role: str = "GUEST",
        context: Optional[Dict[str, Any]] = None,
        session_id: str = "",
        tenant_id: str = "default",
        use_neuromorphic: bool = True,
    ) -> Dict[str, Any]:
        """Sync wrapper returning a LanguageEngine-compatible dict plus extras."""
        try:
            asyncio.get_running_loop()
            running = True
        except RuntimeError:
            running = False

        coro = self.process_text_async(
            text,
            role=role,
            context=context,
            session_id=session_id,
            tenant_id=tenant_id,
            use_neuromorphic=use_neuromorphic,
        )
        if running:
            # Called from within a running loop (rare for CLI); use a dedicated thread.
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                result = pool.submit(asyncio.run, coro).result()
        else:
            result = asyncio.run(coro)

        data = result.to_dict()
        data["used_context"] = bool(context)
        return data
