# SIONA Phase 4D — Learned SNN Breadth / Safety Gate (EXP-4-005)

**Experiment:** EXP-4-005  
**Date:** 2026-08-07  
**Base main SHA:** `4689963ebb13d62132d00f7db20a94ba9f149dee`  
**Decision:** `PHASE4_LEARNED_SNN_BREADTH_SAFETY_VERIFIED`  
**Training runs:** 0

## Executive result

EXP-4-005 hardens the learned software SNN provider and records a full
model-free breadth/safety/integrity gate after EXP-4-004 parity.

ADR 0004 remains **Proposed**. Phase 4 remains **in progress**.

## Security hardenings

| Issue | Fix |
|------|-----|
| A — in-memory artifact injection | Removed public `artifact=<dict>` construction; weights load only from SHA-verified file bytes |
| B — unbounded artifact read | Stat + bounded read of at most `MAX_ARTIFACT_BYTES + 1` (256 KiB) |
| C — learned event envelope | Exact feature key set `{temporal_sequence}`; bounded non-empty `event_id`; binary 20×8 only |
| D — batch bound | `MAX_LEARNED_BATCH_EVENTS = 256`; generators rejected |
| E — batch atomicity | Claimed learned events prevalidated before any provider state mutation |

## Breadth results

| Check | Result |
|------|--------|
| Frozen held-out test | 128/128 correct; balanced accuracy 1.0; recalls 1.0/1.0 |
| Time-reversal (64 positives) | mean drop ≈ 0.99943 (≥ 0.90) |
| Valid edge controls | 9/9 pass (finite probs, no authority) |
| Malformed learned inputs | fail closed; no successful state mutation |
| Corrupted artifacts | rejected before inference |
| Unsupported modalities | deterministic fallback with explicit metadata |

## Isolation / authority

- runtime deps: Python standard library only (no torch/snnTorch/numpy)
- `requirements.txt` unchanged
- Qwen/registry unchanged
- tool executions: 0
- reflex proposals (learned path): 0
- physical actuation authority: false
- `energy_metrics=false`; `energy=0.0` is compatibility only, not a measured claim

## Next blocker

**ADR 0004 ACCEPTANCE + PHASE 4 COMPLETION DECISION**

## Evidence

- `docs/evidence/EXP-4-005_PHASE_4_BREADTH_SAFETY.json`
- tests: `ssn/tests/test_phase4d_learned_snn_breadth_safety.py`
