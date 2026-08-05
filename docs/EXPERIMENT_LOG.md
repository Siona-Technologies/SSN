# Experiment Log

Standard template for future experiments. **Do not fabricate results.**

---

## Template

```text
Experiment ID:
Date:
Git commit:
Runtime mode: legacy | shadow | cognitive_experimental
Dataset:
Model/provider:
Neuromorphic backend:
Hardware: (CPU / GPU model / CUDA yes|no)
Configuration:
Metrics:
Result:
Limitations:
Artifact references:
Reproduction command:
```

## Logged experiments

### EXP-3A-001 — Provider eval scaffold (mock/deterministic)

```text
Experiment ID: EXP-3A-001
Date: 2026-08-05
Git commit: (Phase 3A branch tip)
Runtime mode: legacy (default) + provider eval harness
Dataset: built-in provider eval cases
Model/provider: deterministic + mock local HTTP (no real weights)
Neuromorphic backend: n/a
Hardware: CPU-only laptop (no CUDA)
Configuration: SSN_OFFLINE=1; no SSN_MODEL_PROVIDER unless test-local
Metrics: provider_eval summary pass/fail
Result: Phase 3A scaffold only — not a real-model benchmark
Limitations: No open-weight model installed; results labelled mock/deterministic
Artifact references: artifacts/eval/ or SSN_EVAL_OUTPUT_DIR
Reproduction command: SSN_OFFLINE=1 python scripts/run_eval.py --provider
```
