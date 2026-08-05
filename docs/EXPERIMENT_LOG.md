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

### EXP-3B-001 — Official-source runtime and model research

```text
Experiment ID: EXP-3B-001
Date: 2026-08-05
Git commit: (Phase 3B research branch tip)
Runtime mode: n/a — documentation/research only
Dataset: n/a
Model/provider: none installed; none downloaded
Neuromorphic backend: n/a
Hardware: unchanged inventory baseline (i7-1165G7 / Iris Xe / ~16 GiB / no CUDA)
Configuration: no runtime; no weights; official-source research only
Metrics: none (no inference; no token/s fabricated)
Sources examined: ggml-org/llama.cpp (build, SYCL, LICENSE, release b9968);
                  docs.ollama.com/windows; ollama/ollama MIT;
                  LM Studio developer server docs;
                  OpenVINO GenAI 2026 docs;
                  ONNX Runtime GenAI / DirectML path notes;
                  Qwen/Qwen3-1.7B (+ GGUF); ggml-org/Qwen3-1.7B-GGUF;
                  Qwen/Qwen3-4B-GGUF; ibm-granite/granite-4.0-micro(+GGUF);
                  microsoft/Phi-4-mini-instruct; Qwen/Qwen3.5-2B
Result: official-source matrix completed after coverage and
        traceability correction (full 7-runtime / 5-model field sets;
        pinned HF revisions; source traceability appendix);
        provisional runtime = llama.cpp Windows CPU baseline (b9968);
        provisional first model family = Qwen3-1.7B
        (publisher Q8_0 or ggml-org Q4_K_M — owner choice pending);
        second candidate = Qwen3-4B Q4_K_M; comparison = Granite 4.0 Micro Q4_K_M;
        Phi-4 community GGUF and Qwen3.5-2B deferred/rejected for first gate;
        provisional recommendation remains pending owner approval
Outstanding approval gates: runtime install; model download; local benchmark
Limitations: no runtime installed; no weights downloaded; no benchmark metrics;
             installation not authorized; model download not authorized;
             ADR 0003 remains Proposed; Phase 3B remains in progress;
             Phase 4 not started
Artifact references: docs/PHASE_3B_MODEL_RUNTIME_RESEARCH.md,
                      docs/PHASE_3B_INSTALLATION_RUNBOOK.md,
                      docs/adr/0003-first-local-model-strategy.md,
                      docs/PHASE_STATUS.md
Reproduction command: n/a (documentation/research entry)
```

### EXP-3B-002 — Owner-approved baseline selection

```text
Experiment ID: EXP-3B-002
Date: 2026-08-05
Git commit: (Phase 3B selection branch tip)
Runtime mode: n/a — documentation and governance event only
Dataset: n/a
Model/provider: none installed; none downloaded; none executed
Neuromorphic backend: n/a
Hardware: unchanged inventory baseline (i7-1165G7 / Iris Xe / ~16 GiB / no CUDA)
Configuration: no runtime; no weights; owner selection recorded only
Metrics: none (no inference; no token/s; not a completed inference experiment)
Owner approval scope: OWNER-APPROVED FIRST BASELINE FOR PRE-INSTALLATION
                      VERIFICATION ONLY
Runtime selection: llama.cpp b9968 Windows x64 CPU-only
Runtime source revision: 1d1d9a9ed7a4f09c4225ea4cc8fd3bd1cf2c940f
Expected runtime archive: llama-b9968-bin-win-cpu-x64.zip
Model selection: Qwen3-1.7B-Q4_K_M.gguf
Model repository: ggml-org/Qwen3-1.7B-GGUF
Model repository revision: daeb8e2d528a760970442092f6bf1e55c3b659eb
Expected model size: 1282439264 bytes
Expected model SHA256: d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5
Original publisher: Qwen Team / Alibaba Cloud
Quantizer: ggml-org
Licence: Apache License 2.0
Result: documentation-only recording of owner-approved first baseline;
        purpose limited to transport/integration/safety/provenance/rollback/
        baseline-performance validation after later explicit install authorization
Outstanding authorization gates: read-only pre-install checklist;
        runtime archive SHA verification; install/download authorization;
        execution; capability verification; real-model evaluation
Limitations: no runtime downloaded; no runtime installed; no model downloaded;
             no weights downloaded; no runtime executed; no inference;
             no benchmark metrics; capabilities unverified;
             ADR 0003 remains Proposed; Phase 3B remains in progress;
             Phase 4 not started
Artifact references: docs/PHASE_3B_INSTALLATION_RUNBOOK.md,
                      docs/PHASE_3B_MODEL_RUNTIME_RESEARCH.md,
                      docs/adr/0003-first-local-model-strategy.md,
                      docs/PHASE_STATUS.md,
                      docs/PHASE_3_ENGINEERING_SPEC.md
Reproduction command: n/a (documentation/governance entry)
```
