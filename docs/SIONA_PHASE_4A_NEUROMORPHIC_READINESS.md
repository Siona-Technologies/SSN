# SIONA Phase 4A — Learned Neuromorphic Readiness Audit (EXP-4-001)

**Experiment:** EXP-4-001  
**Date:** 2026-08-07  
**Base main SHA:** `409d0d0b5144e4d6236269b09952a84dcbd58d69`  
**Mode:** read-only architecture/dependency research + deterministic model-free task scaffolding  
**Decision:** `PHASE_4A_READINESS_DEFINED_TRAINING_NOT_AUTHORIZED`

## Executive result

Phase 4A has enough architectural separation to proceed toward a first learned
SNN, but the repository deliberately has **no PyTorch/SNN training dependency**
and no governed learned-checkpoint format yet.

The correct next transition is therefore a separate dependency/training execution
gate after this readiness record is accepted. No training was run by EXP-4-001.

## 1. Existing neuromorphic contract audit

The current `NeuromorphicProvider` protocol already defines the required runtime
surface:

- `capabilities()`
- `health()`
- `reset()`
- `get_state()`
- `process_event()`
- `process_batch()`

`NeuromorphicOutput` already carries bounded fields suitable for a learned
provider, including salience, novelty/anomaly fields, attention trigger,
optional reflex **proposal**, optional spike trace, energy, backend identity and
a `simulated` marker.

### Contract conclusion

**No higher-level contract redesign is required for the first learned SNN.**

A learned provider can implement the existing protocol and remain injectable
through `NeuromorphicSNNFacade`. The facade already defaults to
`DeterministicNeuromorphicProvider`, preserving a deterministic fallback path.

### Existing providers

- `DeterministicNeuromorphicProvider`
  - deterministic;
  - simulated;
  - not trained;
  - stable reference/fallback for CI;
  - emits synthetic spike and energy metadata.
- `LegacySNNEngineAdapter`
  - wraps the older random `SNNEngine`;
  - simulated;
  - non-deterministic;
  - not an acceptable learned baseline.

The first learned provider must never relabel either existing simulation as a
trained SNN.

## 2. Missing learned-artifact boundary

The repository does not yet have a dedicated governed artifact manifest for an
SNN checkpoint. The language-model registry must **not** be reused casually for
this purpose because it describes a different model/runtime authority boundary.

Before provider integration, Phase 4 must define a neuromorphic artifact record
containing at minimum:

- provider/backend ID;
- task ID/version;
- architecture/topology ID;
- training backend and exact version;
- Python/PyTorch version;
- dataset/generator ID and fingerprints;
- seed and split policy;
- checkpoint format;
- checkpoint SHA-256;
- trained/verified status;
- accepted metrics;
- capability/scope limits;
- `tool_authority=false`;
- `physical_actuation_authority=false`.

## 3. Current dependency boundary

Current repository `requirements.txt` contains only:

- `python-dotenv==1.2.1`
- `PyYAML==6.0.3`

It does **not** currently include PyTorch, snnTorch, Norse or another SNN
training framework.

Therefore importing the new Phase 4A dataset scaffold remains dependency-free,
and hosted CI stays model-free.

No PyTorch/SNN package was installed during this audit.

## 4. Official-source backend research

Source access date: **2026-08-07**.

### Candidate A — snnTorch 1.0.0

Official PyPI/project evidence records:

- release: **1.0.0**, uploaded 2026-06-29;
- licence: **MIT** for source code;
- Python requirement: `>=3.9`;
- project classifiers explicitly include Python 3.9, 3.10 and 3.11;
- PyTorch is a prerequisite;
- pip installation also uses lightweight Python dependencies including numpy and
  pandas;
- project documentation explicitly states that small and large networks can be
  trained on CPU where needed and that CUDA acceleration follows PyTorch when
  available.

Readiness interpretation:

- good fit for the CPU-first proof;
- permissive licence is simpler for the initial dependency gate;
- recent 1.0.0 release;
- exact PyTorch version is **not** selected by this audit;
- Python 3.12 support must not be inferred merely from `Requires-Python >=3.9`
  because the published classifiers shown in the inspected release stop at 3.11.

### Candidate B — Norse 1.1.0

Official PyPI/project evidence records:

- release: **1.1.0**, uploaded 2024-03-18;
- licence: **LGPLv3**;
- Python requirement: `>=3.8`;
- project classifiers include Python 3.8 through 3.11;
- package metadata requires `torch>=2.0.0`, `torchvision>=0.15.0`, `numpy`, `nir`
  and `nirtorch`;
- the project provides PyTorch-based spiking-neural-network primitives.

Readiness interpretation:

- technically viable and mature;
- larger default dependency surface for this repository;
- LGPL obligations require deliberate packaging/compliance handling;
- older published release than the inspected snnTorch release.

### Preferred dependency-gate candidate

**snnTorch 1.0.0 is preferred for the first controlled dependency/training gate.**

This is a research recommendation, **not an installation approval**. The next
gate must still choose an exact compatible CPU PyTorch build and verify the
selected Python interpreter before any dependency installation.

For the first local execution gate, Python 3.11 is the conservative candidate
because both inspected SNN packages explicitly classify Python 3.11 support.
Hosted CI must not become dependent on the training stack.

## 5. First bounded task — `phase4a-temporal-salience-v1`

A deterministic synthetic task is defined in:

`config/phase4a_temporal_salience_task.json`

and generated by:

`ssn/cognition/neuromorphic/phase4a_dataset.py`

### Input

- 20 timesteps;
- 8 binary event channels;
- exactly 16 events per sample.

### Classes

- `0` — distributed background activity;
- `1` — late synchronous burst.

The total event count is identical for both classes. Therefore a model cannot
solve the task merely by counting events; the discriminating information is the
temporal distribution.

Positive samples place 12/16 events in the final four timesteps. Negative
samples distribute one event over 16 distinct timesteps, limiting late-window
activity to at most 4/16.

### Deterministic splits

- train: 256 samples;
- validation: 64 samples;
- test: 128 samples;
- balanced classes in every split;
- root seed: 42007;
- split/sample seeds derived by SHA-256 rather than Python's process-randomized
  hash.

Frozen readiness fingerprints:

- train: `e124d6b5858399956f7b52f1fc6e342e9d2833704b44710315d57844c43805bd`
- validation: `cfd32c4b9b2684dc10f21e9b28d169807c42ae54e7968d5080a676d602929285`
- test: `34d93878277a0b6afae880c02a3b2d878fbc142a1cfee77b51985eebbf7f4116`

The generator contains no personal, company, customer, website or user-memory
data and uses no Qwen-generated labels.

## 6. Predeclared future training criteria

These values are locked **before** the first training run:

- test balanced accuracy >= **0.90**;
- per-class recall >= **0.85**;
- margin over balanced random/majority baseline >= **0.20**;
- test set may not be used for threshold tuning;
- a temporal-sensitivity control is required;
- for positive examples, time reversal must reduce the model's positive score by
  at least **0.10** on the declared aggregate control metric.

The task's balanced majority baseline is exactly 0.50. Total event count is
non-discriminative by construction.

## 7. Candidate first topology

Framework-neutral starting point:

- input: 8 event features per timestep;
- hidden: 16 LIF spiking units;
- output: 2 classes;
- sequence length: 20 timesteps.

The exact recurrent/feed-forward topology, decoder/readout, surrogate gradient,
loss, optimizer, learning rate, epoch limit and early-stopping policy remain
**pending** until the dependency/training gate. They must be committed before
training and may not be tuned on the held-out test set.

## 8. Safety/authority result

The existing provider contract supports a learned provider without granting
additional authority.

For the first learned checkpoint:

- `tool_authority=false`;
- `physical_actuation_authority=false`;
- outputs remain proposals/signals;
- deterministic policy/capability layers remain authoritative;
- no robotics/IoT/vehicle/drone path is part of this task;
- Qwen/model-registry capabilities remain unchanged.

## 9. EXP-4-001 decision

`PHASE_4A_READINESS_DEFINED_TRAINING_NOT_AUTHORIZED`

The architecture, task, deterministic dataset and predeclared evaluation gate
are ready for review. The next step is a **separate dependency + training
execution authorization** that must pin:

1. Python interpreter;
2. CPU PyTorch version/build;
3. snnTorch version and artifact provenance;
4. exact topology/readout;
5. loss/optimizer/learning rate;
6. epoch/time budget and early stopping;
7. checkpoint path and cleanup policy;
8. resource preflight;
9. execution/evidence script.

Until that gate is accepted, **no SNN training is authorized**.

## External source references

- PyPI: `snntorch` 1.0.0 project/release metadata, accessed 2026-08-07.
- snnTorch project description/documentation linked from its official PyPI page,
  accessed 2026-08-07.
- PyPI: `norse` 1.1.0 project/release metadata, accessed 2026-08-07.
- Norse official project documentation linked from PyPI, accessed 2026-08-07.
