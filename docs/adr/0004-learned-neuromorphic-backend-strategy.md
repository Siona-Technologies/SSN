# ADR 0004 — Learned neuromorphic backend strategy

## Status

Accepted (Phase 4)

## Context

SIONA's hybrid architecture separates deliberative foundation-model reasoning
from a neuromorphic layer responsible for bounded temporal processing, salience,
novelty, anomaly and reflex **proposals**.

Phase 3 accepted the first real optional local foundation-model path. Phase 4
was created to establish the first genuine learned neuromorphic software
component without collapsing the whole intelligence architecture into an SNN or
granting learned outputs tool/actuator authority.

The development machine has no CUDA GPU, so Phase 4 deliberately separated a
reproducible CPU learned-provider proof from future hardware-gated GPU or
neuromorphic-silicon evidence.

## Decision

SIONA accepts a **replaceable learned software SNN provider** behind the existing
neuromorphic-provider boundary.

The accepted provider is:

- provider ID: `siona-neuro-learned-lif-v1`;
- task: `phase4a-temporal-salience-v1`;
- architecture: `phase4b-lif-final-membrane-v1`;
- input: explicit `temporal_salience_v1`, 20 × 8 binary temporal sequence;
- training: one authorized CPU run using PyTorch 2.13.0+cpu and snnTorch 1.0.0;
- accepted artifact: `artifacts/neuromorphic/phase4b-lif-final-membrane-v1.json`;
- artifact SHA-256: `dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc`;
- runtime inference: pure Python, no torch/snnTorch/numpy/Norse dependency;
- activation: explicit only;
- default/fallback: deterministic reference provider remains intact.

The learned SNN may produce bounded temporal classification, salience,
attention-trigger and software spike-count signals. Those outputs are advisory
signals, not authorization.

## Evidence basis

Phase 4 acceptance is supported by the governed evidence chain:

- **EXP-4-001** — contract/task/data readiness defined before training;
- **Phase 4B training gate** — environment, topology, seed, training recipe and
  thresholds frozen before execution;
- **EXP-4-003** — `FIRST_CPU_SNN_TRAINING_VERIFIED`; exactly one CPU training
  run; held-out balanced accuracy 1.0; class recalls 1.0/1.0; temporal reversal
  control passed;
- **EXP-4-004** — `LEARNED_SNN_PROVIDER_PARITY_VERIFIED`; pure-Python runtime
  matched snnTorch reference across 197/197 parity samples within frozen
  tolerances;
- **EXP-4-005** — `PHASE4_LEARNED_SNN_BREADTH_SAFETY_VERIFIED`; strict
  artifact/input/batch boundaries, full frozen-test inference, temporal breadth,
  fallback, corruption and authority checks passed.

See [PHASE_4_ACCEPTANCE.md](../PHASE_4_ACCEPTANCE.md).

## Acceptance conditions

All conditions defined while this ADR was Proposed are satisfied:

1. Exact learned task and predeclared metrics/thresholds recorded before training — **satisfied**.
2. Dataset/generator provenance and train/validation/test split reproducible — **satisfied**.
3. Backend/version/licence recorded — **satisfied**.
4. Real learned checkpoint/artifact produced from an authorized run — **satisfied**.
5. Artifact checksum and metadata recorded — **satisfied**.
6. Held-out performance exceeds predeclared baseline/margin — **satisfied**.
7. Learned inference works through the existing provider boundary — **satisfied**.
8. Deterministic fallback remains intact — **satisfied**.
9. Hosted CI remains deterministic and does not train — **satisfied**.
10. No tool/actuator/owner authority is granted — **satisfied**.
11. No unapproved/private training data was used — **satisfied**.
12. CPU evidence is separated from future GPU evidence — **satisfied**.
13. Qwen registry capabilities remain unchanged — **satisfied**.

## Training-data boundary

The accepted first task uses SIONA-controlled deterministic synthetic temporal
data with frozen split fingerprints. It uses no private identity records,
contacts, customer data, website content, user memory, secrets, unrelated
personal/project material or Qwen-generated labels.

Future learned tasks require their own dataset/provenance decisions.

## Authority boundary

The accepted learned SNN may influence:

- temporal classification;
- salience;
- attention prioritisation;
- bounded cognitive signals.

It may not directly authorize:

- tools;
- policy changes;
- owner actions;
- memory mutation;
- external side effects;
- physical actuators.

The accepted learned path emits no reflex proposal for this task.

## Safety/integrity boundary

The accepted runtime includes:

- SHA-verified canonical artifact bytes;
- 256 KiB bounded artifact loading;
- strict UTF-8 and duplicate-key rejection;
- exact task/provider/architecture/training identity;
- finite, shape-checked weights;
- strict 20 × 8 binary learned-event envelope;
- bounded non-empty event IDs;
- maximum learned batch size of 256;
- atomic prevalidation for claimed learned events;
- fail-closed malformed learned inputs;
- deterministic fallback for unsupported modalities;
- no in-memory artifact-injection bypass.

## Runtime and hardware boundary

The accepted runtime is a **software SNN**, not neuromorphic silicon.

Accepted claims:

- CPU-trained learned SNN artifact;
- pure-Python deterministic inference;
- software LIF spike execution;
- explicit provider integration and fallback.

Not accepted/verified by this ADR:

- CUDA/GPU SNN training or benchmarking;
- Loihi/FPGA execution;
- neuromorphic-silicon deployment;
- measured energy efficiency;
- event-by-event persistent/stateful streaming SNN inference;
- real event-camera input.

`energy_metrics=false`; compatibility `energy=0.0` is not a measured energy
claim.

## Relationship to the language model

The learned SNN is independent of the Phase 3 Qwen baseline. Phase 4 did not
change the Qwen model registry or capabilities and performed no Qwen
LoRA/QLoRA/PEFT/fine-tuning.

A SIONA-trained SNN artifact does not make the external Qwen foundation weights
SIONA-native.

## Alternatives considered

| Alternative | Disposition |
|---|---|
| Keep deterministic neuromorphic provider only | Retained as default/fallback, but insufficient as the sole Phase 4 outcome |
| Make the whole SIONA brain an SNN | Rejected; contradicts the hybrid architecture |
| Fine-tune Qwen instead | Deferred; separate dataset/training/ownership decision |
| Start robotics/IoT next | Deferred; physical safety and actuator authority remain separately gated |
| Require CUDA before any learned SNN work | Rejected; reproducible CPU proof was sufficient for this bounded software milestone |
| Use private/user identity data | Rejected for the accepted task |

## Consequences

- SIONA now has its first genuine learned neuromorphic software component.
- The deterministic provider remains the default/reference/fallback path.
- Normal hosted CI remains free of the training stack.
- The accepted learned provider remains explicit opt-in rather than global
  default.
- Future tasks, streaming semantics, hardware acceleration and physical
  embodiment can evolve behind existing contracts without rewriting higher-level
  cognitive architecture.

## Explicit non-authorization

This ADR does not authorize:

- production-security certification;
- a global/default learned provider switch;
- repeated or new SNN training without a new governed task/training decision;
- CUDA/GPU claims;
- Qwen fine-tuning/adapters;
- semantic/vector-memory migration;
- STT/TTS or SIBONA embodiment;
- robotics/IoT/vehicle/drone control;
- physical actuation;
- a SIONA-native foundation language-model claim.

## Phase disposition

ADR 0004 acceptance completes **Phase 4** for the defined learned-neuromorphic
software-provider scope.

No subsequent phase starts automatically. The next objective requires a separate
governed planning decision.

## References

- [PHASE_4_ACCEPTANCE.md](../PHASE_4_ACCEPTANCE.md)
- [PHASE_4_ENGINEERING_SPEC.md](../PHASE_4_ENGINEERING_SPEC.md)
- [SIONA_PHASE_4A_NEUROMORPHIC_READINESS.md](../SIONA_PHASE_4A_NEUROMORPHIC_READINESS.md)
- [PHASE_4B_FIRST_CPU_SNN_TRAINING_GATE.md](../PHASE_4B_FIRST_CPU_SNN_TRAINING_GATE.md)
- [SIONA_PHASE_4B_FIRST_CPU_SNN_TRAINING.md](../SIONA_PHASE_4B_FIRST_CPU_SNN_TRAINING.md)
- [SIONA_PHASE_4C_LEARNED_PROVIDER_INTEGRATION.md](../SIONA_PHASE_4C_LEARNED_PROVIDER_INTEGRATION.md)
- [SIONA_PHASE_4D_BREADTH_SAFETY_GATE.md](../SIONA_PHASE_4D_BREADTH_SAFETY_GATE.md)
- [SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md](../SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md)
- [SIONA_VISION_CHARTER.md](../SIONA_VISION_CHARTER.md)
