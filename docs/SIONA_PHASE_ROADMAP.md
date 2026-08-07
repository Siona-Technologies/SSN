# SIONA Phase Roadmap

Governing charter: [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md)  
Current phase status: [PHASE_STATUS.md](PHASE_STATUS.md)  
Phase 3B acceptance: [PHASE_3B_ACCEPTANCE.md](PHASE_3B_ACCEPTANCE.md)  
Phase 4 planning gate: [PHASE_4_PLANNING_ACCEPTANCE.md](PHASE_4_PLANNING_ACCEPTANCE.md)

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

**Planning gate accepted; EXP-4-003/004/005 verified; ADR 0004 acceptance and Phase 4 completion pending.**

The bounded Phase 4 objective is to deliver the first **real learned SNN
provider** behind SIONA's existing neuromorphic-provider boundary for a temporal
salience/classification task. EXP-4-003 verified a CPU candidate artifact.
EXP-4-004 integrated an explicit pure-Python learned provider with snnTorch
parity and deterministic fallback. EXP-4-005 hardened artifact/input/batch
safety and recorded breadth/integrity evidence. ADR 0004 acceptance and Phase 4
completion remain separately gated.

Planning / gate records:

- [PHASE_4_ENGINEERING_SPEC.md](PHASE_4_ENGINEERING_SPEC.md)
- [PHASE_4_PLANNING_ACCEPTANCE.md](PHASE_4_PLANNING_ACCEPTANCE.md)
- [PHASE_4B_FIRST_CPU_SNN_TRAINING_GATE.md](PHASE_4B_FIRST_CPU_SNN_TRAINING_GATE.md)
- [SIONA_PHASE_4B_FIRST_CPU_SNN_TRAINING.md](SIONA_PHASE_4B_FIRST_CPU_SNN_TRAINING.md)
- [SIONA_PHASE_4C_LEARNED_PROVIDER_INTEGRATION.md](SIONA_PHASE_4C_LEARNED_PROVIDER_INTEGRATION.md)
- [SIONA_PHASE_4D_BREADTH_SAFETY_GATE.md](SIONA_PHASE_4D_BREADTH_SAFETY_GATE.md)
- proposed [ADR 0004](adr/0004-learned-neuromorphic-backend-strategy.md)

### Completed through EXP-4-005

- Phase 4A readiness (EXP-4-001);
- Phase 4B frozen training gate;
- one controlled CPU training/evaluation run (`FIRST_CPU_SNN_TRAINING_VERIFIED`);
- canonical candidate JSON under `artifacts/neuromorphic/`;
- explicit learned provider + fallback/parity (`LEARNED_SNN_PROVIDER_PARITY_VERIFIED`);
- breadth/safety/integrity gate (`PHASE4_LEARNED_SNN_BREADTH_SAFETY_VERIFIED`).

### Not authorized yet

- ADR 0004 acceptance / Phase 4 completion;
- CUDA/GPU claim;
- Qwen fine-tuning/adapters;
- physical actuation/robotics/IoT;
- memory/database migration;
- voice/SIBONA embodiment work.

The next controlled blocker is **ADR 0004 ACCEPTANCE + PHASE 4 COMPLETION DECISION**.

## Later capabilities — unsequenced after the Phase 4 scope

The following remain future candidates and are **not** part of the accepted
Phase 4 learned-neuromorphic scope:

- Vector / Postgres memory backends behind existing contracts
- Transactional world-model store
- Real STT/TTS and voice embodiment work
- First MQTT or ROS 2 adapter, still safety-gated and confirmation-required
- Semantic retrieval / embedding backends under explicit governance
- Production deployment/packaging hardening
- Explicit product-integration decisions outside present Core scope
- Future user-facing assistant embodiment (working name: SIBONA)
- SIONA-specific language-model adapters/fine-tuning under a separate
  dataset/training governance decision
- Future SIONA-native foundation-model research under SIONA-controlled training
  provenance
- Loihi/FPGA deployment after learned-provider software evidence

## Legacy planning note

`SIONA_BUILD_PLAN.md` is a dated planning reference whose internal phase numbers
were created before the later governed Phase 1–3 acceptance sequence. Its
historical “Phase 4” label must **not** be treated as the current Phase 4
authorization. Use this roadmap, `PHASE_STATUS.md`, and the accepted Phase 4
planning record for current phase state.
