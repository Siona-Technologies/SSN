# SIONA Phase Roadmap

Governing charter: [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md)  
Current phase status: [PHASE_STATUS.md](PHASE_STATUS.md)  
Phase 3B acceptance: [PHASE_3B_ACCEPTANCE.md](PHASE_3B_ACCEPTANCE.md)  
Phase 4 acceptance: [PHASE_4_ACCEPTANCE.md](PHASE_4_ACCEPTANCE.md)

This roadmap records the **current governed phase sequence**. Older dated
planning documents may contain earlier phase numbering; when they differ, the
Vision Charter, `PHASE_STATUS.md`, accepted ADRs, and phase acceptance records
control current status and authorization.

## Phase 1 — Cognitive runtime foundation

**Completed and hardened** (`183fa70`).

Delivered:

- Event fabric + workspace + attention
- Model gateway contracts + legacy adapters
- Neuromorphic provider abstraction + deterministic reference
- Cognitive loop skeleton
- Memory / world boundaries
- Embodiment contracts + mock adapter
- Docs + deterministic tests
- Owner-control freeze respected

## Phase 2 — Runtime integration

**Completed and hardened.** Accepted implementation gate: `7b92114`.  
Formal record: [PHASE_2_ACCEPTANCE.md](PHASE_2_ACCEPTANCE.md).

Delivered:

- Runtime modes (`legacy`, `shadow`, `cognitive_experimental`)
- Integration facade and observation bridges
- Exact legacy Front Door compatibility
- Trace continuity and shared-deps isolation
- Safe async observation lifecycle
- Governance documentation

## Phase 3 — Local model and evaluation layer

**Completed and accepted.**

Phase 3A established the optional provider/evaluation foundation with
deterministic, model-free CI. Phase 3B then installed and governed the first real
optional local open-weight baseline and completed the controlled evaluation and
registry-bound runtime path.

Accepted Phase 3B baseline:

- Runtime: llama.cpp b9968
- Model: `Qwen3-1.7B-Q4_K_M`
- Registry provider: `siona-local-open-weight-v1`
- Verified registry capability: bounded text/chat at context 4096
- `tools=false`
- `structured_json=false` (`NOT_VERIFIED` natively)
- `streaming=false` (`UNSUPPORTED_ON_PINNED_BASELINE`)
- `multimodal=false`
- `siona_native=false`
- Steady-state runtime: stopped; no automatic/permanent startup

Key accepted evidence:

- EXP-3B-011 — Gate E breadth
- EXP-3B-012 — conservative model-registry activation review
- EXP-3B-013 — `STATE_C_VERIFIED`
- ADR 0003 — **Accepted (Phase 3B)**
- [PHASE_3B_ACCEPTANCE.md](PHASE_3B_ACCEPTANCE.md)

Phase 3 is complete for its defined local-model/evaluation scope. This is not a
production certification and does not make the external Qwen weights SIONA-native.

## Phase 4 — Learned neuromorphic backend

**Completed and accepted.**

Phase 4 delivered SIONA's first genuine learned software SNN component behind
the existing neuromorphic-provider boundary while preserving deterministic
fallback and authority separation.

Accepted evidence chain:

- EXP-4-001 — readiness/task/data/backend governance;
- EXP-4-003 — `FIRST_CPU_SNN_TRAINING_VERIFIED`;
- EXP-4-004 — `LEARNED_SNN_PROVIDER_PARITY_VERIFIED`;
- EXP-4-005 — `PHASE4_LEARNED_SNN_BREADTH_SAFETY_VERIFIED`;
- ADR 0004 — **Accepted (Phase 4)**;
- [PHASE_4_ACCEPTANCE.md](PHASE_4_ACCEPTANCE.md).

Accepted learned component:

- provider: `siona-neuro-learned-lif-v1`;
- task: `phase4a-temporal-salience-v1`;
- architecture: `phase4b-lif-final-membrane-v1`;
- canonical artifact SHA-256:
  `dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc`;
- deterministic/reference provider remains default/fallback;
- normal runtime is standard-library only;
- no torch/snnTorch/numpy runtime dependency;
- no Qwen capability or registry change;
- no tool or physical authority;
- CPU software SNN only; no CUDA/GPU, Loihi, FPGA or neuromorphic-silicon claim.

Phase 4 is complete for its defined learned-neuromorphic software scope. This is
not production-security certification and does not authorize physical actuation,
Qwen adaptation, or automatic promotion of the learned provider to global
default.

## Phase 5 — Planning boundary

**Not started.**

Phase 4 completion makes Phase 5 eligible for a separate governed planning
decision. Phase 5 scope is deliberately **not** inferred from old phase numbering
or from the remaining deferred-capability list.

Before Phase 5 implementation begins, the planning gate must:

1. select one bounded objective;
2. define explicit objectives and non-objectives;
3. specify data/model/hardware dependencies and authority implications;
4. define tests, evidence and acceptance criteria before implementation;
5. preserve deterministic policy, owner-control and physical-safety boundaries;
6. decide whether a new ADR is required;
7. keep Qwen fine-tuning, physical embodiment, memory migration, voice and
   asynchronous/event-stream SNN expansion separately authorized unless one is
   explicitly chosen as the Phase 5 objective.

Until that planning gate is accepted, **Phase 5 remains NOT STARTED**.

## Later capabilities — unsequenced until Phase 5 planning

Future candidates include:

- true streaming/event-by-event learned SNN state updates;
- vector/Postgres memory backends behind existing contracts;
- transactional world-model store;
- real STT/TTS and voice embodiment work;
- first MQTT or ROS 2 adapter with separate physical-safety gates;
- semantic retrieval / embedding backends under explicit governance;
- production deployment/packaging hardening;
- SIONA-specific language-model adapters/fine-tuning under separate data/training
  governance;
- future SIONA-native foundation-model research under SIONA-controlled training
  provenance;
- CUDA/GPU benchmarking for learned neuromorphic workloads;
- Loihi/FPGA/neuromorphic-silicon deployment;
- future user-facing assistant embodiment (working name: SIBONA).

None of these is automatically Phase 5 merely because it appears in this list.

## Legacy planning note

`SIONA_BUILD_PLAN.md` is a dated planning reference whose internal phase numbers
were created before the later governed Phase 1–4 acceptance sequence. Its older
phase labels must **not** be treated as current authorization. Use this roadmap,
`PHASE_STATUS.md`, and accepted phase/ADR records for current state.
