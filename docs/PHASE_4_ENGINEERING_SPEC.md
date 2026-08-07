# Phase 4 Engineering Specification — Learned Neuromorphic Backend

**Status:** Completed and accepted — EXP-4-003/004/005 verified; ADR 0004 Accepted (Phase 4)  
**Phase 3 prerequisite:** Complete and accepted  
**Primary objective:** Deliver the first **real learned SNN provider** for a bounded salience/temporal classification task while preserving deterministic safety, replaceable providers, and model-free hosted CI.  
**Governing charter:** [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md)  
**Acceptance record:** [PHASE_4_ACCEPTANCE.md](PHASE_4_ACCEPTANCE.md)

---

## 1. Objective and disposition

Phase 4 advanced the second learned layer of SIONA's hybrid architecture: a
bounded neuromorphic/SNN provider for salience and temporal classification.

The phase is now **complete** for that defined software-provider scope. It did
not make the whole SIONA intelligence system an SNN and did not grant the
learned provider tool or physical-actuator authority.

---

## 2. Accepted architecture

```text
Cognitive events / bounded temporal features
                ↓
     Neuromorphic provider interface
                ↓
       ┌───────────────────────┐
       │ deterministic provider│  ← default / CI / fallback
       └───────────────────────┘
                OR
       ┌───────────────────────┐
       │ learned SNN provider   │  ← explicit opt-in
       └───────────────────────┘
                ↓
 temporal classification / salience / attention signal
                ↓
 Global Cognitive Workspace / policy boundary
```

Accepted learned provider:

- `siona-neuro-learned-lif-v1`;
- task `phase4a-temporal-salience-v1`;
- architecture `phase4b-lif-final-membrane-v1`;
- exact learned input `temporal_salience_v1`, 20 × 8 binary;
- canonical artifact SHA-256
  `dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc`;
- pure-Python runtime inference;
- deterministic/reference provider retained as default and fallback.

The learned provider is advisory. It does not acquire tool, owner, policy,
memory-mutation or physical-actuator authority.

---

## 3. Completed Phase 4 stages

### Phase 4A — Contract and dataset/training governance

Completed under EXP-4-001:

- audited the existing neuromorphic provider contract;
- defined the bounded temporal-salience task;
- defined deterministic synthetic data and frozen split fingerprints;
- recorded dependency/licence research;
- froze metrics and acceptance thresholds before training.

No private identity, company-contact, website, user-memory or unrelated research
records were used as training data.

### Phase 4B — CPU reference learned SNN

Completed under the frozen Phase 4B training gate and EXP-4-003:

- CPython 3.11 x64 isolated environment;
- PyTorch 2.13.0+cpu;
- snnTorch 1.0.0;
- one controlled CPU training run;
- architecture `phase4b-lif-final-membrane-v1`;
- canonical learned artifact exported and checksum recorded;
- `FIRST_CPU_SNN_TRAINING_VERIFIED`.

### Phase 4C — Provider integration and parity

Completed under EXP-4-004:

- strict artifact loading;
- dependency-free pure-Python LIF inference;
- explicit learned-provider integration;
- deterministic fallback preserved;
- 197/197 class and spike-count parity against the retained snnTorch reference;
- `LEARNED_SNN_PROVIDER_PARITY_VERIFIED`.

### Phase 4D — Breadth / safety / integrity

Completed under EXP-4-005:

- removed in-memory artifact injection bypass;
- bounded artifact reads to 256 KiB;
- strict learned-event envelope;
- bounded batches to 256 events;
- atomic batch prevalidation;
- malformed learned inputs fail closed;
- corruption/fallback/edge matrices passed;
- full frozen test breadth 128/128;
- `PHASE4_LEARNED_SNN_BREADTH_SAFETY_VERIFIED`.

### Phase 4E — Hardware-gated benchmark

Not required for this bounded software-provider acceptance.

CUDA/GPU benchmarking remains explicitly hardware-gated and **not verified** on
the current machine. A future benchmark must be separately authorized and must
not be inferred from CPU evidence.

---

## 4. First-task definition

The accepted task remains intentionally narrow:

> Given a bounded 20 × 8 binary temporal event sequence, classify temporal
> salience and expose bounded score/spike information suitable for cognitive
> attention, not actuator authorization.

The dataset is deterministic synthetic/neutral data under SIONA control with
explicit labels, frozen train/validation/test splits and no Qwen-generated
labels.

---

## 5. Acceptance evidence

All required software/evidence criteria are satisfied:

1. Real learned SNN artifact distinct from deterministic provider — **satisfied**.
2. Reproducible training code/config/data provenance/seed — **satisfied**.
3. Artifact checksum and metadata recorded — **satisfied**.
4. Held-out evaluation exceeds predeclared baseline — **satisfied**.
5. Learned inference executes through provider boundary — **satisfied**.
6. Invalid/corrupt artifacts and malformed learned inputs fail closed; unsupported modalities fall back deterministically — **satisfied**.
7. Hosted CI remains deterministic and does not train — **satisfied**.
8. No learned output directly authorizes tools or actuation — **satisfied**.
9. Owner-control, policy and capability enforcement remain authoritative — **satisfied**.
10. No private/unapproved data entered training — **satisfied**.
11. CPU evidence is distinguished from hardware-gated GPU claims — **satisfied**.
12. Qwen/model-registry capabilities were not expanded — **satisfied**.

See [PHASE_4_ACCEPTANCE.md](PHASE_4_ACCEPTANCE.md) for the final disposition.

---

## 6. Accepted metrics and controls

- held-out test: 128/128 correct;
- balanced accuracy: 1.0;
- class-0 recall: 1.0;
- class-1 recall: 1.0;
- reversed positive samples: 64;
- temporal mean score drop: ≈0.99943249;
- EXP-4-004 parity: 197/197 class/spike-count agreement;
- valid edge controls: 9/9;
- malformed learned inputs: fail closed;
- corrupt artifacts: rejected;
- unsupported modalities: deterministic fallback;
- maximum batch: 256;
- maximum artifact: 256 KiB bounded read.

---

## 7. Explicit non-objectives / non-claims

Phase 4 does **not** authorize or claim:

- Qwen LoRA/QLoRA/PEFT or language-model fine-tuning;
- a SIONA-native foundation language model;
- vector/Postgres production memory migration;
- semantic-RAG deployment;
- real STT/TTS/voice embodiment;
- SIBONA implementation;
- MQTT/ROS 2 physical integration;
- robotics/humanoid/vehicle/drone control;
- physical actuation;
- automatic/permanent Qwen startup;
- enabling Qwen tools, structured JSON, streaming or multimodal capability;
- production-security certification;
- cloud/multi-GPU migration;
- CUDA/GPU SNN training/benchmark evidence;
- Loihi/FPGA/neuromorphic-silicon execution;
- measured SNN energy efficiency;
- persistent event-by-event asynchronous/stateful SNN streaming;
- real event-camera input.

---

## 8. Safety and authority constraints

- Learned SNN outputs are signals/proposals, not permission decisions.
- Model output is not authorization.
- Trace IDs are not authentication.
- Policy/tool/capability systems remain authoritative.
- No physical actuator is driven by the accepted provider.
- Owner-control semantics are unchanged.
- Artifact loading validates exact identity, checksum, shape and authority flags.

---

## 9. CI strategy

Hosted CI remains lightweight and deterministic. It may run:

- deterministic/reference neuromorphic tests;
- canonical learned-artifact validation;
- pure-Python forward-pass tests;
- frozen parity fixtures;
- synthetic-data determinism tests;
- fail-closed/fallback/breadth tests.

Hosted CI does not require CUDA, external downloads, model training,
Qwen/llama.cpp, private datasets or network access.

---

## 10. Evidence sequence

- `EXP-4-001` — readiness/task/dataset audit;
- `EXP-4-003` — first CPU SNN training/evaluation;
- `EXP-4-004` — learned-provider integration/parity;
- `EXP-4-005` — breadth/safety/integrity gate.

`EXP-4-002` was not required as a separate execution because deterministic split
validation was incorporated into the readiness/training-gate evidence. Experiment
numbering is not required to be contiguous.

`EXP-4-006` remains an optional future hardware-gated GPU benchmark and is not
part of Phase 4 software acceptance.

---

## 11. ADR disposition

ADR 0004 — Learned neuromorphic backend strategy is **Accepted (Phase 4)**.

The acceptance is deliberately narrow: a trained software SNN provider for one
bounded temporal task, not a claim of a complete asynchronous neuromorphic brain.

---

## 12. Phase disposition

**Phase 4 is COMPLETE** for its defined learned-neuromorphic software-provider
scope.

No subsequent phase is started by this specification. A new objective requires a
separate governed planning decision.
