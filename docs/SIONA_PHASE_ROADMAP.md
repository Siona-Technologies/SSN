# SIONA Phase Roadmap

Governing charter: [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md)  
Current phase status: [PHASE_STATUS.md](PHASE_STATUS.md)  
Phase 3B acceptance: [PHASE_3B_ACCEPTANCE.md](PHASE_3B_ACCEPTANCE.md)

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

## Phase 4 — Planning boundary

**Not started.**

Phase 3 completion makes Phase 4 eligible for a **separate governed planning
and authorization decision**, but does not define or start Phase 4
implementation automatically.

Before Phase 4 implementation begins, the planning gate must:

1. Reconcile older planning documents and current architecture.
2. Select one bounded Phase 4 objective rather than combining unrelated future
   capabilities.
3. Define explicit objectives, non-objectives, tests and acceptance criteria.
4. Classify every proposed capability using the Vision Charter taxonomy.
5. Preserve owner-control, policy, tool-authority and physical-safety boundaries.
6. Identify any hardware-gated work before implementation.
7. Decide whether a new ADR is required for architectural changes.
8. Keep Qwen/model startup, model training and capability expansion separately
   authorized unless the approved Phase 4 specification explicitly includes
   them.

Until that planning gate is accepted, **Phase 4 remains NOT STARTED**.

## Later capabilities — unsequenced until Phase 4 planning

The following remain future candidates and must not be inferred to be the
Phase 4 scope merely from their order here:

- Vector / Postgres memory backends behind existing contracts
- Transactional world-model store
- Real STT/TTS and voice embodiment work
- First MQTT or ROS 2 adapter, still safety-gated and confirmation-required
- Learned neuromorphic backends (for example snnTorch / Norse) as providers
- Semantic retrieval / embedding backends under explicit governance
- Production deployment/packaging hardening
- Explicit product-integration decisions outside present Core scope
- Future user-facing assistant embodiment (working name: SIBONA)
- SIONA-specific model adapters/fine-tuning under a separate dataset/training
  governance decision
- Future SIONA-native model research under SIONA-controlled training provenance

## Legacy planning note

`SIONA_BUILD_PLAN.md` is a dated planning reference whose internal phase numbers
were created before the later governed Phase 1–3 acceptance sequence. For
example, its historical “Phase 4” label must **not** be treated as the current
Phase 4 authorization. Use this roadmap and `PHASE_STATUS.md` for current phase
state.
