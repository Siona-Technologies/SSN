# SIONA Phase 4B — First Controlled CPU SNN Training (EXP-4-003)

**Experiment:** EXP-4-003  
**Date:** 2026-08-07  
**Execution base SHA:** `b8c633fe2cdea55043426937637b48d55da20302`  
**Decision:** `FIRST_CPU_SNN_TRAINING_VERIFIED`  
**Training runs:** 1 (exactly one; no retune)

## Executive result

EXP-4-003 completed the frozen Phase 4B CPU training/evaluation plan on an
isolated CPython 3.11.9 x64 venv. Held-out test metrics passed every immutable
acceptance check. A canonical JSON candidate artifact was exported and is
eligible for later pure-Python / provider parity work.

This does **not**:

- integrate a learned `NeuromorphicProvider`;
- accept ADR 0004;
- complete Phase 4;
- authorize CUDA/GPU claims;
- change Qwen/model-registry capabilities;
- grant tool or physical-actuator authority.

## Bootstrap recovery (pre-training)

The original attempt stopped at `PYTHON_3_11_REQUIRED_BUT_NOT_AVAILABLE`.
PR #24 amended the Phase 4B gate to allow one controlled user-scoped WinGet
install of `Python.Python.3.11` side-by-side. Python 3.14 and QGIS Python were
preserved. Bootstrap did not consume the training run.

## Environment (sanitized)

| Item | Value |
|------|--------|
| Python | 3.11.9 x64 |
| torch | 2.13.0+cpu |
| snntorch | 1.0.0 |
| `torch.version.cuda` | `None` |
| `torch.cuda.is_available()` | false |
| torch wheel | `torch-2.13.0+cpu-cp311-cp311-win_amd64.whl` |
| torch SHA-256 | `10717d8b3b67c45a4788bf7ffc0bab1ea1e5ebbedd24466be6100102d141fac1` |
| snntorch wheel | `snntorch-1.0.0-py2.py3-none-any.whl` |
| snntorch SHA-256 | `b5a85f6f44c6d27c8a1dcea16cb18a630d00b8d2f3cfec85b7e580cb177e606b` |
| `requirements.txt` | unchanged |
| pip freeze | operator-local outside Git |

## Preflight (sanitized)

- available RAM ≥ 4 GiB (measured ≈ 7.18 GiB free)
- free disk ≥ 2 GiB (measured ≈ 39.2 GiB free on system volume)
- AC power
- port 8080 closed
- Qwen stopped
- llama.cpp stopped

## Frozen task / model

- task: `phase4a-temporal-salience-v1`
- architecture: `phase4b-lif-final-membrane-v1`
- seed: `42007`
- topology: 8→16 LIF (β=0.9, θ=1.0, subtract reset, fast_sigmoid slope 25) → 2-class linear readout from final membrane
- max epochs 80 / wall clock 600 s / one test evaluation / no test tuning

Dataset fingerprints matched EXP-4-001 frozen values:

- train `e124d6b5858399956f7b52f1fc6e342e9d2833704b44710315d57844c43805bd`
- validation `cfd32c4b9b2684dc10f21e9b28d169807c42ae54e7968d5080a676d602929285`
- test `34d93878277a0b6afae880c02a3b2d878fbc142a1cfee77b51985eebbf7f4116`

## Training summary

| Field | Value |
|-------|--------|
| epochs executed | 80 |
| selected epoch | 79 |
| stop reason | `max_epochs` |
| selected validation loss | ≈ 3.38e-4 |
| wall seconds | ≈ 7.08 |
| test balanced accuracy | 1.0 |
| class-0 recall | 1.0 |
| class-1 recall | 1.0 |
| baseline margin | 0.5 |
| positive original mean | ≈ 0.99943 |
| positive reversed mean | ≈ 1.67e-7 |
| time-reversal score drop | ≈ 0.99943 |
| confusion matrix | `[[64, 0], [0, 64]]` |

All acceptance checks passed.

## Artifacts

- raw `.pt` checkpoint: operator-local outside Git  
  SHA-256 `8c67eb056970a109caeaf7d5cb9e5942372c919b203d56dbae158a5935e4ccec`
- committed candidate JSON: `artifacts/neuromorphic/phase4b-lif-final-membrane-v1.json`  
  SHA-256 `dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc`
- authority fields on candidate: `tool_authority=false`, `physical_actuation_authority=false`

## Governance after EXP-4-003

- ADR 0004: **Proposed**
- Phase 4: **in progress**; learned-provider integration + fallback/parity verification is the next blocker
- Qwen / llama.cpp remain stopped; port 8080 closed
- no tool executions; no physical actuation
- `ssn/data` and website untouched; protected primary `world_model.json` untouched by this experiment worktree

## Evidence

- `docs/evidence/EXP-4-003_FIRST_CPU_SNN_TRAINING.json`
- `artifacts/neuromorphic/phase4b-lif-final-membrane-v1.json`
- gate: `docs/PHASE_4B_FIRST_CPU_SNN_TRAINING_GATE.md`
