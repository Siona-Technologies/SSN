# SIONA Phase Roadmap

Governing charter: [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md)  
Phase status: [PHASE_STATUS.md](PHASE_STATUS.md)

## Phase 1 — Cognitive runtime foundation

**Completed and hardened** (`183fa70`).

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

**Specified but not started.**  
Specification only: [PHASE_3_ENGINEERING_SPEC.md](PHASE_3_ENGINEERING_SPEC.md).

Recommended future branch (do not create until Phase 3 is authorized):
`feat/siona-local-model-evals-v3`.

## Later phases (sketch)

- Vector / Postgres memory backends behind existing contracts
- Transactional world-model store
- First MQTT or ROS 2 adapter (still gated, confirmation required)
- Learned neuromorphic backends (snnTorch / Norse) as providers
- Explicit product-integration decisions (out of present Core scope)
- Future user-facing assistant embodiment (working name: SIBONA)
