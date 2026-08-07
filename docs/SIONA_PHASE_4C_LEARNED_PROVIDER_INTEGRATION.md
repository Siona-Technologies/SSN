# SIONA Phase 4C — Learned SNN Provider Integration (EXP-4-004)

**Experiment:** EXP-4-004  
**Date:** 2026-08-07  
**Base main SHA:** `3c23b5dc98a0162c5aee4587704afc3cfd182b1a`  
**Decision:** `LEARNED_SNN_PROVIDER_PARITY_VERIFIED`  
**Training runs in EXP-4-004:** 0

## Executive result

EXP-4-004 integrates the EXP-4-003 canonical candidate as an explicit learned
neuromorphic provider (`siona-neuro-learned-lif-v1`) with:

- strict artifact loading and SHA verification;
- pure-Python LIF inference (no torch/snnTorch/numpy runtime dependency);
- mathematical parity against retained snnTorch 1.0.0 / torch 2.13.0+cpu;
- deterministic fallback for unsupported modalities;
- fail-closed rejection of malformed learned-task inputs;
- unchanged default `NeuromorphicSNNFacade` / deterministic provider.

ADR 0004 remains **Proposed**. Phase 4 remains **in progress**.

## Provider

| Field | Value |
|------|--------|
| Provider ID | `siona-neuro-learned-lif-v1` |
| Artifact | `artifacts/neuromorphic/phase4b-lif-final-membrane-v1.json` |
| Artifact SHA-256 | `dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc` |
| Task | `phase4a-temporal-salience-v1` |
| Architecture | `phase4b-lif-final-membrane-v1` |
| Input modality | `temporal_salience_v1` |
| Input shape | 20 × 8 binary |
| Runtime deps | Python standard library only |
| Default facade | unchanged (`siona-neuro-deterministic-v1`) |

## Parity (operator-local reference stack)

| Field | Value |
|------|--------|
| Python | 3.11.9 |
| torch | 2.13.0+cpu |
| snntorch | 1.0.0 |
| CUDA | false |
| Held-out test | 128 |
| Reversed positives | 64 |
| Edge controls | 5 |
| Total | **197** |
| Max \|Δ logit\| | ≈ 5.95e-6 (≤ 1e-5) |
| Max \|Δ probability\| | ≈ 7.69e-8 (≤ 1e-5) |
| Class agreement | 197/197 |
| Spike-count agreement | 197/197 |

Hosted CI recomputes pure-Python outputs against
`docs/evidence/EXP-4-004_PARITY_FIXTURE.json` (5 representative samples) without
importing torch.

## Governance

- tool authority: false
- physical actuation authority: false
- reflex proposals from learned path: none
- Qwen/registry unchanged
- `requirements.txt` unchanged / training-stack-free
- no Qwen/llama runtime used

## Next blocker

**EXP-4-005 PHASE 4 BREADTH / SAFETY / EVIDENCE GATE**

## Evidence

- `docs/evidence/EXP-4-004_LEARNED_SNN_PROVIDER_PARITY.json`
- `docs/evidence/EXP-4-004_PARITY_FIXTURE.json`
- implementation: `ssn/cognition/neuromorphic/learned_*.py`
