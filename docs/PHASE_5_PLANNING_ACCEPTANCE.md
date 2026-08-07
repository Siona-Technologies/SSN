# Phase 5 Planning Acceptance — Stateful Streaming Neuromorphic Runtime

**Status:** Accepted planning gate  
**Decision date:** 2026-08-07  
**Planning base:** `e446960c3f1da08f165afd445b46d7c7a915b0ea`  
**Phase 5 implementation status:** Not started  
**ADR 0005:** Proposed

## Decision

The next governed SIONA phase is selected as:

> **Phase 5 — Stateful Streaming Neuromorphic Runtime**

The objective is to evolve the accepted Phase 4 learned software SNN from one
complete 20 × 8 window per call to bounded event-by-event/timestep-by-timestep
stateful software inference, while preserving exact Phase 4 model semantics and
all existing authority boundaries.

## Why this objective was selected

This is the smallest architectural step that joins two capabilities SIONA already
has:

1. an accepted learned temporal SNN with verified pure-Python inference; and
2. an asynchronous cognitive event bus with bounded queues, backpressure, TTL,
   timeouts and graceful shutdown.

It advances event-driven cognition without prematurely introducing new weights,
GPU hardware, neuromorphic silicon, robotics or language-model fine-tuning.

## Phase 5A authorization

After this planning gate is merged, Phase 5A is authorized to perform:

- read-only audit of exact Phase 4 pure-Python LIF update semantics;
- streaming event/state/lifecycle contract definition;
- frozen active-stream, identifier, ordering and TTL bounds;
- stateful pure-Python provider implementation using the unchanged Phase 4
  artifact;
- model-free unit/regression tests;
- parity scaffolding against the accepted Phase 4 window provider.

## Not authorized by this planning gate

- SNN retraining;
- weight/artifact mutation;
- Qwen training/adapters or capability changes;
- making the streaming provider globally default;
- CUDA/GPU claims;
- Loihi/FPGA/silicon claims;
- measured energy claims;
- real event-camera hardware;
- physical actuation/robotics/IoT;
- production certification.

AsyncEventBus wiring should occur only after the standalone stateful provider and
its parity/isolation semantics are proven.

## Frozen planning parity target

The initial Phase 5 implementation must target all 128 frozen Phase 4 held-out
sequences with:

- predicted-class agreement 128/128;
- spike-count agreement 128/128;
- max absolute logit difference ≤ 1e-12;
- max absolute probability difference ≤ 1e-12.

The parity target is window-provider versus streaming-provider using the same
committed artifact; no torch/snnTorch reference is required for that comparison.

## Governance state after planning

- Phases 1–4: **Complete for their accepted scopes**
- Phase 5 planning: **Accepted**
- Phase 5 implementation: **Not Started**
- Phase 5A: **Authorized**
- ADR 0005: **Proposed**
- SNN retraining: **Not authorized**
- Qwen changes: **Not authorized**
- Physical authority: **Not authorized**

## Historical numbering clarification

The repository contains older files/tests whose names include historical
`phase5`, `phase6`, and other numbers from earlier development sequences. Those
names are historical implementation labels and do **not** define the current
governed Phase 5 scope.

The authoritative current Phase 5 scope is this planning record plus
`PHASE_5_ENGINEERING_SPEC.md` and proposed ADR 0005.

## Next evidence gate

`EXP-5-001 — STREAMING NEUROMORPHIC CONTRACT / STATE-MACHINE READINESS`
