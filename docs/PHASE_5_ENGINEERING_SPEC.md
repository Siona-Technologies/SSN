# Phase 5 Engineering Specification — Stateful Streaming Neuromorphic Runtime

**Status:** Planning gate proposed — implementation not started  
**Phase 4 prerequisite:** Complete and accepted  
**Primary objective:** Extend the accepted learned software SNN from complete 20 × 8 windows to bounded, stateful **event-by-event / timestep-by-timestep streaming inference** while preserving exact Phase 4 semantics, deterministic isolation, backpressure, and zero tool/actuator authority.

## 1. Why this is the next phase

Phase 4 accepted a real learned software SNN provider, but its learned interface
is intentionally window-based and stateless: one inference receives a complete
20 × 8 binary temporal sequence.

SIONA already has an asynchronous `AsyncEventBus` with bounded queues,
backpressure, priority, TTL, handler timeouts, failure isolation and graceful
shutdown. The missing architectural bridge is a stateful learned-neuromorphic
runtime that can consume bounded temporal steps as they arrive without requiring
callers to construct the full learned window first.

This phase advances SIONA toward genuine event-driven software neuromorphic
processing. It does **not** claim asynchronous neuromorphic silicon.

## 2. Bounded Phase 5 objective

Create an explicit streaming learned provider that reuses the accepted Phase 4
artifact and exact LIF equations, but maintains membrane state across individual
8-channel timesteps.

For one valid stream:

```text
8-channel step t=0
      ↓
stateful LIF update
      ↓
8-channel step t=1
      ↓
stateful LIF update
      ↓
...
      ↓
step t=19
      ↓
final readout → class probabilities / salience / spike count
```

The critical invariant is:

> Feeding the same 20 timesteps to the streaming provider in order must reproduce
> the accepted Phase 4 window provider result within a frozen numerical
> tolerance, without retraining or changing weights.

## 3. Phase 5A — streaming contract and state machine

Phase 5A should define and implement only the bounded streaming contract.

Proposed provider identity:

`siona-neuro-streaming-lif-v1`

Proposed learned step contract:

- explicit event type/modality for one temporal step;
- stream/session identifier;
- sequence index 0..19;
- exactly 8 binary numeric values;
- explicit lifecycle: start → steps → complete/reset;
- no out-of-order coercion;
- no implicit cross-session state sharing.

Each stream state must contain only what is required to reproduce the accepted
LIF calculation, such as membrane vector, prior reset/spike state as required by
exact semantics, cumulative spike count, next expected sequence index and safe
metadata.

## 4. State isolation requirements

The provider must be safe for multiple interleaved logical streams.

Required properties:

- stream A and stream B state are isolated;
- interleaving A/B events cannot alter each other's result;
- duplicate or out-of-order step indices fail closed;
- malformed claimed streaming events do not mutate stream state;
- reset affects only the named stream unless an explicit provider-wide reset is
  invoked;
- completed streams do not remain indefinitely resident;
- bounded maximum active streams;
- bounded idle-state lifetime/TTL or explicit deterministic eviction policy;
- no unbounded per-stream payload retention.

Exact limits must be frozen before implementation acceptance.

## 5. Phase 4 parity invariant

No retraining is required for the initial Phase 5 implementation.

For every accepted Phase 4 frozen test sequence:

1. run the existing window provider;
2. feed the same 20 rows sequentially through the new streaming provider;
3. compare final logits/probabilities/predicted class/spike count.

Predeclared parity targets for planning:

- predicted class agreement: 128/128;
- spike-count agreement: 128/128;
- maximum absolute logit difference ≤ 1e-12 for pure-Python vs pure-Python paths;
- maximum absolute probability difference ≤ 1e-12.

If implementation structure requires a looser floating tolerance, that change
must be justified and approved **before** the acceptance experiment, not after
observing failures.

## 6. AsyncEventBus integration boundary

The existing asynchronous bus is infrastructure, not model authority.

A later Phase 5 integration stage may subscribe a bounded adapter to a specific
streaming neuromorphic event type and forward validated temporal steps to the
streaming provider.

Required bus behavior:

- respect queue/backpressure policy;
- respect event TTL/expiry;
- preserve tenant/session/trace provenance;
- handler timeout/failure cannot corrupt learned stream state;
- shutdown clears/terminates streaming state safely;
- no bus event directly authorizes tools or physical actions.

The first streaming-provider implementation may be proven synchronously before
bus wiring, but Phase 5 is not complete until the asynchronous integration
boundary is validated.

## 7. Acceptance stages

Recommended evidence sequence:

- `EXP-5-001` — streaming contract/state-machine readiness and limits;
- `EXP-5-002` — pure-Python stateful provider implementation + full Phase 4 parity;
- `EXP-5-003` — multi-stream isolation/order/reset/TTL/bounds safety;
- `EXP-5-004` — AsyncEventBus integration, backpressure, timeout and shutdown gate;
- `EXP-5-005` — final breadth/evidence gate before ADR acceptance.

Experiment numbering records evidence and does not imply success.

## 8. Required Phase 5 acceptance criteria

Phase 5 cannot close unless all mandatory criteria are evidenced:

1. No Phase 4 artifact/weight mutation or retraining is required for the accepted
   initial streaming provider.
2. Streaming 20 ordered steps reproduces Phase 4 window inference within the
   frozen parity tolerance across all 128 frozen test samples.
3. Multiple interleaved streams are deterministic and isolated.
4. Duplicate/out-of-order/malformed claimed streaming events fail closed without
   partial state mutation.
5. Active stream count and retained state are bounded.
6. Stream lifecycle/reset/expiry is deterministic and testable.
7. AsyncEventBus integration respects backpressure, TTL, timeout and shutdown.
8. Hosted CI remains offline/model-free and requires no torch/snnTorch/Qwen.
9. Learned streaming output has no tool, policy, memory-mutation or physical
   authority.
10. Qwen registry/capabilities remain unchanged.
11. Existing Phase 4 window provider remains available and unchanged as an
    accepted reference path.
12. Evidence distinguishes event-driven **software** execution from
    neuromorphic-silicon execution.

## 9. Explicit non-objectives

Phase 5 does not authorize:

- SNN retraining or new learned weights for the initial streaming milestone;
- Qwen LoRA/QLoRA/PEFT/fine-tuning;
- CUDA/GPU claims;
- Loihi/FPGA/silicon claims;
- measured energy-efficiency claims;
- real event-camera hardware;
- making learned SNN output an actuator command;
- robotics/IoT/vehicle/drone control;
- semantic/vector-memory migration;
- STT/TTS or SIBONA embodiment;
- production-security certification.

## 10. Relationship to asynchronous execution

Phase 5 targets **software event-driven stateful inference**: SIONA may process
one bounded temporal step at a time and preserve membrane state between events.

This is materially more asynchronous/event-oriented than Phase 4's complete
window call, but it is still software running on conventional CPU hardware. It
must not be described as asynchronous neuromorphic silicon.

## 11. ADR requirement

ADR 0005 — Stateful streaming neuromorphic strategy should remain **Proposed**
until the full parity/isolation/event-bus evidence chain supports acceptance.

## 12. Planning-gate effect

If this planning gate is accepted, it authorizes **Phase 5A only**:

- read-only audit of the accepted Phase 4 LIF semantics and async bus;
- exact streaming event/state/lifecycle schema;
- frozen bounds and parity tolerances;
- model-free implementation/test scaffolding.

It does not by itself authorize retraining, hardware work or physical side
effects.
