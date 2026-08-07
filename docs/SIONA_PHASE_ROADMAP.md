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
deterministic, model-free CI. Phase 3B installed and governed the first real
optional local open-weight language-model baseline and completed controlled
registry-bound runtime verification.

Accepted Phase 3B baseline:

- llama.cpp b9968;
- `Qwen3-1.7B-Q4_K_M`;
- registry provider `siona-local-open-weight-v1`;
- `chat=true` at context 4096;
- `tools=false`;
- `structured_json=false` (`NOT_VERIFIED` natively);
- `streaming=false` (`UNSUPPORTED_ON_PINNED_BASELINE`);
- `multimodal=false`;
- `siona_native=false`;
- steady-state runtime stopped.

ADR 0003 is **Accepted (Phase 3B)**.

## Phase 4 — Learned neuromorphic backend

**Completed and accepted.**

Phase 4 delivered the first real learned SNN provider behind SIONA's existing
neuromorphic-provider boundary for a bounded temporal salience/classification
task.

Accepted provider:

- provider ID: `siona-neuro-learned-lif-v1`;
- task: `phase4a-temporal-salience-v1`;
- architecture: `phase4b-lif-final-membrane-v1`;
- input: explicit `temporal_salience_v1`, 20 × 8 binary sequence;
- trained artifact SHA-256:
  `dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc`;
- accepted runtime: pure Python without torch/snnTorch/numpy/Norse;
- explicit activation only;
- deterministic provider remains default/reference/fallback;
- tool authority false;
- physical actuation authority false;
- energy metrics false.

Accepted evidence chain:

- EXP-4-001 — readiness/task/data governance;
- Phase 4B frozen training gate;
- EXP-4-003 — `FIRST_CPU_SNN_TRAINING_VERIFIED`;
- EXP-4-004 — `LEARNED_SNN_PROVIDER_PARITY_VERIFIED`;
- EXP-4-005 — `PHASE4_LEARNED_SNN_BREADTH_SAFETY_VERIFIED`;
- ADR 0004 — **Accepted (Phase 4)**;
- [PHASE_4_ACCEPTANCE.md](PHASE_4_ACCEPTANCE.md).

Key bounded evidence:

- 128/128 held-out samples correct;
- balanced accuracy 1.0 and class recalls 1.0/1.0;
- 197/197 class/spike parity samples against the retained snnTorch reference;
- 64 reversed-positive controls with mean score drop ≈0.99943249;
- 9/9 valid edge controls;
- malformed learned inputs fail closed;
- corrupt artifacts reject before inference;
- unsupported modalities use deterministic fallback;
- maximum batch 256;
- maximum artifact 256 KiB with bounded read.

Phase 4 is complete for this **learned neuromorphic software-provider scope**.
This does not claim fully asynchronous neuromorphic hardware execution or a
general SNN brain.

### Explicitly deferred beyond Phase 4

- event-by-event persistent/stateful streaming SNN inference;
- CUDA/GPU SNN training or benchmark claims;
- Loihi/FPGA/neuromorphic-silicon deployment;
- measured SNN energy efficiency;
- real event-camera input;
- making the learned provider globally default;
- Qwen fine-tuning/adapters;
- physical actuation/robotics/IoT;
- semantic/vector memory migration;
- voice/SIBONA embodiment work;
- production-security certification.

## Next phase — not selected

**No next phase has started.**

Completion of Phase 4 does not automatically select Phase 5 or inherit phase
numbers/scopes from historical planning documents.

The next governed planning gate must choose one bounded objective, define its
non-objectives and acceptance criteria, and determine whether a new ADR is
required before implementation starts.

## Future capability candidates — unsequenced

The following remain candidates only until a future planning decision selects
one:

- streaming/event-by-event neuromorphic processing;
- GPU or neuromorphic-hardware SNN benchmarking;
- Vector / Postgres memory backends;
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

`SIONA_BUILD_PLAN.md` is a dated planning reference whose internal phase numbers
were created before the later governed phase acceptance sequence. Its historical
phase labels must **not** be treated as current authorization. Use this roadmap,
`PHASE_STATUS.md`, and accepted phase records for current state.
