# ADR 0005 — Stateful streaming neuromorphic strategy

## Status

Proposed

## Context

Phase 4 accepted `siona-neuro-learned-lif-v1`, a learned software SNN for a
bounded 20 × 8 temporal-salience task. Its accepted inference contract is
stateless at the provider boundary: callers supply the complete sequence in one
call.

SIONA already has an in-process `AsyncEventBus` with bounded queues,
priority-aware backpressure, event TTL, handler timeouts, dead-letter handling
and graceful shutdown. The next architectural question is whether the accepted
learned LIF computation can become a stateful, event-by-event software provider
without changing weights, weakening isolation or granting new authority.

## Decision under evaluation

Evaluate a replaceable streaming learned provider that:

- reuses the exact accepted Phase 4 artifact and LIF semantics;
- consumes one 8-channel binary temporal step at a time;
- keeps bounded per-stream membrane/lifecycle state;
- produces the same completed 20-step result as the Phase 4 window provider;
- isolates interleaved streams by explicit stream/session identity;
- fails closed on malformed, duplicate and out-of-order claimed stream steps;
- can later receive validated steps through the existing AsyncEventBus;
- remains pure Python and model-free in hosted CI;
- receives no tool, policy, memory-mutation or physical authority.

## Key invariant

For every frozen Phase 4 test sequence, ordered streaming execution must reproduce
the accepted window-provider result within the predeclared numerical tolerance.
The first Phase 5 milestone therefore requires **no SNN retraining** and no weight
mutation.

## State boundary

A streaming provider introduces persistent in-process model state, so the state
must be explicitly governed.

Before ADR acceptance, evidence must establish:

- maximum active stream count;
- exact per-stream state schema;
- valid lifecycle and completion semantics;
- duplicate/out-of-order behavior;
- reset semantics;
- idle TTL or deterministic eviction policy;
- tenant/session isolation where those identifiers are used;
- bounded memory retention;
- deterministic behavior under interleaving;
- safe shutdown cleanup.

## AsyncEventBus boundary

The event bus may transport validated streaming inputs but does not become model
authority.

Bus integration must preserve:

- existing backpressure semantics;
- event expiry/TTL;
- trace/session/tenant provenance;
- handler timeout and failure isolation;
- graceful shutdown;
- no direct tool or actuator execution.

## Accepted Phase 4 path remains authoritative reference

Phase 5 must not silently replace or rewrite the accepted Phase 4 provider.
`LearnedTemporalSalienceProvider` remains the accepted fixed-window reference
until a later explicit activation/default decision.

## Non-claims

Even if this ADR is accepted later, stateful software streaming does not itself
prove:

- neuromorphic-silicon execution;
- Loihi/FPGA deployment;
- GPU execution;
- measured energy efficiency;
- real event-camera operation;
- physical actuation;
- a generally intelligent SNN.

## Alternatives

| Alternative | Disposition |
|---|---|
| Keep only fixed-window provider | Safe reference remains, but does not advance event-driven processing |
| Retrain a new recurrent SNN immediately | Deferred; first prove streaming equivalence with existing weights |
| Feed arbitrary bus events into the learned model | Rejected; streaming learned events require a strict dedicated schema |
| Global singleton membrane state | Rejected; violates session/stream isolation |
| Use Qwen to aggregate streaming events | Rejected for this objective; conflates deliberative LLM and neuromorphic roles |
| Jump directly to Loihi/FPGA | Deferred; software state semantics must be proven first |

## Acceptance conditions

ADR 0005 may become Accepted only if:

1. streaming contract/state limits are frozen before acceptance experiments;
2. all 128 frozen Phase 4 test sequences meet exact streaming/window parity;
3. interleaved streams remain deterministic and isolated;
4. malformed, duplicate and out-of-order claimed stream inputs fail closed;
5. rejected inputs do not partially mutate successful stream state;
6. active state and lifecycle retention are bounded;
7. reset/expiry/shutdown behavior is deterministic;
8. AsyncEventBus integration respects backpressure, TTL, timeout and shutdown;
9. hosted CI remains offline without torch/snnTorch/Qwen;
10. Phase 4 artifact and weights remain unchanged;
11. no tool/policy/memory/physical authority is granted;
12. documentation keeps software streaming distinct from neuromorphic hardware.

## Non-authorization

This Proposed ADR does not authorize retraining, Qwen adaptation, hardware
acceleration, event-camera deployment, physical actuation or production
certification.

## References

- [PHASE_5_ENGINEERING_SPEC.md](../PHASE_5_ENGINEERING_SPEC.md)
- [PHASE_4_ACCEPTANCE.md](../PHASE_4_ACCEPTANCE.md)
- [SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md](../SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md)
- [SIONA_PHASE_ROADMAP.md](../SIONA_PHASE_ROADMAP.md)
