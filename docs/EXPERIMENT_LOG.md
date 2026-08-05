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
Git commit: d6c17d0d723ef309cca1f8edf3fb467b12d04d2a
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

### EXP-3A-002 — Final security/isolation gate (mock/deterministic)

```text
Experiment ID: EXP-3A-002
Date: 2026-08-05
Git commit: d6c17d0d723ef309cca1f8edf3fb467b12d04d2a
Runtime mode: legacy + hardened local provider foundation
Dataset: Phase 3A security/registry/isolation/provider-eval suites
Model/provider: deterministic + mock local HTTP only
Result: Final gate hardening — redirects rejected, request sanitizer,
        per-test isolation, registry transactional load, hard eval timeouts
Limitations: Still no real model/runtime; not production-security certified
Reproduction command: SSN_OFFLINE=1 python scripts/run_tests.py
```

### EXP-3B-000 — Hardware readiness and planning baseline

```text
Experiment ID: EXP-3B-000
Date: 2026-08-05
Git commit: (Phase 3B planning branch tip)
Runtime mode: n/a — planning only
Dataset: n/a
Model/provider: none installed
Neuromorphic backend: n/a
Hardware: HP EliteBook 840 G8; Intel i7-1165G7 (4C/8T); Intel Iris Xe;
          15.73 GiB RAM; no CUDA GPU; Balanced power plan; on AC during inventory
Configuration: no runtime; no weights; documentation scaffolding only
Metrics: none (no inference)
Result: readiness/planning only —
        storage gate passed at 41.86 GiB free after controlled cleanup
        (prior low-space ~7.74 GiB; 31.51 GiB duplicate archive removed);
        free RAM after restart/check 4.73 GiB; preferred target 6–8 GiB;
        WSL2 Ubuntu available but stopped; Docker absent; no model runtimes
Limitations: model and runtime selection pending; no real-model experiment;
             no runtime installed; no weights downloaded
Artifact references: docs/PHASE_3B_HARDWARE_INVENTORY.md,
                      docs/PHASE_3B_MODEL_INDEPENDENCE.md,
                      docs/PHASE_3B_MODEL_RUNTIME_RESEARCH.md,
                      docs/PHASE_3B_INSTALLATION_RUNBOOK.md,
                      docs/adr/0003-first-local-model-strategy.md
Reproduction command: n/a (documentation/planning entry)
```
