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
| Phase 4 | **Completed and accepted — EXP-4-003 training VERIFIED; EXP-4-004 learned-provider parity VERIFIED; EXP-4-005 breadth/safety VERIFIED; ADR 0004 Accepted (Phase 4)** |
| Phase 4 accepted evidence baseline | `05de2b04279a72ece4834a984461a505de1188b3` |
| Phase 4 architecture decision | ADR 0004 **Accepted (Phase 4)** |
| Next phase | **Not started — requires a separate governed planning decision** |
| Current machine | Intel i7-1165G7, Iris Xe, no CUDA GPU |

Historical status preservation: immediately before Phase 3 closeout, Phase 3B
was **In progress**. During the Phase 3 closeout transition the authoritative
record also stated that Phase 4 remains **not started**. Later Phase 4 planning,
training, provider integration and breadth/safety evidence superseded that
historical current-state wording. Experiment records retain the governance state
that existed when each experiment ran and are not rewritten retroactively.

## Governing documents

- [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md)
- [PHASE_2_ACCEPTANCE.md](PHASE_2_ACCEPTANCE.md)
- [PHASE_3B_ACCEPTANCE.md](PHASE_3B_ACCEPTANCE.md)
- [PHASE_4_ACCEPTANCE.md](PHASE_4_ACCEPTANCE.md)
- [PHASE_3_ENGINEERING_SPEC.md](PHASE_3_ENGINEERING_SPEC.md)
- [PHASE_4_ENGINEERING_SPEC.md](PHASE_4_ENGINEERING_SPEC.md)
- [PHASE_4_PLANNING_ACCEPTANCE.md](PHASE_4_PLANNING_ACCEPTANCE.md)
- [SIONA_PHASE_4A_NEUROMORPHIC_READINESS.md](SIONA_PHASE_4A_NEUROMORPHIC_READINESS.md)
- [PHASE_4B_FIRST_CPU_SNN_TRAINING_GATE.md](PHASE_4B_FIRST_CPU_SNN_TRAINING_GATE.md)
- [SIONA_PHASE_4B_FIRST_CPU_SNN_TRAINING.md](SIONA_PHASE_4B_FIRST_CPU_SNN_TRAINING.md)
- [SIONA_PHASE_4C_LEARNED_PROVIDER_INTEGRATION.md](SIONA_PHASE_4C_LEARNED_PROVIDER_INTEGRATION.md)
- [SIONA_PHASE_4D_BREADTH_SAFETY_GATE.md](SIONA_PHASE_4D_BREADTH_SAFETY_GATE.md)
- [SIONA_MODEL_GATEWAY.md](SIONA_MODEL_GATEWAY.md)
- [SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md](SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md)
- [adr/0002-local-open-weight-transport.md](adr/0002-local-open-weight-transport.md)
- [adr/0003-first-local-model-strategy.md](adr/0003-first-local-model-strategy.md)
- [adr/0004-learned-neuromorphic-backend-strategy.md](adr/0004-learned-neuromorphic-backend-strategy.md)

## Phase 3A status (completed)

Phase 3A is **completed, hardened, hosted-CI accepted and merged**.

- Accepted feature SHA: `d6c17d0d723ef309cca1f8edf3fb467b12d04d2a`
- Merge commit: `2e6abb6d70f4204bb4f9e479e081b0a9fc116580`
- PR: [#2](https://github.com/Siona-Technologies/SSN/pull/2)

Hosted CI (PR #2): Python 3.11 and 3.12 accepted; production evaluation 7/7;
HTTP smoke passed.

Delivered in Phase 3A includes centralized runtime-data isolation, optional
`LocalOpenWeightProvider`, provider-boundary sanitization, conservative model
capability reporting, strict model-registry schema, deterministic evaluation and
loopback-only transport tests.

## Phase 3B status (completed and accepted)

Phase 3B is **complete**. The first real optional local language-model baseline
was installed, artifact-verified, exercised through SIONA's provider path and
then shut down. Gate E breadth, conservative model-registry activation and State
C exact registry-bound runtime verification were recorded.

ADR 0003 is **Accepted (Phase 3B)**.

Key evidence retained:

- EXP-3B-005 controlled real-provider text path;
- EXP-3B-011 Gate E breadth;
- EXP-3B-012 model-registry activation review;
- EXP-3B-013 `STATE_C_VERIFIED`.

Accepted Qwen capability distinctions remain:

- `chat=true` at context 4096;
- native JSON `NOT_VERIFIED`, therefore `structured_json=false`;
- streaming `UNSUPPORTED_ON_PINNED_BASELINE`, therefore `streaming=false`;
- `tools=false`;
- `multimodal=false`;
- `siona_native=false`.

The Qwen/llama runtime remains optional and is not automatically started.
Production certification is not claimed.

## Phase 4 status (completed and accepted)

Phase 4 is **complete** for its defined learned-neuromorphic software-provider
scope. ADR 0004 is **Accepted (Phase 4)**.

### Phase 4 evidence chain

- EXP-4-001 — model-free neuromorphic contract/task/data readiness;
- Phase 4B gate — frozen CPython/PyTorch/snnTorch environment, model topology,
  seed, training recipe and thresholds;
- EXP-4-003 — `FIRST_CPU_SNN_TRAINING_VERIFIED` from exactly one CPU training
  run;
- EXP-4-004 — `LEARNED_SNN_PROVIDER_PARITY_VERIFIED` across 197/197 reference
  parity samples;
- EXP-4-005 — `PHASE4_LEARNED_SNN_BREADTH_SAFETY_VERIFIED`.

### Accepted learned provider

- provider: `siona-neuro-learned-lif-v1`;
- task: `phase4a-temporal-salience-v1`;
- architecture: `phase4b-lif-final-membrane-v1`;
- learned input: 20 × 8 binary temporal sequence;
- artifact SHA-256:
  `dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc`;
- pure-Python runtime inference;
- no runtime torch/snnTorch/numpy/Norse dependency;
- explicit activation only;
- deterministic/reference provider remains default and fallback;
- tool authority false;
- physical actuation authority false;
- energy metrics false.

### Accepted behavior

- frozen held-out test: 128/128 correct;
- balanced accuracy 1.0;
- class recalls 1.0/1.0;
- 64 reversed-positive temporal controls with mean score drop ≈ 0.99943249;
- 9/9 valid edge controls;
- malformed learned inputs fail closed;
- corrupted learned artifacts fail before inference;
- unsupported modalities fall back deterministically;
- maximum learned batch 256;
- maximum learned artifact 256 KiB with bounded read.

### Phase 4 limitations carried forward

Phase 4 does not claim or authorize:

- CUDA/GPU SNN evidence;
- Loihi/FPGA/neuromorphic-silicon execution;
- measured energy efficiency;
- persistent event-by-event asynchronous/stateful streaming SNN inference;
- real event-camera input;
- making the learned provider globally default;
- Qwen fine-tuning/adapters;
- physical actuation/robotics/IoT;
- semantic/vector-memory migration;
- voice/SIBONA implementation;
- production-security certification.

The learned artifact is a SIONA-trained software SNN artifact; it does not make
external Qwen foundation weights SIONA-native.

## Known limitations carried forward

- Optional local Qwen provider requires explicitly configured endpoint and model ID.
- Qwen provider is not claimed production-secure.
- Synchronous urllib transport does not support mid-request cancellation.
- Artefact verification remains separate from broader production certification.
- Default Front Door path remains the legacy dummy provider unless opted in.
- Current machine has no CUDA GPU; GPU SNN evidence remains hardware-gated.
- The accepted SNN task is intentionally narrow and window-based, not persistent
  event-by-event asynchronous neuromorphic execution.

## Next

Phases 1–4 are complete for their defined scopes.

**No next phase has started.** The next objective must be selected through a
separate governed planning decision. Older historical documents must not be used
to infer or auto-start a new phase.

Phase 4 acceptance is not permission to start Qwen automatically, promote Qwen
optional capabilities, retrain either model, or grant learned-model tool or
physical authority.
