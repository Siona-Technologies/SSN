# ADR 0004 — Learned neuromorphic backend strategy

## Status

Proposed

## Context

SIONA's hybrid architecture intentionally separates deliberative foundation-model
reasoning from a neuromorphic layer responsible for bounded temporal processing,
salience, novelty, anomaly and reflex **proposals**.

Phase 3 accepted the first real optional local foundation-model path. The
neuromorphic provider remains deterministic/reference-only; no trained SNN is
currently claimed in SIONA Core.

`DEFERRED_CAPABILITIES.md` records SNN training and GPU benchmarking as Phase 4
or hardware-gated work. The current development machine has no CUDA GPU, so the
architecture must distinguish a reproducible CPU learned-provider proof from a
future CUDA benchmark.

## Decision under evaluation

Phase 4 will evaluate a **replaceable learned SNN provider** behind the existing
neuromorphic-provider boundary.

The first accepted learned SNN, if evidence supports it, will:

- solve a bounded temporal salience/classification task;
- remain advisory only;
- produce proposals/signals rather than authorization;
- use a versioned, governed dataset/generator and deterministic split;
- record backend/version, training configuration, seed and checkpoint checksum;
- retain the deterministic/reference provider as CI path and fallback;
- remain independent of Qwen and the local language-model registry;
- not require physical hardware or actuator access.

## Candidate implementation direction

snnTorch and Norse may be evaluated as candidate Python/PyTorch-compatible
backends. Neither is approved by this ADR merely by being named.

Before adopting a backend, Phase 4A must record:

- official project/source;
- exact version;
- licence;
- Python/PyTorch compatibility;
- CPU support;
- deterministic/reproducibility considerations;
- maintenance status;
- dependency footprint;
- artifact/checkpoint format implications.

## Training-data boundary

The first Phase 4 training dataset must use either:

1. a deterministic synthetic/neutral temporal generator committed under SIONA
   control; or
2. a separately approved public dataset with explicit licence/provenance.

Private identity records, contacts, customer data, website content, user memory,
secrets and unrelated personal/project material are excluded by default.

Qwen-generated pseudo-labels are not an approved default training authority.

## Hardware boundary

A small CPU reference learned SNN may be accepted if it satisfies the predeclared
Phase 4 criteria.

CUDA training and GPU benchmarking remain separate hardware-gated claims until a
CUDA-capable environment is actually available and verified. No documentation
may convert CPU evidence into a GPU claim.

## Authority boundary

A learned SNN may influence:

- salience;
- novelty;
- temporal classification;
- attention prioritisation;
- bounded reflex proposals.

It may not directly authorize:

- tools;
- policy changes;
- owner actions;
- external side effects;
- physical actuators.

Existing deterministic policy, capability and physical-safety requirements
remain authoritative.

## Alternatives

| Alternative | Disposition |
|---|---|
| Keep deterministic neuromorphic provider only | Safe fallback, but does not advance the learned SNN layer |
| Make the whole SIONA brain an SNN now | Rejected; contradicts the hybrid architecture and current evidence |
| Fine-tune Qwen instead | Deferred; language-model adaptation is a separate model-training/data-governance decision |
| Start robotics/IoT next | Deferred; physical safety and learned cognitive signals must mature first |
| Require CUDA before any learned SNN work | Rejected; software architecture and a small CPU proof can proceed while GPU evidence stays hardware-gated |
| Use private/user identity data for first training | Rejected by default; unnecessary and creates governance risk |

## Acceptance conditions before ADR status may become Accepted

1. Exact learned task and predeclared metrics/thresholds are recorded before the
   acceptance training run.
2. Dataset/generator provenance and train/validation/test split are reproducible.
3. Backend/version/licence are recorded.
4. A real learned checkpoint is produced from an authorized training run.
5. Checkpoint checksum and metadata are recorded.
6. Held-out performance exceeds the predeclared naive/random baseline by the
   required margin.
7. Learned inference works through the existing neuromorphic-provider boundary.
8. Deterministic provider fallback remains intact.
9. Hosted CI remains deterministic and does not train the model.
10. No tool/actuator/owner authority is granted to the SNN.
11. No unapproved/private training data is used.
12. CPU and any future GPU evidence are labeled separately.
13. Qwen registry capabilities remain unchanged unless separately approved.

## Consequences if accepted later

- SIONA will have its first genuine learned neuromorphic component.
- The deterministic provider remains available for CI, fallback and reference.
- The learned checkpoint is a governed SIONA artifact, but this alone does not
  make the foundation language model SIONA-native.
- Later phases may expand learned neuromorphic tasks or hardware backends without
  rewriting higher-level cognitive contracts.

## Non-authorization

This Proposed ADR does not authorize:

- a training run;
- dependency installation;
- CUDA/GPU claims;
- Qwen fine-tuning;
- physical actuation;
- robotics/IoT integration;
- Phase 4 completion.

It authorizes planning/research only when merged as part of the Phase 4 planning
gate.

## References

- [PHASE_4_ENGINEERING_SPEC.md](../PHASE_4_ENGINEERING_SPEC.md)
- [SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md](../SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md)
- [DEFERRED_CAPABILITIES.md](../DEFERRED_CAPABILITIES.md)
- [SIONA_VISION_CHARTER.md](../SIONA_VISION_CHARTER.md)
