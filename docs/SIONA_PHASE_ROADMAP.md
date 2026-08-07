# SIONA Phase Roadmap

Governing charter: [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md)  
Current phase status: [PHASE_STATUS.md](PHASE_STATUS.md)  
Phase 3B acceptance: [PHASE_3B_ACCEPTANCE.md](PHASE_3B_ACCEPTANCE.md)  
Phase 4 acceptance: [PHASE_4_ACCEPTANCE.md](PHASE_4_ACCEPTANCE.md)  
Phase 5 planning: [PHASE_5_PLANNING_ACCEPTANCE.md](PHASE_5_PLANNING_ACCEPTANCE.md)

This roadmap records the **current governed phase sequence**. Older dated
planning documents may contain earlier phase numbering; when they differ, the
Vision Charter, `PHASE_STATUS.md`, accepted ADRs, and phase acceptance/planning
records control current status and authorization.

## Phase 1 — Cognitive runtime foundation

**Completed and hardened** (`183fa70`).

Delivered event fabric, workspace/attention, model and neuromorphic provider
contracts, cognitive-loop skeleton, memory/world boundaries, embodiment
contracts, documentation and deterministic tests.

## Phase 2 — Runtime integration

**Completed and hardened.** Accepted implementation gate: `7b92114`.  
Formal record: [PHASE_2_ACCEPTANCE.md](PHASE_2_ACCEPTANCE.md).

## Phase 3 — Local model and evaluation layer

**Completed and accepted.**

Phase 3 accepted the optional local Qwen/llama.cpp path behind the governed model
registry and gateway. Conservative capabilities remain `chat=true` at context
4096 with tools/structured JSON/streaming/multimodal false and
`siona_native=false`.

ADR 0003 is **Accepted (Phase 3B)**.

## Phase 4 — Learned neuromorphic backend

**Completed and accepted.**

Phase 4 delivered the first real learned SNN provider behind SIONA's
neuromorphic-provider boundary for a bounded temporal-salience task.

Accepted provider:

- `siona-neuro-learned-lif-v1`;
- task `phase4a-temporal-salience-v1`;
- architecture `phase4b-lif-final-membrane-v1`;
- 20 × 8 binary complete-window input;
- pure-Python runtime using verified SIONA-trained artifact;
- deterministic provider retained as default/reference/fallback;
- tool and physical authority false.

Evidence chain:

- EXP-4-003 — `FIRST_CPU_SNN_TRAINING_VERIFIED`;
- EXP-4-004 — `LEARNED_SNN_PROVIDER_PARITY_VERIFIED`;
- EXP-4-005 — `PHASE4_LEARNED_SNN_BREADTH_SAFETY_VERIFIED`;
- ADR 0004 — **Accepted (Phase 4)**.

Phase 4 deliberately did not claim persistent event-by-event streaming,
neuromorphic silicon, GPU training, measured energy efficiency or physical
actuation.

## Phase 5 — Stateful streaming neuromorphic runtime

**Planning accepted; implementation not started.**

The current governed Phase 5 objective is to reuse the unchanged accepted Phase
4 learned artifact while evolving the software execution contract from one
complete 20 × 8 window per call to bounded stateful processing of individual
8-channel temporal steps.

Planning records:

- [PHASE_5_ENGINEERING_SPEC.md](PHASE_5_ENGINEERING_SPEC.md)
- [PHASE_5_PLANNING_ACCEPTANCE.md](PHASE_5_PLANNING_ACCEPTANCE.md)
- proposed [ADR 0005](adr/0005-stateful-streaming-neuromorphic-strategy.md)

### Phase 5A authorized now

- exact streaming event/state/lifecycle contract;
- frozen active-stream/order/TTL/state bounds;
- pure-Python streaming provider using the unchanged Phase 4 artifact;
- full 128-sample streaming/window parity scaffolding;
- deterministic interleaved-stream isolation/reset/failure tests.

### Later Phase 5 stages

After standalone stateful semantics are proven:

- multi-stream breadth/safety evidence;
- integration with the existing `AsyncEventBus`;
- backpressure/TTL/timeout/shutdown evidence;
- final breadth gate and ADR 0005 acceptance decision.

### Not authorized by Phase 5 planning

- SNN retraining or weight mutation;
- Qwen adaptation/capability changes;
- global learned-provider default switch;
- CUDA/GPU, Loihi/FPGA or measured-energy claims;
- real event-camera hardware;
- tools, robotics, IoT or physical actuation;
- production certification.

This phase targets **event-driven software state**, not neuromorphic-silicon
execution.

## Historical Phase 4 closeout note

At the Phase 4 closeout boundary, **no next phase had started** and a **separate
governed planning decision** was required. That requirement has now been
satisfied by the Phase 5 planning record; the historical Phase 4 acceptance
snapshot remains unchanged.

## Future capability candidates — unsequenced beyond current Phase 5

- GPU or neuromorphic-hardware SNN benchmarking;
- real event-camera input;
- Vector/Postgres memory backends;
- transactional world-model store;
- semantic retrieval / embedding backends;
- real STT/TTS and voice embodiment;
- MQTT or ROS 2 adapters under physical-safety gates;
- production deployment/packaging hardening;
- user-facing assistant embodiment (working name: SIBONA);
- SIONA-specific language-model adapters/fine-tuning under separate dataset and
  training governance;
- future SIONA-native foundation-model research under SIONA-controlled training
  provenance.

## Legacy planning note

`SIONA_BUILD_PLAN.md` and older code/test names such as historical `phase5_*`
labels predate the current governed sequence. Their numeric labels do **not**
define current Phase 5 authorization. Use this roadmap, `PHASE_STATUS.md`, and
the Phase 5 planning record for current state.
