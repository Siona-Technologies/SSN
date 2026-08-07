# Phase Status

| Field | Value |
|-------|--------|
| Phase 1 | **Completed and hardened** (`183fa70`) |
| Phase 2 | **Completed and hardened** (accepted gate `7b92114`; merged `19b3b13`) |
| Phase 3 | **Completed — Phase 3A accepted; Phase 3B accepted under ADR 0003 conservative local-model architecture** |
| Phase 3A | **Completed and hosted-CI accepted** (`d6c17d0`; merged `2e6abb6`) |
| Phase 3B | **Completed and accepted — baseline installed/verified; `openai_chat` dialect implemented; controlled real-provider text path validated; governed prompt-context bridge and approved identity registry merged; governed response guard hardened; real-Qwen guarded retest passed; Gate E breadth recorded; conservative model registry activated at the metadata/binding layer; State C registry-bound real-runtime verification passed and runtime shut down; ADR 0003 Accepted (Phase 3B)** |
| Phase 3B accepted evidence baseline | `1e1237e1a635dda52a0868a080a84623c74950ec` |
| Phase 3A PR | [#2](https://github.com/Siona-Technologies/SSN/pull/2) |
| Phase 4 | **In progress — planning gate accepted; Phase 4A readiness (EXP-4-001) and Phase 4B gate merged; EXP-4-003 first CPU SNN training VERIFIED; learned-provider integration / Phase 4 completion still pending** |
| Phase 4 architecture decision | ADR 0004 **Proposed** |
| Current machine | Intel i7-1165G7, Iris Xe, no CUDA GPU |

Historical note: immediately before Phase 3 closeout, Phase 3B was recorded as **In progress**. That historical wording is superseded by the accepted status above. Phase 4 learned-provider integration has not completed; EXP-4-003 verified a candidate training artifact only.

## Governing documents

- [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md)
- [PHASE_2_ACCEPTANCE.md](PHASE_2_ACCEPTANCE.md)
- [PHASE_3B_ACCEPTANCE.md](PHASE_3B_ACCEPTANCE.md)
- [PHASE_3_ENGINEERING_SPEC.md](PHASE_3_ENGINEERING_SPEC.md)
- [PHASE_4_ENGINEERING_SPEC.md](PHASE_4_ENGINEERING_SPEC.md)
- [PHASE_4_PLANNING_ACCEPTANCE.md](PHASE_4_PLANNING_ACCEPTANCE.md)
- [SIONA_PHASE_4A_NEUROMORPHIC_READINESS.md](SIONA_PHASE_4A_NEUROMORPHIC_READINESS.md)
- [PHASE_4B_FIRST_CPU_SNN_TRAINING_GATE.md](PHASE_4B_FIRST_CPU_SNN_TRAINING_GATE.md)
- [SIONA_PHASE_4B_FIRST_CPU_SNN_TRAINING.md](SIONA_PHASE_4B_FIRST_CPU_SNN_TRAINING.md)
- [SIONA_MODEL_GATEWAY.md](SIONA_MODEL_GATEWAY.md)
- [SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md](SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md)
- [adr/0002-local-open-weight-transport.md](adr/0002-local-open-weight-transport.md)
- [adr/0003-first-local-model-strategy.md](adr/0003-first-local-model-strategy.md)
- [adr/0004-learned-neuromorphic-backend-strategy.md](adr/0004-learned-neuromorphic-backend-strategy.md)
- [PHASE_3B_HARDWARE_INVENTORY.md](PHASE_3B_HARDWARE_INVENTORY.md)
- [PHASE_3B_MODEL_INDEPENDENCE.md](PHASE_3B_MODEL_INDEPENDENCE.md)
- [PHASE_3B_MODEL_RUNTIME_RESEARCH.md](PHASE_3B_MODEL_RUNTIME_RESEARCH.md)
- [PHASE_3B_INSTALLATION_RUNBOOK.md](PHASE_3B_INSTALLATION_RUNBOOK.md)
- [SIONA_STATE_C_REGISTRY_BOUND_RUNTIME_VERIFICATION.md](SIONA_STATE_C_REGISTRY_BOUND_RUNTIME_VERIFICATION.md)

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

## Phase 3B status (completed and accepted)

Phase 3B is **completed**. The first runtime/model baseline was installed and
artifact-verified locally. A controlled real SIONA provider text-path validation
(LanguageEngine → ModelGateway → LocalOpenWeightProvider → llama.cpp → Qwen)
completed against the pinned runtime, then the runtime was stopped. Gate E
breadth evaluation is recorded (EXP-3B-011). Model-registry activation review
passed with conservative capability binding (EXP-3B-012). State C controlled
registry-bound real-runtime verification passed (EXP-3B-013): pinned
llama.cpp/Qwen started on loopback only, the exact registry entry was bound
through `build_local_provider_from_env()`, real bounded text responses were
received without tools or deterministic fallback, and the runtime was shut down.

ADR 0003 is **Accepted (Phase 3B)**. The acceptance is deliberately conservative
and does not promote unsupported or unverified capabilities.

### Completed evidence chain

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
- Governed prompt-context bridge (EXP-3B-006)
- First approved public identity registry (EXP-3B-007): three owner-approved
  records; explicit `GovernedContextInput` selection only; no automatic injection
- Controlled real-Qwen identity campaign (EXP-3B-008), with observed failures
  retained honestly and used to drive response hardening
- Governed identity response guard (EXP-3B-009)
- Controlled real-Qwen guarded-path retest (EXP-3B-010): all 21 final guarded
  responses passed; native structured JSON remained unverified
- Gate E breadth (EXP-3B-011): governed safety 8/8; required runtime checks
  recorded; streaming unsupported on pinned baseline; native JSON not verified
- Model-registry activation review (EXP-3B-012): canonical manifest and exact
  provider/model binding with conservative capabilities
- State C (EXP-3B-013): `STATE_C_VERIFIED`; A/B/C/D/E independently recomputed
  from committed evidence; runtime stopped afterward; deterministic fallback
  remained available

### Accepted capability distinctions

- Bounded text/chat: conservatively verified at 4096 context (`chat=true`)
- Native JSON / `structured_json`: evaluated, `NOT_VERIFIED`, disabled
- Streaming: evaluated, `UNSUPPORTED_ON_PINNED_BASELINE`, disabled
- Tools: disabled; no model tool authority
- Multimodal: unverified/disabled
- `siona_native=false`: the Qwen weights remain external and replaceable

The six retained Gate E JSON outputs passed exact parsing/schema validation, but
this remains separate from native-provider JSON capability verification.

### Current runtime state

- Runtime currently **stopped**
- Port 8080 currently **not listening**
- Steady-state model runtime remains inactive; State C did not create automatic
  or permanent startup
- Deterministic CI remains model-free
- Model registry capabilities remain conservative and unchanged

Phase 3B is **complete**. With Phase 3A and Phase 3B both accepted, Phase 3 is
**complete for its defined local-model/evaluation scope**.

Phase 4 remains **not started** at the learned-provider integration and Phase 4 completion level. Its planning gate is accepted, EXP-4-001 defines Phase 4A readiness, the Phase 4B gate authorized one controlled CPU training run, and EXP-4-003 recorded `FIRST_CPU_SNN_TRAINING_VERIFIED`. Learned-provider integration, ADR 0004 acceptance, and Phase 4 completion remain pending.

## Phase 4 status

Phase 4 planning is **accepted** as **Learned Neuromorphic Backend & Evaluation**.
ADR 0004 remains **Proposed**.

EXP-4-001 completed the model-free readiness work:

- current neuromorphic contract/reference audit;
- deterministic `phase4a-temporal-salience-v1` task;
- frozen train/validation/test fingerprints;
- official-source backend research;
- predeclared metrics/baseline/acceptance thresholds;
- model-free test scaffolding;
- snnTorch 1.0.0 preferred for the next dependency gate only.

The Phase 4B training gate freezes:

- CPython 3.11 x64;
- PyTorch 2.13.0+cpu from the official CPU index;
- snnTorch 1.0.0 from PyPI;
- isolated venv outside Git;
- architecture `phase4b-lif-final-membrane-v1`;
- training seed/configuration and a 600-second hard wall-clock cap;
- one held-out test evaluation;
- immutable acceptance thresholds;
- candidate artifact and evidence policy.

**Authorization effect:** the Phase 4B training gate merged green and authorized one controlled **EXP-4-003 CPU SNN training/evaluation run**. That run executed once and decided `FIRST_CPU_SNN_TRAINING_VERIFIED`. See [SIONA_PHASE_4B_FIRST_CPU_SNN_TRAINING.md](SIONA_PHASE_4B_FIRST_CPU_SNN_TRAINING.md) and `docs/evidence/EXP-4-003_FIRST_CPU_SNN_TRAINING.json`.

Still not authorized by the training gate alone:

- CUDA/GPU training or claims;
- repeated/tuned training after a metric failure without a new record;
- Qwen fine-tuning/adapters;
- learned-provider runtime integration;
- ADR 0004 acceptance;
- physical actuation/robotics/IoT;
- semantic/vector memory migration;
- voice/SIBONA implementation.

## Known limitations carried forward

- Optional local Qwen provider requires explicitly configured endpoint **and** model ID
- Qwen provider is **not** claimed production-secure
- Synchronous urllib transport does **not** support mid-request cancellation
  (pre-network cancel only; mid-request cancel deferred to async transport)
- Artefact verification is separate from behavioural capability verification
- Default Front Door path remains the legacy dummy provider unless opted in
- `openai_chat` dialect is opt-in via `SSN_LOCAL_MODEL_API_DIALECT`; default
  remains `siona_generate` for CI mock compatibility
- Owner-adjacent baseline failures remain technical debt
- Preferred pre-inference free-RAM target is 6–8 GiB; measured free RAM may be lower
- Broader adversarial/security hardening beyond Gate E remains future
  production-certification work
- Current machine has no CUDA GPU; GPU SNN evidence remains hardware-gated
- A verified EXP-4-003 candidate JSON exists under `artifacts/neuromorphic/`; learned-provider integration and fallback/parity verification are still pending

## Next

The next controlled Phase 4 blocker is **LEARNED SNN PROVIDER INTEGRATION + FALLBACK/PARITY VERIFICATION**. Do not accept ADR 0004 or mark Phase 4 complete until that work is separately authorized and evidenced.

Phase 4 work must not reinterpret Phase 3B acceptance as permission to:

- start Qwen automatically;
- promote tools/structured JSON/streaming/multimodal capabilities;
- claim the external Qwen baseline is SIONA-native;
- begin Qwen/model adapter training without a separate approved plan.
