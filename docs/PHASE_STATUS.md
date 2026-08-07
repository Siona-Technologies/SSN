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
| Phase 4 | **Completed and accepted — first governed learned software SNN trained, integrated, parity-verified and breadth/safety-verified; ADR 0004 Accepted (Phase 4)** |
| Phase 4 accepted evidence baseline | `05de2b04279a72ece4834a984461a505de1188b3` |
| Phase 4 architecture decision | ADR 0004 **Accepted (Phase 4)** |
| Phase 5 | **Not started — requires a separate governed planning decision** |
| Current machine | Intel i7-1165G7, Iris Xe, no CUDA GPU |

Historical note: immediately before Phase 4 closeout, Phase 4 was **In progress** and ADR 0004 was **Proposed**. EXP-4-005 removed the final breadth/safety blocker. The accepted current state is Phase 4 complete and ADR 0004 Accepted (Phase 4). Phase 5 remains **not started**.

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
- [adr/0003-first-local-model-strategy.md](adr/0003-first-local-model-strategy.md)
- [adr/0004-learned-neuromorphic-backend-strategy.md](adr/0004-learned-neuromorphic-backend-strategy.md)

## Phase 3A status (completed)

Phase 3A is **completed, hardened, hosted-CI accepted and merged**.

- Accepted feature SHA: `d6c17d0d723ef309cca1f8edf3fb467b12d04d2a`
- Merge commit: `2e6abb6d70f4204bb4f9e479e081b0a9fc116580`
- PR: [#2](https://github.com/Siona-Technologies/SSN/pull/2)
- Hosted CI: Python 3.11/3.12 green; production evaluation 7/7; HTTP smoke passed.

Delivered in Phase 3A:

- centralized runtime-data isolation;
- optional `LocalOpenWeightProvider` behind `ModelProvider`;
- provider-boundary sanitization and local transport hardening;
- conservative capability reporting;
- model registry/evaluation scaffolding;
- loopback-only mock model tests.

## Phase 3B status (completed and accepted)

Phase 3B is **completed**. The first runtime/model baseline was installed and
artifact-verified locally. Controlled real-provider validation, governed context,
approved identity registry, response hardening, Gate E, model-registry binding,
and State C all completed.

ADR 0003 is **Accepted (Phase 3B)**.

Accepted capability distinctions remain:

- `chat=true` at tested context 4096;
- `tools=false`;
- `structured_json=false` and native JSON remains `NOT_VERIFIED`;
- `streaming=false`, `UNSUPPORTED_ON_PINNED_BASELINE`;
- `multimodal=false`;
- `siona_native=false`.

The Qwen runtime remains optional and steady-state stopped; Phase 4 did not
change its registry or capabilities.

## Phase 4 status (completed and accepted)

Phase 4 is **complete** for the defined **Learned Neuromorphic Backend &
Evaluation** scope.

### EXP-4-001 — readiness

- current provider contract audited;
- deterministic `phase4a-temporal-salience-v1` task defined;
- deterministic train/validation/test fingerprints frozen;
- official-source backend research recorded;
- private/user/company/website data excluded;
- acceptance metrics locked before training.

### EXP-4-003 — first learned SNN training

Decision: `FIRST_CPU_SNN_TRAINING_VERIFIED`.

- exactly one controlled CPU training run;
- CPython 3.11.9 x64;
- PyTorch 2.13.0+cpu;
- snnTorch 1.0.0;
- CUDA false;
- 128/128 held-out test samples correct;
- balanced accuracy 1.0;
- class recalls 1.0/1.0;
- temporal time-reversal score drop about 0.99943;
- learned artifact SHA-256:
  `dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc`.

### EXP-4-004 — learned provider integration/parity

Decision: `LEARNED_SNN_PROVIDER_PARITY_VERIFIED`.

- explicit provider `siona-neuro-learned-lif-v1` integrated;
- deterministic provider remains default/fallback;
- pure-Python learned runtime, no torch/snnTorch/numpy requirement;
- 197/197 parity cases agreed in predicted class;
- no retraining;
- Qwen/model registry unchanged;
- tool and physical authority remained false.

### EXP-4-005 — breadth/safety/integrity

Decision: `PHASE4_LEARNED_SNN_BREADTH_SAFETY_VERIFIED`.

- arbitrary in-memory artifact injection removed;
- 256 KiB bounded artifact read;
- strict learned-event envelope;
- max learned batch 256;
- malformed learned batches reject atomically;
- 128/128 frozen held-out samples remain correct;
- 64 reversed positives retain strong temporal sensitivity;
- valid edge, malformed-input, fallback and corrupted-artifact matrices pass;
- network/subprocess/Qwen/training calls 0;
- tool execution 0;
- learned reflex proposals 0;
- physical authority false;
- energy metrics claim false.

### Accepted Phase 4 boundaries

The learned SNN may produce bounded temporal salience/classification signals and
attention triggers. It may not authorize tools, policy, memory mutations,
external actions or physical actuation.

The accepted evidence is CPU software-SNN evidence only. No CUDA/GPU, Loihi,
FPGA, measured energy-efficiency or neuromorphic-silicon claim is made.

Normal learned-provider runtime and hosted CI remain training-stack-free.

ADR 0004 is **Accepted (Phase 4)**.

## Known limitations carried forward

- Qwen remains external, replaceable and not production-security certified.
- Native Qwen JSON remains unverified and streaming unsupported on the pinned baseline.
- Current machine has no CUDA GPU; GPU SNN evidence remains hardware-gated.
- The learned SNN handles the bounded 20×8 temporal-salience task; it is not a
  general-purpose SNN brain.
- The current learned provider consumes complete temporal windows; true
  event-by-event asynchronous stateful learned execution is future work.
- No physical-safety kernel exists for real-world actuation.
- No SIONA language-model adapter or SIONA-native foundation model has been trained.

## Next

Phase 4 is closed. Phase 5 remains **not started**.

The next action is a **separate Phase 5 planning decision**. It must select one
bounded objective and must not automatically inherit old phase numbering or
unsequenced deferred capabilities.

Candidates that remain separate until Phase 5 planning include:

- streaming/event-by-event learned SNN execution;
- memory/vector backend expansion;
- language-model adaptation;
- voice/SIBONA embodiment;
- robotics/IoT/physical embodiment;
- GPU/neuromorphic-hardware benchmarking.
