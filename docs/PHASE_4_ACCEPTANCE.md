# Phase 4 Acceptance Record — Learned Neuromorphic Backend

**Status:** Accepted  
**Decision date:** 2026-08-07  
**Accepted evidence baseline:** `05de2b04279a72ece4834a984461a505de1188b3`  
**Architecture decision:** ADR 0004 — Accepted (Phase 4)

## Decision

Phase 4 is accepted for its bounded objective: SIONA now has a real learned
software SNN provider behind the existing neuromorphic-provider boundary for the
`phase4a-temporal-salience-v1` task.

The accepted provider is:

- provider ID: `siona-neuro-learned-lif-v1`;
- architecture: `phase4b-lif-final-membrane-v1`;
- input modality: `temporal_salience_v1`;
- input shape: 20 timesteps × 8 binary event channels;
- trained artifact: `artifacts/neuromorphic/phase4b-lif-final-membrane-v1.json`;
- artifact SHA-256: `dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc`;
- training backend: PyTorch 2.13.0+cpu + snnTorch 1.0.0;
- accepted runtime implementation: dependency-free pure Python inference;
- normal/default neuromorphic provider: unchanged deterministic reference;
- learned-provider activation: explicit, not global/default.

## Accepted evidence chain

| Evidence | Result |
|---|---|
| EXP-4-001 | Neuromorphic contract/task/data readiness defined; no training |
| Phase 4B training gate | Exact CPU environment, topology, seed, training recipe and thresholds frozen before training |
| EXP-4-003 | `FIRST_CPU_SNN_TRAINING_VERIFIED`; exactly one CPU training run; held-out balanced accuracy 1.0; recalls 1.0/1.0; temporal reversal control passed |
| EXP-4-004 | `LEARNED_SNN_PROVIDER_PARITY_VERIFIED`; pure-Python provider matched snnTorch reference across 197/197 samples within frozen tolerances |
| EXP-4-005 | `PHASE4_LEARNED_SNN_BREADTH_SAFETY_VERIFIED`; strict artifact/input/batch safety, 128/128 frozen test inference, fallback and corruption matrices passed |

## ADR 0004 acceptance conditions

All required ADR 0004 acceptance conditions are satisfied:

1. Task and metrics were frozen before training — **satisfied**.
2. Dataset generator/splits are reproducible and fingerprinted — **satisfied**.
3. Backend/version/licence are recorded — **satisfied**.
4. A real learned checkpoint/artifact was produced by an authorized training run — **satisfied**.
5. Artifact checksum and metadata are recorded — **satisfied**.
6. Held-out performance exceeded the predeclared baseline/margin — **satisfied**.
7. Learned inference works through the existing neuromorphic-provider boundary — **satisfied**.
8. Deterministic fallback remains intact — **satisfied**.
9. Hosted CI remains deterministic/model-free and does not train — **satisfied**.
10. No tool, actuator or owner authority is granted to the SNN — **satisfied**.
11. No private/unapproved training data was used — **satisfied**.
12. CPU evidence is explicitly separated from future GPU evidence — **satisfied**.
13. Qwen/model-registry capabilities remain unchanged — **satisfied**.

## Accepted behavioral evidence

The accepted claims are deliberately bounded:

- frozen held-out test: 128/128 correct;
- balanced accuracy: 1.0;
- class-0 recall: 1.0;
- class-1 recall: 1.0;
- 64 reversed-positive temporal controls;
- mean original positive score ≈ 0.99943266;
- mean reversed positive score ≈ 0.000000167;
- mean temporal score drop ≈ 0.99943249;
- EXP-4-004 parity set: 197/197 class and spike-count agreement;
- EXP-4-005 valid edge controls: 9/9;
- malformed learned inputs: fail closed;
- corrupted artifacts: rejected before inference;
- unsupported modalities: deterministic fallback with explicit metadata;
- maximum learned batch: 256 events;
- artifact maximum: 256 KiB with bounded read;
- runtime training-stack dependencies: none.

## Security and authority boundaries

The accepted learned SNN may provide:

- temporal classification;
- bounded salience score;
- attention trigger;
- actual software-LIF spike count.

It does not receive authority for:

- tool execution;
- policy decisions;
- memory mutation;
- owner actions;
- external side effects;
- physical actuation;
- robotics, vehicle, drone or IoT control.

The learned path emits no reflex proposal in the accepted task.

## Explicit non-claims

Phase 4 acceptance does **not** claim or authorize:

- asynchronous neuromorphic-silicon execution;
- Loihi/FPGA deployment;
- CUDA/GPU SNN training or benchmarking;
- measured energy efficiency (`energy_metrics=false`; compatibility `energy=0.0` is not a measurement);
- event-by-event persistent/stateful streaming SNN inference;
- real event-camera input;
- anomaly/novelty learning beyond the accepted task;
- arbitrary SNN tasks or general intelligence from this checkpoint;
- making the learned provider the global/default provider;
- Qwen capability expansion;
- Qwen LoRA/QLoRA/PEFT/fine-tuning;
- a SIONA-native foundation language model;
- robotics/IoT/physical actuation;
- production-security certification.

The accepted artifact is a **SIONA-trained learned neuromorphic software
artifact**, not a claim that the external Qwen foundation weights are
SIONA-native.

## Runtime/dependency disposition

The training environment remains isolated from normal SIONA runtime and hosted
CI. The normal learned-provider implementation uses Python standard-library
math and the verified JSON artifact; it does not require torch, snnTorch, numpy
or Norse at runtime.

The deterministic/reference provider remains the default and fallback.

## Phase decision

**ADR 0004 is Accepted (Phase 4).**

**Phase 4 is COMPLETE** for its defined learned-neuromorphic software-provider
scope.

Completion does not automatically start another phase. The next phase/objective
must be selected through a separate governed planning decision rather than being
inferred from older historical phase numbering.

## Related records

- [PHASE_4_ENGINEERING_SPEC.md](PHASE_4_ENGINEERING_SPEC.md)
- [PHASE_4_PLANNING_ACCEPTANCE.md](PHASE_4_PLANNING_ACCEPTANCE.md)
- [SIONA_PHASE_4A_NEUROMORPHIC_READINESS.md](SIONA_PHASE_4A_NEUROMORPHIC_READINESS.md)
- [PHASE_4B_FIRST_CPU_SNN_TRAINING_GATE.md](PHASE_4B_FIRST_CPU_SNN_TRAINING_GATE.md)
- [SIONA_PHASE_4B_FIRST_CPU_SNN_TRAINING.md](SIONA_PHASE_4B_FIRST_CPU_SNN_TRAINING.md)
- [SIONA_PHASE_4C_LEARNED_PROVIDER_INTEGRATION.md](SIONA_PHASE_4C_LEARNED_PROVIDER_INTEGRATION.md)
- [SIONA_PHASE_4D_BREADTH_SAFETY_GATE.md](SIONA_PHASE_4D_BREADTH_SAFETY_GATE.md)
- [adr/0004-learned-neuromorphic-backend-strategy.md](adr/0004-learned-neuromorphic-backend-strategy.md)
