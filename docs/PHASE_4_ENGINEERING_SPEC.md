# Phase 4 Engineering Specification — Learned Neuromorphic Backend

**Status:** Proposed planning gate — implementation not started  
**Phase 3 prerequisite:** Complete and accepted  
**Primary objective:** Replace the simulation-only neuromorphic path with the first **real learned SNN provider** for a bounded salience/temporal classification task, while preserving deterministic safety, replaceable providers, and model-free hosted CI.  
**Governing charter:** [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md)

---

## 1. Why this is the next phase

Phase 3 established the first real optional local foundation-model path. The
other major learned-intelligence layer in the SIONA hybrid architecture remains
neuromorphic/SNN processing: salience, novelty, temporal activity and reflex
**proposals**.

The repository already records:

- `HW-SNN-001` — CUDA-accelerated SNN training, target Phase 4;
- `HW-BENCH-001` — GPU benchmarking, target Phase 4;
- a replaceable neuromorphic provider abstraction;
- only a deterministic/reference neuromorphic provider as the current executable
  baseline.

Phase 4 therefore advances the hybrid architecture instead of adding a user
interface feature or prematurely fine-tuning the language model.

---

## 2. Phase 4 objective

Deliver and validate the first **learned neuromorphic provider** behind the
existing SIONA neuromorphic-provider contract.

The first learned task must remain intentionally narrow:

> Given a bounded temporal event sequence, produce a learned salience / temporal
> classification result and associated bounded confidence/score suitable for a
> cognitive **proposal**, not an actuator command.

The phase proves the training/evaluation/artifact/governance pipeline for learned
SNNs. It does not attempt to make the whole SIONA intelligence system an SNN.

---

## 3. Architectural role

```text
Cognitive events / bounded temporal features
                ↓
     Neuromorphic provider interface
                ↓
       ┌───────────────────────┐
       │ deterministic provider│  ← CI/reference/fallback
       └───────────────────────┘
                OR
       ┌───────────────────────┐
       │ learned SNN provider   │  ← Phase 4 target
       └───────────────────────┘
                ↓
  salience / novelty / temporal proposal
                ↓
 Global Cognitive Workspace / policy boundary
```

The learned provider is advisory. It does not acquire tool, owner, policy, or
physical-actuator authority.

---

## 4. Implementation stages

### Phase 4A — Contract and dataset/training governance

1. Audit the existing neuromorphic provider contract and deterministic reference.
2. Define a versioned learned-provider metadata/artifact schema.
3. Define the first bounded training/evaluation task.
4. Define a deterministic synthetic/neutral temporal dataset generator or a
   separately approved small public dataset with recorded licence/provenance.
5. Define deterministic seeds and train/validation/test separation.
6. Define checkpoint checksum/provenance requirements.
7. Define evaluation metrics and minimum acceptance thresholds before training.

No private identity, company-contact, website, user-memory, or unrelated research
records may be used as training data by default.

### Phase 4B — CPU reference learned SNN

Implement the smallest practical learned SNN backend that can be trained and
validated reproducibly on the current CPU machine.

Preferred initial stack for evaluation:

- Python/PyTorch-compatible implementation;
- snnTorch or Norse may be evaluated as optional learned backends;
- no backend is accepted merely because it is listed here;
- dependency, licence, maintenance and deterministic behavior must be reviewed
  before adoption.

A tiny CPU reference training run is permitted only when the training plan,
data/provenance and thresholds are already recorded.

### Phase 4C — Provider integration

1. Load the accepted learned checkpoint through a replaceable provider.
2. Keep deterministic/reference provider as fallback.
3. Expose safe capability/health metadata.
4. Feed learned salience/temporal outputs into the existing cognitive proposal
   path without bypassing policy or owner-control boundaries.
5. Prove fallback when the learned artifact is missing, invalid or disabled.

### Phase 4D — Evaluation and evidence

Record:

- training configuration;
- seed;
- dataset provenance/version;
- checkpoint checksum;
- train/validation/test metrics;
- comparison against deterministic/reference and naive/random baselines;
- inference latency;
- spike/event statistics where meaningful;
- memory use where measurable;
- failure/abstention behavior;
- fallback behavior;
- evidence that no tool or actuator authority is granted.

### Phase 4E — Hardware-gated benchmark

GPU benchmarking is **hardware-gated**.

If an approved CUDA-capable environment is available later, run a separate,
reproducible GPU training/inference benchmark. Lack of a CUDA GPU on the current
machine must not cause Phase 4 software architecture to pretend GPU execution
occurred.

A Phase 4 CPU learned-provider acceptance may be possible without the GPU
benchmark if the acceptance criteria below are met; `HW-SNN-001` GPU execution
and `HW-BENCH-001` remain explicitly open/hardware-gated until separately
verified.

---

## 5. First-task requirements

The first learned task must be small enough to audit and reproduce. It must:

- operate on synthetic/neutral temporal event sequences or separately approved
  public data;
- have explicit labels and split provenance;
- support deterministic regeneration from a versioned seed/config where
  synthetic;
- avoid personal/private identity information;
- avoid website/customer/company contact data;
- avoid using Qwen outputs as training labels by default;
- avoid physical-control labels;
- measure genuine learned generalization on a held-out set rather than merely
  memorizing a fixture.

The exact task definition and thresholds must be committed **before** the first
acceptance training run.

---

## 6. Acceptance criteria

Phase 4 cannot be marked complete unless all required criteria are met.

### Required software/evidence criteria

1. A real learned SNN checkpoint exists and is distinguishable from the
   deterministic neuromorphic provider.
2. Training is reproducible from recorded code/config/data provenance and seed.
3. The checkpoint checksum and metadata are recorded.
4. Held-out evaluation exceeds a predeclared naive/random baseline by the
   predeclared margin for the bounded task.
5. Learned-provider inference executes through the existing provider boundary.
6. Missing/corrupt/disabled learned artifacts fail closed to the deterministic
   provider or an explicit unavailable state.
7. Hosted CI does not perform expensive model training and remains deterministic.
8. No learned output directly authorizes tools or physical actuation.
9. Owner-control, policy and capability enforcement remain authoritative.
10. No private or unapproved data enters the training dataset.
11. Phase 4 evidence distinguishes CPU verification from any hardware-gated GPU
    benchmark.
12. Current Qwen/model-registry capabilities are not silently expanded.

### Optional/hardware-gated criteria

- CUDA training benchmark;
- GPU latency/energy comparison;
- Loihi/FPGA deployment;
- real event-camera input.

These remain separate capability claims until actually verified.

---

## 7. Explicit non-objectives

Phase 4 does **not** authorize or include:

- Qwen LoRA/QLoRA/PEFT or language-model fine-tuning;
- a SIONA-native foundation language model claim;
- vector/Postgres production memory migration;
- semantic-RAG deployment;
- real STT/TTS/voice embodiment;
- SIBONA implementation;
- MQTT/ROS 2 physical integration;
- robotics/humanoid control;
- vehicle/drone control;
- physical actuation;
- automatic or permanent Qwen startup;
- enabling Qwen tools, structured JSON, streaming or multimodal capability;
- production-security certification;
- cloud/multi-GPU infrastructure migration;
- product integrations outside SIONA Core.

Those require later, separately governed phases/ADRs.

---

## 8. Safety and authority constraints

- Learned SNN outputs are **proposals/signals**, not permission decisions.
- Model output is not authorization.
- Trace IDs are not authentication.
- Policy/tool/capability systems remain authoritative.
- No physical actuator may be driven by this phase.
- No owner-control semantics may be altered as a side effect of SNN training.
- Artifact loading must validate expected type/version/checksum before use.

---

## 9. CI strategy

Hosted CI must remain lightweight and deterministic.

CI may use:

- deterministic/reference neuromorphic provider tests;
- tiny static learned checkpoint fixtures when licence/provenance permits;
- deterministic forward-pass tests;
- artifact-schema/checksum validation;
- synthetic-data generator determinism tests;
- provider fail-closed/fallback tests.

Hosted CI must not require:

- CUDA;
- external model downloads;
- long training runs;
- Qwen/llama.cpp;
- private datasets;
- external network access.

---

## 10. Evidence naming

Recommended Phase 4 experiment sequence:

- `EXP-4-001` — neuromorphic contract + task/dataset readiness audit
- `EXP-4-002` — synthetic/public dataset deterministic split validation
- `EXP-4-003` — first CPU SNN training/evaluation run
- `EXP-4-004` — learned-provider integration/fallback verification
- `EXP-4-005` — breadth/safety/evidence gate
- `EXP-4-006` — optional hardware-gated GPU benchmark when available

Experiment numbering records evidence; it does not imply an experiment passed.

---

## 11. ADR requirement

ADR 0004 — Learned neuromorphic backend strategy is proposed alongside this
specification. It remains **Proposed** until the learned provider and evidence
justify acceptance.

---

## 12. Phase 4 entry decision

Merging the Phase 4 planning gate may authorize implementation of **Phase 4A
only**: contract audit, dataset/task governance, test scaffolding, and dependency
research.

It does **not** by itself authorize a real training run or a new dependency
installation. Before the first real SNN training execution, the Phase 4A records
must identify the exact task, data source/generator, backend/version, dependency
licences, metrics and acceptance threshold.

This preserves the Vision Charter rule that planning, implementation, training
and capability claims are separate governed transitions.
