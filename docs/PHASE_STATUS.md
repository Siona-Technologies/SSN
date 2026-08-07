# Phase Status

| Field | Value |
|-------|--------|
| Phase 1 | **Completed and hardened** (`183fa70`) |
| Phase 2 | **Completed and hardened** (accepted gate `7b92114`; merged `19b3b13`) |
| Phase 3 | **In progress — Phase 3A completed; Phase 3B research recorded** |
| Phase 3A | **Completed and hosted-CI accepted** (`d6c17d0`; merged `2e6abb6`) |
| Phase 3B | **In progress — baseline installed/verified; openai_chat dialect implemented; controlled real-provider text path validated (runtime stopped); governed prompt-context bridge merged (EXP-3B-006); first approved public identity registry merged (EXP-3B-007); controlled real-Qwen governed identity campaign executed (EXP-3B-008, acceptance not met, explicit retrieval only, runtime shut down); governed identity response guard implemented and offline-validated with fail-closed hardening (EXP-3B-009); controlled real-Qwen guarded-path retest executed (EXP-3B-010: all 21 guarded finals passed; model-native structured JSON remains unverified; deterministic JSON fallback contained failures; runtime shut down; complete responses local-only); Gate E breadth recorded (EXP-3B-011: native text recomputed; JSON exact-schema 6/6 separately recorded; native JSON capability NOT_VERIFIED without original provider-origin proof; 8/8 safety containment; streaming unsupported on pinned baseline; registry-review recommendation conservative-allow); model-registry activation review passed with conservative capability binding (EXP-3B-012: canonical manifest `config/model_registry.json`; exact provider binding; runtime not started); ADR 0003 acceptance and Phase 3B completion decision still pending** |
| Phase 3A PR | [#2](https://github.com/Siona-Technologies/SSN/pull/2) |
| Current machine | Intel i7-1165G7, Iris Xe, no CUDA GPU |

## Governing documents

- [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md)
- [PHASE_2_ACCEPTANCE.md](PHASE_2_ACCEPTANCE.md)
- [PHASE_3_ENGINEERING_SPEC.md](PHASE_3_ENGINEERING_SPEC.md)
- [SIONA_MODEL_GATEWAY.md](SIONA_MODEL_GATEWAY.md)
- [adr/0002-local-open-weight-transport.md](adr/0002-local-open-weight-transport.md)
- [PHASE_3B_HARDWARE_INVENTORY.md](PHASE_3B_HARDWARE_INVENTORY.md)
- [PHASE_3B_MODEL_INDEPENDENCE.md](PHASE_3B_MODEL_INDEPENDENCE.md)
- [PHASE_3B_MODEL_RUNTIME_RESEARCH.md](PHASE_3B_MODEL_RUNTIME_RESEARCH.md)
- [PHASE_3B_INSTALLATION_RUNBOOK.md](PHASE_3B_INSTALLATION_RUNBOOK.md)
- [adr/0003-first-local-model-strategy.md](adr/0003-first-local-model-strategy.md)

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

The optional local provider is **not** production-security certified.

## Phase 3B status (in progress)

Phase 3B remains **in progress**. The first runtime/model baseline has been
**installed and artifact-verified locally**. A **controlled real SIONA provider
text-path validation** (LanguageEngine → ModelGateway → LocalOpenWeightProvider
→ llama.cpp → Qwen) completed against the pinned runtime, then the runtime was
**stopped**. Gate E breadth evaluation is **recorded** (EXP-3B-011). Model
registry activation, capability approval, ADR acceptance, and Phase 3B
completion remain **pending** and are **not** issued.

### Completed (local operator evidence, 2026-08-05)

- Owner baseline selection
- Read-only pre-install checks
- Runtime download and portable extraction (`llama.cpp` b9968)
- Runtime archive local SHA256 verification (**MATCH**, 18211732 bytes,
  `f98e6690faad6a8718451d420a63cbfde6c87028beae4e7f35a36a762730cefd`)
- Model download (`Qwen3-1.7B-Q4_K_M.gguf`)
- Model SHA256 verification (**MATCH**, 1282439264 bytes,
  `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`)
- Licence-copy preservation (MIT beside runtime; Apache-2.0 beside model)
- CPU-only loopback startup (`127.0.0.1:8080`, ctx 4096, threads 4, ngl 0)
- Basic health/model/chat probes (HTTP 200)
- Controlled normal non-force shutdown
- Rollback-friendly portable layout (outside Git)
- Controlled real-provider validation (EXP-3B-005): exact model-ID verify;
  direct provider text probe; LanguageEngine end-to-end; tool proposals absent;
  deterministic fallback after shutdown; offline tests/eval/smoke green
- Governed prompt-context bridge (EXP-3B-006): merged on main; opt-in assembler
  validated against deterministic providers only
- First approved public identity registry (EXP-3B-007): three owner-approved
  records; explicit `GovernedContextInput` selection only; no automatic injection;
  no model training; no embeddings; no model registry activation. See
  [SIONA_APPROVED_IDENTITY_REGISTRY.md](SIONA_APPROVED_IDENTITY_REGISTRY.md).

### Still pending

- Operator-controlled model runtime startup (registry state C)
- ADR 0003 acceptance
- Phase 3B completion decision

### Current runtime state

- Runtime currently **stopped**
- Port 8080 currently **not listening**
- Capabilities beyond EXP-3B-011 Gate E results and EXP-3B-012 conservative binding remain limited to verified chat at 4096 context
- ADR 0003 remains **Proposed**
- Model registry: record available and binding software supported (EXP-3B-012); model registry runtime remains **inactive** (state C — llama.cpp not started)

Phase 3B is **not** completed. Phase 3 overall remains **in progress**.
Phase 4 remains **not started**.

## Known limitations

- Optional local provider requires explicitly configured endpoint **and** model ID
- Provider is **not** claimed production-secure
- Synchronous urllib transport does **not** support mid-request cancellation
  (pre-network cancel only; mid-request cancel deferred to async transport)
- Artefact verification is separate from behavioural capability verification
- Default Front Door path remains the legacy dummy provider unless opted in
- `openai_chat` dialect is opt-in via `SSN_LOCAL_MODEL_API_DIALECT`; default
  remains `siona_generate` for CI mock compatibility
- Owner-adjacent baseline failures remain technical debt
- Preferred pre-inference free-RAM target is 6–8 GiB; measured free RAM may be lower

## Next

Phase 3B: ADR 0003 acceptance; operator-controlled runtime activation (state C); Phase 3B
completion decision (still optional; CI remains deterministic and model-free).
EXP-3B-011 Gate E breadth is recorded. EXP-3B-010 guarded-path retest
acceptance was met; identity-guard model-native JSON remains unverified.
Phase 3B is **not** complete. Phase 4 remains **not started**.
