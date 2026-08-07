# Phase 4 Planning Acceptance

**Status:** Accepted planning gate  
**Decision date:** 2026-08-07  
**Planning base:** `e93ec65297e1b29415f20cd28a4b591f4135fcb0`  
**Implementation status:** Not started  
**Authorized next scope:** Phase 4A research / contract / task / dataset / dependency governance only

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
modality without conflating it with:

- language-model fine-tuning;
- private memory training;
- voice/UI work;
- robotics or IoT;
- production database migration;
- physical actuation.

## Phase 4A authorization

After this planning gate is merged, **Phase 4A only** is authorized:

- read-only audit of the current neuromorphic provider contract;
- selection/definition of the first bounded learned task;
- synthetic/public dataset governance and deterministic split design;
- candidate backend research (for example snnTorch / Norse) from official
  sources;
- version/licence/dependency review;
- predeclared metrics and acceptance-threshold design;
- checkpoint metadata/provenance schema design;
- deterministic/offline test scaffolding that does not require training.

## Not yet authorized by this planning gate

A real SNN training run is **not yet authorized**.

Before the first training run, Phase 4A must produce an execution-ready record
containing:

- exact task definition;
- exact dataset/generator and licence/provenance;
- exact backend/version and dependencies;
- deterministic seed/split procedure;
- model topology/configuration;
- loss/optimizer/training limits;
- evaluation metrics;
- predeclared naive/random baseline;
- minimum acceptance margin;
- artifact/checkpoint output path policy;
- rollback/cleanup procedure.

The first real training execution is a separate controlled transition.

## Explicit exclusions

This planning acceptance does not authorize:

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
- Phase 4 implementation: **Not Started**
- Phase 4A: **Authorized for planning/research/scaffolding**
- ADR 0004: **Proposed**
- First real Phase 4 training run: **Not Authorized Yet**

## Related documents

- [PHASE_4_ENGINEERING_SPEC.md](PHASE_4_ENGINEERING_SPEC.md)
- [adr/0004-learned-neuromorphic-backend-strategy.md](adr/0004-learned-neuromorphic-backend-strategy.md)
- [SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md](SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md)
- [DEFERRED_CAPABILITIES.md](DEFERRED_CAPABILITIES.md)
- [SIONA_PHASE_ROADMAP.md](SIONA_PHASE_ROADMAP.md)
