# Phase Status

| Field | Value |
|-------|--------|
| Phase 1 | **Completed and hardened** (`183fa70`) |
| Phase 2 | **Completed and hardened** (accepted gate `7b92114`; merged `19b3b13`) |
| Phase 3 | **In progress — Phase 3A completed; Phase 3B not started** |
| Phase 3A | **Completed and hosted-CI accepted** (`d6c17d0`; merged `2e6abb6`) |
| Phase 3B | **Not started** |
| Phase 3A PR | [#2](https://github.com/Siona-Technologies/SSN/pull/2) |
| Current machine | Intel i7-1165G7, Iris Xe, no CUDA GPU |

## Governing documents

- [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md)
- [PHASE_2_ACCEPTANCE.md](PHASE_2_ACCEPTANCE.md)
- [PHASE_3_ENGINEERING_SPEC.md](PHASE_3_ENGINEERING_SPEC.md)
- [SIONA_MODEL_GATEWAY.md](SIONA_MODEL_GATEWAY.md)
- [adr/0002-local-open-weight-transport.md](adr/0002-local-open-weight-transport.md)

## Phase 3A status (completed)

Phase 3A is **completed, hardened, hosted-CI accepted and merged**.

- Accepted feature SHA: `d6c17d0d723ef309cca1f8edf3fb467b12d04d2a`
- Merge commit: `2e6abb6d70f4204bb4f9e479e081b0a9fc116580`
- PR: [#2](https://github.com/Siona-Technologies/SSN/pull/2)

Hosted CI (PR #2):

- Python 3.11: 277 passed, 4 skipped
- Python 3.12: 277 passed, 4 skipped
- Production evaluation: 7/7 on both
- HTTP smoke: passed on both

Local evidence:

- Provider evaluation: 25/25 (deterministic/mock only)

Delivered in Phase 3A (including final security/isolation gate):

- Centralized `SSN_RUNTIME_DATA_DIR` with **per-test** isolation in the governed runner
- Ownership-safe cleanup (external env values are not cleared)
- Optional `LocalOpenWeightProvider` behind the existing `ModelProvider` contract
- HTTP redirects rejected by default; embedded credentials/fragments rejected
- Canonical provider-boundary sanitization for full `ModelRequest` payloads
- Conservative unverified capability reporting (no invented tools/JSON/context window)
- Strict model registry schema with transactional loading (mock fixtures only)
- Declarative provider evaluation cases with hard child-process timeouts
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

Phase 3 overall remains **in progress**. Phase 3B remains **not started**.
The optional local provider is **not** production-security certified.

## Known limitations

- Optional local provider requires explicitly configured endpoint **and** model ID
- Provider is **not** claimed production-secure
- Synchronous urllib transport does **not** support mid-request cancellation
  (pre-network cancel only; mid-request cancel deferred to async transport)
- Artefact verification is separate from behavioural capability verification
- Default Front Door path remains the legacy dummy provider unless opted in
- Owner-adjacent baseline failures remain technical debt

## Next

Phase 3B: select and verify a real optional open-weight model (still optional; CI remains deterministic).
Phase 4 remains **not started**.
