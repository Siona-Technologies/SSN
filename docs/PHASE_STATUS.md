# Phase Status

| Field | Value |
|-------|--------|
| Phase 1 | **Completed and hardened** (`183fa70`) |
| Phase 2 | **Completed and hardened** (accepted gate `7b92114`; merged `19b3b13`) |
| Phase 3 | **In progress — Phase 3A provider and evaluation foundation** |
| Phase 3 branch | `feat/siona-local-model-evals-v3` |
| Current machine | Intel i7-1165G7, Iris Xe, no CUDA GPU |

## Governing documents

- [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md)
- [PHASE_2_ACCEPTANCE.md](PHASE_2_ACCEPTANCE.md)
- [PHASE_3_ENGINEERING_SPEC.md](PHASE_3_ENGINEERING_SPEC.md)
- [SIONA_MODEL_GATEWAY.md](SIONA_MODEL_GATEWAY.md)

## Phase 3A status (this branch)

Delivered in Phase 3A:

- Centralized `SSN_RUNTIME_DATA_DIR` isolation for tests/smoke/CI
- Optional `LocalOpenWeightProvider` behind the existing `ModelProvider` contract
- Model registry / provenance contracts (mock CI fixtures only)
- Provider-oriented evaluation harness extension (deterministic/mock)
- Loopback-only mock local model HTTP server for transport tests

Explicitly **not** done in Phase 3A:

- No real local model installed
- No model weights downloaded
- No real-model benchmark conducted
- Phase 3A uses deterministic/mock validation only
- Actual runtime/model selection deferred to **Phase 3B**
- SIBONA remains unimplemented
- SNN training remains deferred
- Physical embodiments remain deferred

## Known limitations

- Optional local provider requires an explicitly configured user-controlled endpoint
- Default Front Door path remains the legacy dummy provider unless opted in
- Owner-adjacent baseline failures remain technical debt

## Next

Phase 3B: select and verify a real optional open-weight model (still optional; CI remains deterministic).
Phase 4 remains **not started**.
