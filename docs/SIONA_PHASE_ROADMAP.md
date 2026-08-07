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

**Planning gate accepted; implementation/training not started.**

The bounded Phase 4 objective is to deliver the first **real learned SNN
provider** behind SIONA's existing neuromorphic-provider boundary for a temporal
salience/classification task.

Planning decision:

- [PHASE_4_ENGINEERING_SPEC.md](PHASE_4_ENGINEERING_SPEC.md)
- [PHASE_4_PLANNING_ACCEPTANCE.md](PHASE_4_PLANNING_ACCEPTANCE.md)
- proposed [ADR 0004](adr/0004-learned-neuromorphic-backend-strategy.md)

### Authorized now — Phase 4A only

- read-only neuromorphic contract/reference audit;
- exact task definition;
- synthetic/public dataset governance and split design;
- backend/version/licence research;
- predeclared metrics and acceptance threshold design;
- checkpoint/artifact metadata schema design;
- deterministic test scaffolding that does not require real training.

### Not authorized yet

- real SNN training execution;
- new training dependency installation;
- CUDA/GPU claim;
- Qwen fine-tuning/adapters;
- physical actuation/robotics/IoT;
- memory/database migration;
- voice/SIBONA embodiment work.

The first real SNN training run requires a separate execution-ready Phase 4A
record with exact data, backend/version, topology/config, seed, metrics,
predeclared baseline/threshold and cleanup procedure.

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
