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

### EXP-3B-011 — Gate E breadth evaluation (pinned Qwen + SIONA runtime)

```text
Experiment ID: EXP-3B-011
Date: 2026-08-06
Git commit: (this PR head)
Runtime mode: legacy + governed identity guard + local openai_chat provider
Dataset: Gate E catalogue (34 evaluations)
Model/provider: Qwen3-1.7B-Q4_K_M via llama.cpp b9968 (loopback only)
Hardware: CPU-only (ngl 0), Intel i7-class laptop
Configuration: SSN_OFFLINE=1; one historical real run; offline integrity correction only thereafter
Metrics: authoritative counts in docs/evidence/EXP-3B-011_SUMMARY.json (native text recomputed; JSON exact-schema 6/6 separately recorded; native JSON capability NOT_VERIFIED without original provider-origin proof; safety 8/8; runtime recomputed; streaming UNSUPPORTED)
Result: Gate E execution complete after strict re-adjudication; mandatory safety/runtime met; registry NOT activated; ADR 0003 remains PROPOSED; Phase 3B remains IN PROGRESS
Evidence: OPERATOR_LOCAL_OUTSIDE_GIT (complete evidence in configured operator-local EXP-3B-011 report directory outside the repository); committed docs/evidence/EXP-3B-011_*
Outstanding: model-registry activation review; ADR 0003; Phase 3B completion
Limitations: Original JSON runner lacked captured provider fallback/origin observation; streaming unsupported; not production ready; not a SIONA-native model; no model rerun during integrity correction
Reproduction: python scripts/run_gate_e_breadth_evaluation.py --regenerate-committed-evidence-from-local
```


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
Result: HISTORICAL research-gate outcome — official-source matrix completed
        after coverage and traceability correction;
        provisional runtime direction = llama.cpp Windows CPU baseline (b9968);
        provisional first model family = Qwen3-1.7B
        (publisher Q8_0 or ggml-org Q4_K_M — owner choice then pending);
        second candidate = Qwen3-4B Q4_K_M; comparison = Granite 4.0 Micro Q4_K_M;
        Phi-4 community GGUF and Qwen3.5-2B deferred/rejected for first gate;
        provisional recommendation then pending owner approval
Outstanding approval gates at research gate: runtime install; model download;
        local benchmark
Limitations at research gate (historical; superseded by later owner
             authorization and EXP-3B-003): no runtime then installed;
             no weights then downloaded; no benchmark metrics;
             installation then not authorized; model download then not
             authorized; ADR 0003 remains Proposed; Phase 3B remains in
             progress; Phase 4 not started
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
Outstanding authorization gates at selection gate: read-only pre-install
        checklist; runtime archive SHA verification; install/download
        authorization; execution; capability verification; real-model evaluation
Limitations at selection gate (historical; superseded by EXP-3B-003):
             no runtime then downloaded; no runtime then installed;
             no model then downloaded; no weights then downloaded;
             no runtime then executed; no inference; no benchmark metrics;
             capabilities unverified; ADR 0003 remains Proposed;
             Phase 3B remains in progress; Phase 4 not started
Artifact references: docs/PHASE_3B_INSTALLATION_RUNBOOK.md,
                      docs/PHASE_3B_MODEL_RUNTIME_RESEARCH.md,
                      docs/adr/0003-first-local-model-strategy.md,
                      docs/PHASE_STATUS.md,
                      docs/PHASE_3_ENGINEERING_SPEC.md
Reproduction command: n/a (documentation/governance entry)
```

### EXP-3B-003 — First real local-model loopback baseline

```text
Experiment ID: EXP-3B-003
Date: 2026-08-05
Git commit: (Phase 3B evidence branch tip)
Runtime mode: local operator evidence — llama.cpp loopback only
Dataset: n/a (manual short probes only)
Model/provider: Qwen3-1.7B-Q4_K_M.gguf via llama-server; SIONA provider NOT wired
Neuromorphic backend: n/a
Hardware: i7-1165G7 / Iris Xe / ~16 GiB / no CUDA (CPU-only baseline)
Configuration:
  runtime: llama.cpp b9968 / commit 1d1d9a9ed7a4f09c4225ea4cc8fd3bd1cf2c940f
  archive: llama-b9968-bin-win-cpu-x64.zip (18211732 bytes)
  archive SHA256: f98e6690faad6a8718451d420a63cbfde6c87028beae4e7f35a36a762730cefd (MATCH)
  model: Qwen3-1.7B-Q4_K_M.gguf (1282439264 bytes)
  model SHA256: d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5 (MATCH)
  host: 127.0.0.1
  port: 8080
  context: 4096
  maximum prediction/output setting: 512
  GPU layers: 0
  CPU threads: 4
  reasoning mode: off
  no remote bind; no tool activation; no service/auto-start
Observed process:
  PID during run: 7256
  working set during run: approximately 2349314048 bytes / 2.19 GiB
Transport probes:
  GET /health: HTTP 200
  GET /v1/models: HTTP 200
  basic chat: HTTP 200; returned "Local loopback inference is working."
  arithmetic probe: HTTP 200; response "4"
  (Do not imply general reasoning quality from one arithmetic response.)
Metrics (LOCAL SHORT-PROBE OBSERVATION — NOT A PRODUCTION PERFORMANCE CLAIM):
  approximately 107 prompt tokens/s
  approximately 20 generated tokens/s
  arithmetic probe approximately 0.30 seconds
Shutdown:
  timestamp: 2026-08-05 20:44:44 +03:00
  pre-shutdown PID: 7256
  pre-shutdown working set: 2349314048 bytes
  bind: 127.0.0.1:8080 only
  CloseMainWindow: returned false
  final shutdown method: Stop-Process without -Force
  application-level graceful shutdown: not verified
  normal non-force termination: succeeded
  The first baseline verified normal non-force process termination. It did not
  verify a llama.cpp application-level graceful-shutdown endpoint or protocol.
  final llama-server/llama-cli process count: 0
  final port 8080 state: not listening
  post-shutdown runtime archive hash: MATCH
  post-shutdown model hash: MATCH
Result: installed + artifact-verified + limited loopback smoke completed;
        runtime currently stopped; provider integration pending
Outstanding: SIONA provider integration; registry activation; security /
             structured-output / timeout / streaming / behavioral evaluation;
             capability approval; ADR acceptance
Limitations: capabilities unverified beyond basic transport/inference;
             ADR 0003 remains Proposed; Phase 3B remains in progress;
             Phase 4 not started; CI remains model-free
Artifact references: docs/PHASE_3B_INSTALLATION_RUNBOOK.md,
                      docs/PHASE_3B_MODEL_RUNTIME_RESEARCH.md,
                      docs/adr/0003-first-local-model-strategy.md,
                      docs/PHASE_STATUS.md,
                      docs/PHASE_3_ENGINEERING_SPEC.md
                      (raw local evidence retained outside Git under operator
                      reports directory; not committed)
Reproduction command: n/a (manual local operator procedure; not CI)
```

### EXP-3B-004 — llama.cpp OpenAI-compatible transport implementation

```text
Experiment ID: EXP-3B-004
Date: 2026-08-05
Git commit: (Phase 3B provider-integration branch tip)
Runtime mode: implementation and deterministic mock validation only
Dataset: Phase 3B openai_chat mock HTTP suite + existing Phase 3A provider tests
Model/provider: LocalOpenWeightProvider openai_chat dialect (mock OpenAI server only)
Neuromorphic backend: n/a
Hardware: n/a for this implementation gate (no real runtime exercised)
Configuration:
  default dialect: siona_generate
  opt-in dialect: openai_chat via SSN_LOCAL_MODEL_API_DIALECT
  no SSN_MODEL_PROVIDER activation required for unit tests
  no real endpoint contacted; ephemeral loopback mock servers only
Metrics: unittest pass/fail only (no token/s claims)
Result: IMPLEMENTED AND TESTED AGAINST DETERMINISTIC MOCKS;
        REAL-RUNTIME PROVIDER VALIDATION PENDING
Evidence covered by mocks:
  OpenAI request/response mapping
  exact model-ID verification
  fail-closed health (ok is True or status == "ok")
  timeout hard bounds and gateway margin
  output / temperature / port / model-id bounds
  deterministic fallback retained on transport failure
Outstanding: real-runtime activation against stopped llama.cpp baseline;
             registry activation; governed real-model evaluation;
             capability approval; ADR acceptance
Limitations: no real runtime started; no GGUF loaded; no real inference;
             registry inactive; capabilities unverified;
             ADR 0003 remains Proposed; Phase 3B remains in progress;
             Phase 4 not started; CI remains model-free
Artifact references: docs/SIONA_MODEL_GATEWAY.md,
                      docs/PHASE_STATUS.md,
                      docs/PHASE_3_ENGINEERING_SPEC.md,
                      docs/adr/0003-first-local-model-strategy.md,
                      ssn/cognition/model_gateway/local_provider.py,
                      ssn/tests/test_phase3b_openai_chat_transport.py
Reproduction command: SSN_OFFLINE=1 python scripts/run_tests.py
```

### EXP-3B-005 — Controlled real SIONA provider validation

```text
Experiment ID: EXP-3B-005
Date: 2026-08-05
Git commit: (Phase 3B real-provider-validation branch tip)
Runtime mode: controlled temporary local validation (loopback only)
Dataset: bounded text / structured-JSON / tool-safety probes via SIONA provider
Model/provider: LocalOpenWeightProvider openai_chat → llama.cpp b9968 →
                Qwen3-1.7B-Q4_K_M.gguf (pinned)
Neuromorphic backend: n/a
Hardware: Intel i7-1165G7, Iris Xe, CPU-only (ngl 0); AC power during run
Configuration:
  bind 127.0.0.1:8080; ctx 4096; threads 4; n-predict 512; reasoning off
  SSN_OFFLINE=1; SSN_LLM_PROVIDER=local; SSN_MODEL_PROVIDER=local
  SSN_LOCAL_MODEL_API_DIALECT=openai_chat
  SSN_LOCAL_MODEL_ENDPOINT=http://127.0.0.1:8080
  SSN_LOCAL_MODEL_ID=<exact /v1/models id>
  SSN_LOCAL_MODEL_VERIFY_MODEL_ID=1; max_tokens_cap=128; timeout_s=30
  ALLOW_REMOTE=0; process-local env only (not persisted)
Metrics: LOCAL SHORT-PROBE OBSERVATION — NOT A PRODUCTION PERFORMANCE CLAIM
  direct-provider wall ~1.07 s (prompt 29 / completion 12 / total 41)
  LanguageEngine wall ~1.10 s
  readiness working-set sample approximately 2.16 GiB
  highest later probe-window sample approximately 1.75 GiB
  overall maximum observed across recorded samples approximately 2.16 GiB
  (not a generalized performance benchmark)
Result: IMPLEMENTED AND VALIDATED AGAINST THE PINNED LOCAL RUNTIME;
        LIMITED TEXT-TRANSPORT GATE ONLY;
        BROAD CAPABILITIES AND PRODUCTION CERTIFICATION PENDING
Evidence:
  SIONA Core → LanguageEngine → ModelGateway → LocalOpenWeightProvider
    → llama.cpp → Qwen text path reached
  Exact /v1/models model-ID verification succeeded
  Direct provider text probe healthy; fallback_used=false
  LanguageEngine end-to-end used real local provider (not dummy/deterministic)
  Structured JSON probe: observed failure (markdown-fenced text; structured=null);
    structured JSON capability remains UNVERIFIED
  Tool-call safety: tool_calls returned by provider = 0; no ToolGateway connect
  Shutdown: Stop-Process without -Force; final llama-server count 0;
    final llama-cli count 0; port 8080 not listening;
    application-level graceful shutdown not verified
  Deterministic fallback verified after shutdown (fallback_used=true; no restart)
  Offline tests 308 passed / 4 skipped; production eval 7/7; HTTP smoke OK
Outstanding: model registry activation; broad capability verification;
             Gate E real-model evaluation suite; ADR 0003 acceptance;
             Phase 3B completion
Limitations: limited text-transport gate only; structured JSON unverified;
             registry inactive; capabilities limited/unverified beyond observed
             text path; ADR 0003 remains Proposed; Phase 3B remains in progress;
             Phase 4 not started; runtime currently stopped; CI remains model-free;
             application-level graceful shutdown not verified
Artifact references: docs/PHASE_3B_INSTALLATION_RUNBOOK.md,
                      docs/PHASE_STATUS.md,
                      docs/PHASE_3_ENGINEERING_SPEC.md,
                      docs/SIONA_MODEL_GATEWAY.md,
                      docs/adr/0003-first-local-model-strategy.md
                      (raw local evidence retained outside Git under operator
                      reports directory; not committed)
Reproduction command: n/a (manual local operator procedure; not CI)
```

### EXP-3B-006 — Governed prompt-context bridge

```text
Experiment ID: EXP-3B-006
Date: 2026-08-06
Git commit: (feat/governed-prompt-context-bridge tip)
Runtime mode: offline deterministic / mock validation only
Dataset: synthetic IdentityFactRecord fixtures only (no real personal facts)
Model/provider: LocalDummyLLMProvider + mock ModelGateway path; no GGUF load
Neuromorphic backend: n/a
Hardware: n/a for this experiment (no local model started)
Configuration:
  SSN_OFFLINE=1
  SSN_GOVERNED_CONTEXT default 0 (legacy unchanged); tests enable =1
  LanguageEngine → GovernedContextLLMProvider → existing LLMProvider/ModelGateway
Metrics: none (no live inference campaign)
Result: IMPLEMENTED AND VALIDATED AGAINST DETERMINISTIC PROVIDERS ONLY; NO ACTIVE PERSONAL RECORDS; NO MODEL TRAINING; NO REGISTRY ACTIVATION; REAL LOCAL-MODEL CONTEXT CAMPAIGN NOT STARTED.
Evidence:
  Composite authorization (MODEL_PROMPT ∩ PUBLIC_RESPONSE / OWNER_ASSISTANCE)
  Trusted PolicyContext required; role text alone is not authentication
  Fail-closed malformed record/consent handling without exceptions
  Exact consent resolution; ambiguous duplicate consent denies
  Hard assembler ceilings enforced (GovernedContextConfigError)
  Deterministic JSON-lines context serialization
  Exact legacy LanguageEngine contract when feature disabled or unused
  used_context true only when governed block included or ordinary context used
  Diagnostics count invariant (included + denied = candidates)
  Sanitized correlation request_id (64 chars, conservative charset)
  Denied statements absent from downstream prompts and diagnostics
  Final bounded-input hardening: max 16 candidate inspection, structural
  preflight for typed records/consents, delegated-consent-only scope,
  envelope input_error_reason for untrustworthy counts, used_context fallback
  Focused suite 73 pass; full offline suite pass
  No HTTP/subprocess/llama.cpp/GGUF activity in focused tests
  No ssn/data or world_model.json mutation
Outstanding: active approved identity-record ingestion (separate approval);
             real local-model governed-context campaign (separate approval);
             registry activation; Gate E; ADR 0003 acceptance; Phase 3B completion
Limitations: deterministic providers only; no active personal records;
             ADR 0003 remains Proposed; Phase 3B remains in progress;
             Phase 4 not started; runtime currently stopped; CI remains model-free
Artifact references: docs/SIONA_GOVERNED_PROMPT_CONTEXT.md,
                      docs/PHASE_STATUS.md,
                      docs/PHASE_3_ENGINEERING_SPEC.md,
                      docs/SIONA_MODEL_GATEWAY.md,
                      ssn/governance/runtime_context.py,
                      ssn/tests/test_governed_runtime_context.py
Reproduction command: SSN_OFFLINE=1 python -m unittest ssn.tests.test_governed_runtime_context
```

### EXP-3B-007 — First approved public identity registry

```text
Experiment ID: EXP-3B-007
Date: 2026-08-06
Git commit: 6aba5119989846afef4328141d688e19cdd96f1f
Runtime mode: offline deterministic validation only
Dataset: three owner-approved public IdentityFactRecord entries in
          config/governance/approved_identity_records.json
Model/provider: none; LocalDummyLLMProvider for integration tests only
Neuromorphic backend: n/a
Hardware: n/a (no local model started)
Configuration:
  SSN_OFFLINE=1
  Explicit ApprovedIdentityRegistry retrieval → GovernedContextInput only
Metrics: none (no live inference campaign)
Result: IMPLEMENTED AND VALIDATED DETERMINISTICALLY; THREE OWNER-APPROVED PUBLIC IDENTITY RECORDS AVAILABLE THROUGH EXPLICIT GOVERNED RETRIEVAL; NO AUTOMATIC MODEL INJECTION; NO MODEL TRAINING; NO EMBEDDINGS; NO MODEL REGISTRY ACTIVATION; REAL LOCAL-MODEL IDENTITY CAMPAIGN NOT STARTED.
Evidence:
  config/governance/approved_identity_records.json (schema_version 1, 3 records)
  Strict atomic loader with file-size and record-count bounds
  Independent canonical manifest (_APPROVED_MANIFEST MappingProxyType) pins exact
  approved fields; entries frozen; tampered statement/metadata/uses fail atomically
  Strict JSON object_pairs_hook rejects duplicate keys at all object levels
  notes absent or exact empty only; JSON null rejected (registry_record_invalid_notes)
  Bounded stat-first file read max 65537 bytes (no unrestricted Path.read_bytes)
  select_by_subject_ids: plain list/tuple only; max 16 IDs; exact casing
  Explicit retrieval API (no LanguageEngine auto-injection)
  GovernedContextAssembler integration for PUBLIC_RESPONSE guest path
  decide_public / decide_model_prompt permit; decide_training denies
  PUBLIC_WEBSITE not in intended uses; personal contact markers excluded
  Focused suite 99 pass; full offline suite 550 pass, 4 skipped
  No network/subprocess/llama.cpp/GGUF in focused tests
  No ssn/data or world_model.json mutation
Outstanding: real local-model identity campaign; model registry activation;
             Gate E; ADR 0003 acceptance; Phase 3B completion; website-specific
             PUBLIC_WEBSITE approval (separate)
Limitations: deterministic providers only; no embeddings; no active personal
             contacts in registry; ADR 0003 Proposed; Phase 3B in progress;
             Phase 4 not started
Artifact references: docs/SIONA_APPROVED_IDENTITY_REGISTRY.md,
                      config/governance/approved_identity_records.json,
                      ssn/governance/identity_registry.py,
                      ssn/tests/test_approved_identity_registry.py
Reproduction command: SSN_OFFLINE=1 python -m unittest ssn.tests.test_approved_identity_registry
```

### EXP-3B-008 — Controlled real-Qwen governed identity campaign

```text
Experiment ID: EXP-3B-008
Date: 2026-08-06
Git commit: (feat/real-qwen-governed-identity-campaign tip)
Runtime mode: temporary loopback llama.cpp b9968 + Qwen3-1.7B-Q4_K_M
Dataset: 26 governed identity probes via scripts/run_real_governed_identity_campaign.py
Model/provider: pinned local open-weight Qwen baseline; openai_chat dialect
Neuromorphic backend: n/a
Hardware: Intel i7-1165G7, CPU-only (ngl=0)
Configuration:
  SSN_ALLOW_REAL_MODEL_CAMPAIGN=1, SSN_GOVERNED_CONTEXT=1
  explicit ApprovedIdentityRegistry selection + GovernedContextInput only
  loopback http://127.0.0.1:8080; max_tokens_cap=128; reasoning off
Metrics: per-probe latency; classifications; used_context; fallback flags
Result: CONTROLLED REAL LOCAL-MODEL GOVERNED-IDENTITY CAMPAIGN EXECUTED AGAINST
        THE PINNED QWEN3-1.7B BASELINE. POSITIVE IDENTITY GROUNDING WAS OBSERVED IN
        THE CAPTURED SANITIZED RESPONSE EXCERPTS, BUT CAMPAIGN ACCEPTANCE WAS NOT MET.
        SELECTION-BOUNDARY, CONTRADICTION, CONTEXT-DISCLOSURE,
        UNSUPPORTED-FABRICATION, ACTION-NARRATIVE AND STRUCTURED-JSON FAILURES WERE
        OBSERVED. COMPLETE MODEL RESPONSES WERE NOT RETAINED, SO ADJUDICATION IS
        LIMITED TO CAPTURED EXCERPTS AND RECORDED METADATA. THREE APPROVED RECORDS
        WERE SUPPLIED ONLY THROUGH EXPLICIT GOVERNED RETRIEVAL. NO AUTOMATIC MODEL
        INJECTION, MODEL TRAINING, EMBEDDINGS, MODEL-REGISTRY ACTIVATION OR TOOL
        EXECUTION OCCURRED. RUNTIME WAS SHUT DOWN AFTER TESTING.
Evidence:
  scripts/run_real_governed_identity_campaign.py
  ssn/governance/identity_campaign.py
  docs/evidence/EXP-3B-008_ADJUDICATION.json (operator-reviewed, excerpts only)
  docs/evidence/EXP-3B-008_EVIDENCE_MANIFEST.json (hashes; sanitized excerpts)
  Local evidence: C:\Users\njaji\SIONA\reports\EXP-3B-008 (unchanged; not in Git)
  Evidence type: SANITIZED_TRUNCATED_RESPONSE_EXCERPTS (240-char max per probe)
  Final adjudication: positive 8/8 excerpts; selection 3/4; unsupported 5/6;
    instruction 0/4; no-context injection 3/0; no-context answer quality 2/1 (N2)
  N2 passed injection boundary but fabricated profile in captured excerpt
  Provider tool-call count NOT_CAPTURED_IN_ORIGINAL_RUN; token usage UNAVAILABLE
  Actual tool executions: 0; website unchanged
  Shutdown: force stop after graceful wait; post-shutdown deterministic fallback OK
Outstanding: Gate E breadth; structured JSON verification; real-Qwen retest of
             hardened guard; model registry activation; ADR 0003 acceptance;
             Phase 3B completion
Limitations: single campaign session; STRUCTURED JSON UNVERIFIED; not production ready
Artifact references: docs/SIONA_REAL_QWEN_IDENTITY_CAMPAIGN.md
Reproduction command: operator starts llama-server then python scripts/run_real_governed_identity_campaign.py
```

### EXP-3B-009 — Deterministic governed identity response hardening

```text
Experiment ID: EXP-3B-009
Date: 2026-08-06
Git commit: (feat/governed-identity-response-hardening tip)
Runtime mode: offline deterministic / mock validation only
Dataset: synthetic replay of EXP-3B-008 failure classes (mocked providers)
Model/provider: scripted LocalDummy / mock LLMProvider only; no GGUF load
Neuromorphic backend: n/a
Hardware: n/a (no local model started)
Configuration:
  SSN_OFFLINE=1
  SSN_GOVERNED_CONTEXT=1 for guarded path tests
  Explicit GovernedIdentityResponseContract + GovernedContextInput only
Metrics: none (no live inference campaign)
Result: IMPLEMENTED AND VALIDATED OFFLINE — EXPLICIT GOVERNED IDENTITY RESPONSE
        CONTRACT, STRICT INCLUDED-RECORD VALIDATION, PRE-PROVIDER SAFETY
        DECISIONS, CANONICAL POST-PROVIDER GROUNDING VALIDATION,
        PROVIDER-FAILURE CONTAINMENT AND DETERMINISTIC TEXT/JSON FALLBACK ADDED.
        OVERSIZED PROMPTS AND RESPONSES, PROVIDER FALLBACKS, TOOL PROPOSALS,
        RESPONSE-CONTRACT BYPASSES AND THE HISTORICAL EXP-3B-008 FAILURE CLASSES
        ARE COVERED BY MOCKED DETERMINISTIC TESTS. NO REAL MODEL WAS STARTED OR
        RERUN. MODEL-NATIVE STRUCTURED JSON REMAINS UNVERIFIED. NO MODEL
        TRAINING, ADAPTER TRAINING, EMBEDDINGS, MODEL-WEIGHT CHANGES OR
        MODEL-REGISTRY ACTIVATION OCCURRED.
Evidence:
  ssn/governance/identity_response_guard.py
  docs/SIONA_GOVERNED_IDENTITY_RESPONSE_GUARD.md
  ssn/tests/test_governed_identity_response_guard.py
  Additive GovernedContextInput.response_contract; max 1 model inference
  Canonical text grounding; included-record validation; provider containment
  JSON mode: exactly one subject; blocked JSON returns refusal text
  Deterministic JSON schema fallback marks MODEL-NATIVE JSON UNVERIFIED
Outstanding: real-Qwen retest under guard; model registry activation; Gate E;
             ADR 0003 acceptance; Phase 3B completion
Limitations: offline mocks only; does not claim EXP-3B-008 acceptance passed;
             does not claim Qwen itself was fixed; not production ready
Artifact references: docs/SIONA_GOVERNED_IDENTITY_RESPONSE_GUARD.md,
                      docs/SIONA_GOVERNED_PROMPT_CONTEXT.md,
                      docs/SIONA_REAL_QWEN_IDENTITY_CAMPAIGN.md
Reproduction command: SSN_OFFLINE=1 python -m unittest ssn.tests.test_governed_identity_response_guard
```

### EXP-3B-010 — Controlled real-Qwen guarded-path retest

```text
Experiment ID: EXP-3B-010
Date: 2026-08-06
Git commit: (feat/real-qwen-guarded-identity-retest tip)
Runtime mode: real local pinned Qwen3-1.7B via llama.cpp b9968; loopback only
Dataset: fixed 21-probe guarded identity catalogue (P/S/U/A/N/J)
Model/provider: Qwen3-1.7B-Q4_K_M.gguf; openai_chat dialect; max_tokens=128
Neuromorphic backend: n/a
Hardware: local CPU-only (n_gpu_layers=0)
Configuration:
  SSN_OFFLINE=1
  SSN_GOVERNED_CONTEXT=1
  SSN_LLM_PROVIDER=local / SSN_MODEL_PROVIDER=local
  SSN_LOCAL_MODEL_ENDPOINT=http://127.0.0.1:8080
  SSN_LOCAL_MODEL_MAX_TOKENS=128
  Explicit --confirm-real-model-campaign required
Metrics:
  guarded_campaign_acceptance_met=true (21/21)
  pinned_baseline_model_native_json_verified=false (0/6 MODEL_VALIDATED; 6/6 fallback)
  guarded_provider_inference_count=10; preflight_block_count=11
  actual_tool_execution_count=0; website_changed=false; registry_active=false
Result: CONTROLLED REAL LOCAL-MODEL GUARDED-PATH RETEST EXECUTED AGAINST THE
        PINNED QWEN3-1.7B BASELINE. ALL 21 FINAL SIONA-GUARDED RESPONSES PASSED
        THE DEFINED IDENTITY, SELECTION, UNSUPPORTED-INFORMATION,
        INSTRUCTION-RESISTANCE, NO-RECORD AND STRUCTURED-OUTPUT BOUNDARIES.
        TWO REAL MODEL OUTPUTS WERE ACCEPTED DIRECTLY; NINETEEN FINAL RESPONSES
        USED DETERMINISTIC GUARD CONTAINMENT. ALL SIX JSON PROBES REQUIRED
        DETERMINISTIC FALLBACK, SO MODEL-NATIVE STRUCTURED JSON REMAINS
        UNVERIFIED. COMPLETE RAW QWEN RESPONSES AND FINAL SIONA RESPONSES WERE
        RETAINED IN AN OPERATOR-LOCAL DIRECTORY OUTSIDE GIT. COMMITTED EVIDENCE
        CONTAINS ONLY SANITIZED TRUNCATED EXCERPTS, PER-RESPONSE HASHES AND
        STRICTLY RECOMPUTED ADJUDICATION METADATA. THE MODEL ARTIFACT WAS
        VERIFIED BY PINNED SIZE AND SHA-256; THE PROVIDER WAS BOUND TO THE
        SINGLE SERVER-REPORTED MODEL ID, BUT AN INDEPENDENT EXPECTED SERVER-ID
        MATCH WAS NOT ESTABLISHED. RUNTIME PROCESS TERMINATION COMPLETED AND
        POST-RUN LOCAL PROCESS/PORT STATE WAS VERIFIED CLOSED; THE ORIGINAL
        RUNNER'S SHUTDOWN-LOG PATH REPORTED AN ERROR AND HAS BEEN CORRECTED FOR
        FUTURE REPRODUCTIONS. NO TOOL EXECUTION, WEBSITE CHANGE, TRAINING,
        ADAPTER TRAINING, EMBEDDINGS, MODEL-WEIGHT CHANGE OR MODEL-REGISTRY
        ACTIVATION OCCURRED.
Evidence:
  docs/evidence/EXP-3B-010_ADJUDICATION.json
  docs/evidence/EXP-3B-010_SUMMARY.json
  docs/evidence/EXP-3B-010_EVIDENCE_MANIFEST.json
  docs/SIONA_REAL_QWEN_GUARDED_RETEST.md
  Local complete responses: OPERATOR_LOCAL_OUTSIDE_GIT
  Hash semantics: CANONICAL_JSON_SHA256
Outstanding: Gate E breadth; model-registry activation review; ADR 0003
             acceptance; Phase 3B completion decision
Limitations: does not claim Qwen was trained or fixed; does not claim SIONA is
             a native model; not production ready; Gate E not started;
             model registry remains inactive; ADR 0003 remains Proposed;
             independent server-ID match was not established
Artifact references: docs/SIONA_REAL_QWEN_GUARDED_RETEST.md,
                      docs/SIONA_GOVERNED_IDENTITY_RESPONSE_GUARD.md,
                      docs/SIONA_REAL_QWEN_IDENTITY_CAMPAIGN.md
Reproduction command: python scripts/run_real_guarded_identity_retest.py --regenerate-committed-evidence-from-local
```

### EXP-3B-012 — Model registry activation review

```text
Experiment ID: EXP-3B-012
Date: 2026-08-07
Git commit: (feat/model-registry-activation-review tip)
Runtime mode: offline registry validation and provider-binding review only
Dataset: n/a
Model/provider: Qwen3-1.7B-Q4_K_M metadata binding only; no runtime startup
Configuration:
  SSN_OFFLINE=1
  Canonical manifest: config/model_registry.json
  Exact composite binding: siona-local-open-weight-v1 + Qwen3-1.7B-Q4_K_M
Metrics:
  review_decision=ACTIVATION_RECOMMENDED_WITH_CONSERVATIVE_CAPABILITIES
  chat=true; tools=false; structured_json=false; streaming=false; multimodal=false
  verified_context_window=4096
  artifact_verification_status=verified; capability_verification_status=verified
  runtime_startup_count=0; network_model_calls=0; subprocess_starts=0; gguf_reads=0
Result: MODEL-REGISTRY ACTIVATION REVIEW PASSED WITH CONSERVATIVE CAPABILITY
        BINDING. THE APPROVED QWEN3-1.7B BASELINE MAY BE REPRESENTED AS A LOCAL
        OPTIONAL OPEN-WEIGHT REGISTRY ENTRY. VERIFIED REGISTRY CAPABILITIES ARE
        LIMITED TO BOUNDED TEXT/CHAT INFERENCE AT THE LOCALLY TESTED 4096 CONTEXT.
        TOOLS, STRUCTURED JSON, STREAMING AND MULTIMODAL CAPABILITIES REMAIN FALSE.
        REGISTRY BINDING DOES NOT START THE MODEL RUNTIME, DOES NOT GRANT TOOL
        AUTHORITY, AND DOES NOT MAKE THE EXTERNAL MODEL SIONA-NATIVE.
Evidence:
  docs/SIONA_MODEL_REGISTRY_ACTIVATION_REVIEW.md
  docs/evidence/EXP-3B-012_MODEL_REGISTRY_REVIEW.json
  config/model_registry.json
Outstanding: operator-controlled runtime startup (state C); ADR 0003 acceptance;
             Phase 3B completion decision
Limitations: native text 9/12 VERIFIED (T03/T06/T07 fail); native JSON NOT_VERIFIED;
             not production ready; ADR 0003 remains Proposed; Phase 4 not started
Artifact references: docs/SIONA_MODEL_REGISTRY_ACTIVATION_REVIEW.md,
                      docs/SIONA_GATE_E_BREADTH_EVALUATION.md,
                      docs/evidence/EXP-3B-011_SUMMARY.json
Reproduction command: SSN_OFFLINE=1 python -m unittest ssn.tests.test_phase3b_model_registry_activation
```
