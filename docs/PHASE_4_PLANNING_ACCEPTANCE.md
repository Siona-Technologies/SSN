# Phase 4 Planning Acceptance

**Status:** Accepted planning gate  
**Decision date:** 2026-08-07  
**Planning base:** `e93ec65297e1b29415f20cd28a4b591f4135fcb0`  
**Implementation status:** Phase 4A readiness defined; learned-provider implementation/training not started  
**Authorized scope:** Phase 4A research / contract / task / dataset / dependency governance and model-free scaffolding only

## Decision

The Phase 4 planning direction is accepted as:

> **Learned Neuromorphic Backend & Evaluation** — establish SIONA's first real
> learned SNN provider for a bounded temporal salience/classification task while
> preserving deterministic fallback, model-free hosted CI, owner/policy authority,
> and strict separation from physical actuation.

This planning decision is based on the Vision Charter's hybrid architecture and
the existing `HW-SNN-001` / `HW-BENCH-001` deferred-capability records.

## Why this scope was selected

The accepted Phase 3 work made the deliberative language-model path real and
replaceable. The other major learned layer in the hybrid SIONA architecture is
the neuromorphic/SNN path, which is still deterministic/reference-only.

Advancing that layer now gives SIONA a second genuinely learned intelligence
modality without conflating it with language-model fine-tuning, private memory
training, voice/UI work, robotics/IoT, production database migration or physical
actuation.

## Phase 4A authorization and EXP-4-001

The planning gate authorized Phase 4A only:

- read-only audit of the current neuromorphic provider contract;
- selection/definition of the first bounded learned task;
- synthetic/public dataset governance and deterministic split design;
- candidate backend research from official sources;
- version/licence/dependency review;
- predeclared metrics and acceptance-threshold design;
- checkpoint metadata/provenance schema design;
- deterministic/offline test scaffolding that does not require training.

EXP-4-001 records that readiness work in
[SIONA_PHASE_4A_NEUROMORPHIC_READINESS.md](SIONA_PHASE_4A_NEUROMORPHIC_READINESS.md).
It defines the deterministic `phase4a-temporal-salience-v1` task and records
snnTorch 1.0.0 as the **preferred candidate for the next dependency gate**.
This is not an installation or training approval.

## Training remains a separate transition

A real SNN training run is **not yet authorized**.

Before the first training run, a separate dependency/training execution record
must pin:

- exact Python interpreter;
- exact CPU PyTorch version/build;
- exact SNN backend package/version and artifact provenance;
- deterministic seed/split procedure;
- exact model topology/readout;
- loss, optimizer and learning rate;
- epoch/time limits and early stopping;
- evaluation metrics and predeclared baseline/thresholds;
- artifact/checkpoint output path and checksum policy;
- rollback/cleanup procedure;
- resource preflight and evidence script.

The first real training execution remains a separately controlled transition.

## Explicit exclusions

This planning/readiness acceptance does not authorize:

- Qwen LoRA/QLoRA/PEFT or any language-model training;
- private identity/contact/customer/user-memory training data;
- automatic Qwen startup;
- Qwen capability expansion;
- semantic/vector memory migration;
- real STT/TTS;
- SIBONA implementation;
- MQTT/ROS2 physical integration;
- robotics/humanoid/vehicle/drone control;
- physical actuation;
- CUDA/GPU claims without actual verified hardware execution;
- Loihi/FPGA execution;
- production certification.

## Governance state

- Phase 3: **Complete**
- Phase 4 planning: **Accepted**
- Phase 4A readiness: **Defined by EXP-4-001**
- Learned SNN implementation/training: **Not Started**
- ADR 0004: **Proposed**
- First real Phase 4 training run: **Not Authorized Yet**
- Next gate: **separate dependency + first CPU SNN training authorization**

## Related documents

- [PHASE_4_ENGINEERING_SPEC.md](PHASE_4_ENGINEERING_SPEC.md)
- [SIONA_PHASE_4A_NEUROMORPHIC_READINESS.md](SIONA_PHASE_4A_NEUROMORPHIC_READINESS.md)
- [adr/0004-learned-neuromorphic-backend-strategy.md](adr/0004-learned-neuromorphic-backend-strategy.md)
- [SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md](SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md)
- [DEFERRED_CAPABILITIES.md](DEFERRED_CAPABILITIES.md)
- [SIONA_PHASE_ROADMAP.md](SIONA_PHASE_ROADMAP.md)
