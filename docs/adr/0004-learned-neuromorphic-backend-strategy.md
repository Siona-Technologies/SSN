# ADR 0004 — Learned neuromorphic backend strategy

## Status

Accepted (Phase 4)

## Context

SIONA's hybrid architecture intentionally separates deliberative foundation-model
reasoning from a neuromorphic layer responsible for bounded temporal processing,
salience, novelty, anomaly and reflex **proposals**.

Phase 3 accepted the first real optional local foundation-model path. Phase 4
then evaluated whether SIONA could add its first genuine learned neuromorphic
component without weakening deterministic policy, fallback, model separation or
physical-safety boundaries.

`DEFERRED_CAPABILITIES.md` records SNN training and GPU benchmarking as separate
capability claims. The current accepted Phase 4 evidence is CPU-only software
SNN evidence; no CUDA/GPU or neuromorphic-silicon claim is implied.

## Decision

SIONA accepts a **replaceable learned software SNN provider** behind the existing
neuromorphic-provider boundary.

The accepted provider:

- solves the bounded `phase4a-temporal-salience-v1` temporal salience task;
- uses the governed artifact `phase4b-lif-final-membrane-v1`;
- remains advisory only;
- produces learned salience/classification signals rather than authorization;
- loads only from the SHA-verified canonical artifact;
- preserves the deterministic/reference provider as default/fallback;
- has a standard-library-only runtime implementation;
- remains independent of Qwen and the local language-model registry;
- grants no tool or physical-actuator authority.

The learned provider is explicit opt-in. This ADR does not make it the global
default neuromorphic backend.

## Accepted evidence

### EXP-4-001 — readiness

- existing neuromorphic contract audited;
- deterministic synthetic temporal task defined;
- train/validation/test split fingerprints frozen;
- private/user/company/website data excluded;
- predeclared acceptance thresholds recorded before training.

### EXP-4-003 — first controlled CPU training

Decision: `FIRST_CPU_SNN_TRAINING_VERIFIED`.

- exactly one controlled training run;
- CPython 3.11.9 x64;
- PyTorch 2.13.0+cpu;
- snnTorch 1.0.0;
- CUDA unavailable/unused;
- test balanced accuracy 1.0;
- class-0 recall 1.0;
- class-1 recall 1.0;
- baseline margin 0.5;
- time-reversal positive-score drop about 0.99943;
- canonical learned artifact SHA-256:
  `dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc`.

### EXP-4-004 — provider integration/parity

Decision: `LEARNED_SNN_PROVIDER_PARITY_VERIFIED`.

- pure-Python learned provider integrated behind existing contract;
- no torch/snnTorch/numpy runtime dependency;
- deterministic fallback retained;
- 197/197 parity samples agreed in predicted class;
- logit/probability differences remained within frozen tolerance;
- no training occurred in the parity experiment;
- Qwen and model registry remained unchanged.

### EXP-4-005 — breadth/safety/integrity

Decision: `PHASE4_LEARNED_SNN_BREADTH_SAFETY_VERIFIED`.

- in-memory artifact injection removed;
- artifact bytes SHA-verified before execution;
- 256 KiB bounded artifact read;
- strict 20x8 learned-event envelope;
- batch size bounded to 256;
- malformed learned batches fail atomically;
- 128/128 frozen held-out samples remained correct;
- class recalls remained 1.0/1.0;
- 64 reversed-positive samples retained strong temporal sensitivity;
- edge, malformed-input, fallback and corrupted-artifact matrices passed;
- tool executions 0;
- learned reflex proposals 0;
- physical authority false;
- Qwen calls 0;
- training calls 0.

## Accepted capability boundary

The accepted Phase 4 learned component may provide:

- temporal salience score;
- binary temporal classification;
- attention trigger;
- bounded learned probabilities;
- software LIF spike-count metadata where computed.

It does **not** gain:

- tool execution authority;
- policy authority;
- owner authority;
- memory mutation authority;
- external side-effect authority;
- physical actuation authority;
- robotics/vehicle/drone/IoT authority;
- language-model authority.

## Training-data boundary

The accepted training run used only the governed deterministic synthetic task.
Private identity records, contacts, customer data, website content, user memory,
secrets and unrelated personal/project material were not used. Qwen-generated
pseudo-labels were not used.

## Hardware boundary

The accepted evidence is **CPU-only software SNN** evidence.

Not verified or claimed by this ADR:

- CUDA/GPU training;
- GPU inference acceleration;
- measured hardware energy efficiency;
- Loihi;
- FPGA;
- neuromorphic silicon;
- event-camera hardware execution.

Future hardware evidence must be recorded separately and may not be inferred
from the Phase 4 CPU results.

## Dependency/runtime boundary

The training environment used PyTorch/snnTorch in an isolated operator-local
venv. Normal SIONA learned-provider runtime and hosted CI remain free of
PyTorch/snnTorch/numpy dependencies for this provider.

The project-wide `requirements.txt` remains unchanged by the learned SNN runtime.

## Alternatives considered

| Alternative | Disposition |
|---|---|
| Keep deterministic neuromorphic provider only | Retained as default/fallback, but no longer the only provider |
| Make the whole SIONA brain an SNN | Rejected; contradicts hybrid architecture and evidence |
| Fine-tune Qwen instead | Deferred; separate language-model adaptation/data-governance decision |
| Start robotics/IoT next | Deferred; physical safety remains separately gated |
| Require CUDA before learned SNN work | Rejected; CPU proof was sufficient for software architecture acceptance |
| Use private/user identity data | Rejected for the accepted task |

## Acceptance conditions disposition

1. Exact task/metrics/thresholds recorded before training — **satisfied**.
2. Reproducible dataset/generator provenance and splits — **satisfied**.
3. Backend/version/licence recorded — **satisfied**.
4. Real learned checkpoint produced by authorized run — **satisfied**.
5. Artifact checksum/metadata recorded — **satisfied**.
6. Held-out performance exceeds declared baseline — **satisfied**.
7. Learned inference works through existing provider boundary — **satisfied**.
8. Deterministic fallback remains intact — **satisfied**.
9. Hosted CI remains deterministic and does not train — **satisfied**.
10. No tool/actuator/owner authority granted — **satisfied**.
11. No unapproved/private training data used — **satisfied**.
12. CPU and future GPU claims remain separate — **satisfied**.
13. Qwen registry capabilities remain unchanged — **satisfied**.

## Consequences

- SIONA now has its first genuine learned neuromorphic software component.
- The deterministic provider remains the default/reference/fallback path.
- The accepted learned checkpoint is a governed SIONA-produced artifact for a
  bounded task.
- This does not make the external Qwen language model SIONA-native.
- This does not constitute production-security certification.
- Phase 4 is complete for its defined learned-neuromorphic software scope.
- Future SNN tasks, asynchronous/event-stream stateful execution, hardware
  acceleration, neuromorphic silicon, language-model adapters and physical
  embodiment require separate later decisions.

## Non-authorization

This Accepted ADR does not authorize:

- Qwen fine-tuning, LoRA, QLoRA or PEFT;
- a SIONA-native foundation-language-model claim;
- CUDA/GPU or energy claims without separate evidence;
- physical actuation;
- robotics/IoT integration;
- automatic promotion of the learned provider to global default;
- production certification;
- Phase 5 implementation without a separate planning decision.

## References

- [PHASE_4_ENGINEERING_SPEC.md](../PHASE_4_ENGINEERING_SPEC.md)
- [PHASE_4_ACCEPTANCE.md](../PHASE_4_ACCEPTANCE.md)
- [SIONA_PHASE_4A_NEUROMORPHIC_READINESS.md](../SIONA_PHASE_4A_NEUROMORPHIC_READINESS.md)
- [SIONA_PHASE_4B_FIRST_CPU_SNN_TRAINING.md](../SIONA_PHASE_4B_FIRST_CPU_SNN_TRAINING.md)
- [SIONA_PHASE_4C_LEARNED_PROVIDER_INTEGRATION.md](../SIONA_PHASE_4C_LEARNED_PROVIDER_INTEGRATION.md)
- [SIONA_PHASE_4D_BREADTH_SAFETY_GATE.md](../SIONA_PHASE_4D_BREADTH_SAFETY_GATE.md)
- [SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md](../SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md)
- [DEFERRED_CAPABILITIES.md](../DEFERRED_CAPABILITIES.md)
- [SIONA_VISION_CHARTER.md](../SIONA_VISION_CHARTER.md)
