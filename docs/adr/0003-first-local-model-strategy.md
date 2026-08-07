# ADR 0003 — First local model strategy

## Status

Proposed

## Context

Phase 3A delivered an optional `LocalOpenWeightProvider`, registry provenance
schema, sanitization boundary, loopback policy and deterministic evaluation
scaffold — without installing a real runtime or downloading weights.

Phase 3B must decide whether and how SIONA Core may use a first optional
open-weight language model on constrained local hardware (CPU-first laptop,
Intel Iris Xe, ~16 GiB RAM, no CUDA).

SIONA Core is an independent hybrid intelligence platform. An external
pretrained model may supply language/reasoning capability, but it is not
SIONA's identity, authority model, memory, policy or embodiment architecture.
SIONA does not currently own a trained foundation model.

## Decision

1. SIONA may initially use a **replaceable external open-weight language model**
   as an optional reasoning engine behind the existing `ModelGateway`.
2. Model and runtime selection must be **evidence-based**, using official-source
   research, hardware fit, licence/provenance checks and measured evaluations.
3. The provider abstraction prevents permanent architectural dependence on any
   single runtime or checkpoint.
4. SIONA-specific adaptation (adapters/fine-tunes) and future SIONA-native model
   work remain **separate stages** and are not approved by this ADR.
5. **No final runtime or model is approved by this ADR yet.**

## Official-source research outcome (2026-08-05)

Research recorded in
[PHASE_3B_MODEL_RUNTIME_RESEARCH.md](../PHASE_3B_MODEL_RUNTIME_RESEARCH.md).

### Historical pre-install runtime direction

*(State at the official-source research gate, before owner download/install
authorization.)*

- **Primary first baseline:** llama.cpp native Windows x64 CPU build
- **Later experiment only:** llama.cpp SYCL on Intel Iris Xe (no speed claim)
- **Convenience comparison:** Ollama (deferred as first controlled baseline)
- **Intel-optimized alternative research path:** OpenVINO GenAI (deferred)

CPU baseline comes first because it minimizes driver/toolchain variables and
preserves exact binary + model-file control. SYCL remains experimental until
local benchmark. A background service is not preferred for the first controlled
baseline.

### Historical pre-install model direction

*(State at the official-source research gate, before owner download/install
authorization.)*

- **Primary first integration candidate:** Qwen3-1.7B (transport/integration gate)
  - Publisher GGUF currently publishes **Q8_0** (not Q4_K_M)
  - Requested Q4_K_M exists on **ggml-org** with distinct quantizer attribution
- **Second capability candidate:** Qwen3-4B Q4_K_M (official Qwen GGUF)
- **Additional comparison:** IBM Granite 4.0 Micro Q4_K_M (official IBM GGUF)

External models remain optional and replaceable. No SIONA-native foundation
model claim is made.

## Owner-approved Phase 3B baseline

**Historical owner-selection gate:** OWNER-APPROVED FOR PRE-INSTALLATION VERIFICATION ONLY

**Current local evidence:** OWNER-AUTHORIZED DOWNLOAD AND PORTABLE INSTALLATION COMPLETED; ARTIFACT-VERIFIED LOCALLY; LIMITED LOOPBACK EXECUTION COMPLETED; OPENAI_CHAT TRANSPORT IMPLEMENTED; CONTROLLED REAL-PROVIDER TEXT PATH VALIDATED (EXP-3B-005); GATE E BREADTH RECORDED (EXP-3B-011); MODEL-REGISTRY ACTIVATION REVIEW PASSED (EXP-3B-012); REGISTRY RECORD AVAILABLE; BINDING SOFTWARE SUPPORTED; RUNTIME CURRENTLY STOPPED; STATE C REAL-RUNTIME VERIFICATION PENDING

These subsections above describe the state at the official-source research gate.
The owner subsequently issued explicit download/install/execution authorization.
The selected baseline is now locally installed and artifact-verified. Limited
loopback execution completed. The `openai_chat` transport was implemented and
merged. Controlled real-provider text-path validation (EXP-3B-005) succeeded,
then the runtime was stopped. Gate E breadth was recorded (EXP-3B-011).
Model-registry activation review passed with conservative capability binding
(EXP-3B-012). This later work does **not** constitute ADR acceptance. State C
registry-bound real-runtime verification, ADR acceptance, Phase 3B completion
and production certification remain pending. ADR status remains **Proposed**.

| Item | Exact recorded value |
|------|----------------------|
| Runtime family | llama.cpp |
| Runtime release | b9968 |
| Runtime source revision | `1d1d9a9ed7a4f09c4225ea4cc8fd3bd1cf2c940f` |
| Runtime platform | Windows x64 CPU-only |
| Expected runtime archive | `llama-b9968-bin-win-cpu-x64.zip` |
| Model family | Qwen3-1.7B |
| Model artifact | `Qwen3-1.7B-Q4_K_M.gguf` |
| Model repository | `ggml-org/Qwen3-1.7B-GGUF` |
| Model repository revision | `daeb8e2d528a760970442092f6bf1e55c3b659eb` |
| Expected model size | 1282439264 bytes |
| Expected model SHA256 | `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5` |
| Original publisher | Qwen Team / Alibaba Cloud |
| Quantizer | ggml-org |
| Model licence | Apache License 2.0 |
| Purpose | Transport, integration, safety, provenance, rollback and baseline-performance validation only |

Clarifications:

- The external model remains optional and replaceable behind `ModelGateway`.
- No SIONA-native model claim is made.
- Capability verification remains separate from artefact verification.
- Failure of this baseline must not require a SIONA Core redesign.
- State C registry-bound real-runtime verification, ADR acceptance and Phase 3B
  completion remain **outstanding** (EXP-3B-011/012 are recorded, not
  production certification).

## Local evidence (2026-08-05) — necessary but not sufficient

Local operator evidence recorded outside Git (summarized in governed docs):

- Artifact installation and checksum verification **passed** (runtime archive
  and model SHA256 **MATCH**)
- Portable CPU-only runtime loaded the selected model on loopback
- Limited loopback probes **passed** (`/health`, `/v1/models`, basic chat,
  arithmetic smoke)
- `openai_chat` transport implementation **merged**
- Controlled real-provider text path **validated** (EXP-3B-005): exact
  `/v1/models` model-ID verification passed; LanguageEngine reached
  llama.cpp/Qwen through ModelGateway; direct text without fallback; tool
  proposals remained absent
- Runtime **stopped** after validation
- Deterministic fallback **passed** after shutdown
- Structured JSON probe **failed** and remains **unverified**
- Normal non-force process termination **passed**
- Application-level graceful shutdown was **not** verified

These results are **necessary but not sufficient** for changing ADR status from
**Proposed** to Accepted.

### Why ADR status remains Proposed

**Current blocker before ADR acceptance:**

- State C controlled registry-bound real-runtime verification.

**Then (after State C):**

- ADR 0003 acceptance decision;
- Phase 3B completion decision.

**Recorded evidence and conservative limits (not additional Phase 3B closeout blockers):**

- Registry record availability and exact binding software support are complete under EXP-3B-012. Model registry remains inactive at runtime (state C) until that separate authorized verification.
- Gate E breadth recorded (EXP-3B-011); model-registry activation review passed (EXP-3B-012); ADR acceptance still pending
- Identity-guard model-native JSON remains unverified under EXP-3B-010. EXP-3B-011 retained six JSON outputs that passed exact parsing/schema validation, but native JSON capability remains NOT_VERIFIED because the original JSON run did not capture the provider-origin/fallback observation required to prove native-model provenance.
- Streaming classified unsupported on the pinned baseline (Gate E R08); registry `streaming=false`
- Registry capabilities remain conservatively bounded: chat=true only at tested 4096 context; tools=false; structured_json=false; streaming=false; multimodal=false
- Broader adversarial/security campaigns beyond the Gate E catalogue remain future hardening / production-certification work, not an additional required blocker for conservative Phase 3B completion
- Production certification is not part of this Phase 3B closeout and is not issued
- Deterministic CI must remain free of real-model dependencies
- No change to owner-control / actuator authority semantics
- Phase 3B remains In Progress; Phase 4 remains Not Started; ADR remains Proposed

### Conditions required before changing ADR status from Proposed

1. Owner-approved artifacts remain pinned and checksum-verified
2. Model registry activation review completes under policy — **passed** EXP-3B-012 with conservative capabilities; operator runtime activation (state C) still separate
3. Gate E provider tests and real-model evaluations are recorded honestly
4. Security and required runtime-resilience gates must pass. Optional behavioural
   capabilities including structured JSON, streaming, tools and multimodal
   support must be evaluated and either explicitly verified or conservatively
   disabled in the registry. An unsupported optional capability is not an ADR
   blocker when it is recorded as false, is not required by the approved runtime
   path, and no higher layer falsely advertises or depends on it. For the
   approved baseline this means: bounded text/chat is the only positively
   verified registry behaviour; context is limited to tested 4096;
   tools=false; structured_json=false; streaming=false; multimodal=false.
5. Deterministic CI remains free of real-model dependencies
6. No change to owner-control / actuator authority semantics

### State C clarification (not automatic startup)

STATE C DOES NOT MEAN AUTOMATIC OR PERMANENT MODEL STARTUP.

State C means a future controlled verification that:

- starts the already pinned llama.cpp/Qwen baseline;
- explicitly enables the local provider;
- loads the canonical registry;
- proves the exact registry entry is bound;
- proves the provider reaches the real pinned model through that binding;
- confirms safe registry observability;
- performs no tool execution;
- keeps loopback-only operation;
- then shuts the runtime down and verifies port/process closure.

This must be a separate authorized experiment after the EXP-3B-012 PR merges.

## Alternatives

| Alternative | Notes |
|-------------|-------|
| Remain deterministic/mock-only indefinitely | Safest for CI; delays optional local capability |
| Cloud-only LLM dependency | Conflicts with local/offline goals and increases external control surface |
| Hard-wire one runtime into core | Creates permanent lock-in; rejected |
| Claim a SIONA-native foundation model now | False; SIONA does not own trained foundation weights |
| Skip provenance/licence gates | Unacceptable for ownership and commercial-use clarity |
| Ollama / LM Studio as first controlled baseline | Deferred — convenience over exact artefact control / service behaviour |
| SYCL-first or Vulkan-first | Deferred — acceleration without CPU baseline evidence |
| Phi-4 community GGUF / Qwen3.5-2B first | Deferred/rejected for first gate — provenance or multimodal complexity |

## Consequences

- Historical research/planning could proceed without installing software; that
  was the research-gate posture, not the current operator state.
- The portable baseline is now **locally installed and artifact-verified** under
  explicit owner authorization; the limited text path was validated
  (EXP-3B-005); the runtime is currently **stopped**.
- Further governed work (state C registry-bound real-runtime verification, ADR
  acceptance, Phase 3B completion) still requires staged approvals in
  [PHASE_3B_INSTALLATION_RUNBOOK.md](../PHASE_3B_INSTALLATION_RUNBOOK.md).
  Gate E (EXP-3B-011) and model-registry activation review (EXP-3B-012) are
  already recorded; optional capabilities remain conservatively disabled where
  not verified.
- CI remains deterministic; real models stay out of hosted gates unless a later
  ADR explicitly changes that policy.
- Capability claims remain conservative until artefact and behavioural
  verification are both recorded; the limited text-transport gate is not
  sufficient for production capability approval.

## Ownership boundaries

- External base weights remain third-party artefacts under their own licences.
- Adapter/checkpoint ownership depends on base-model licence and dataset rights.
- A genuinely SIONA-native model requires SIONA-controlled data, tokenizer,
  training pipeline and evaluation — not merely wrapping an external checkpoint.
- See [PHASE_3B_MODEL_INDEPENDENCE.md](../PHASE_3B_MODEL_INDEPENDENCE.md).

## Security boundaries

- Loopback-only by default; no remote exposure without explicit later approval.
- No automatic startup or automatic model download.
- Tool proposals remain non-authoritative; SIONA policy/permissions decide.
- Secrets must not leave the provider sanitization boundary.
- Owner identity, law, policy and actuator authority are unchanged by this ADR.

## Exit strategy

- Uninstall the runtime and delete weights without rewriting SIONA Core.
- Fall back to deterministic/mock providers.
- Replace the checkpoint or runtime while retaining ModelGateway contracts.

## Future SIONA-native path

Planned progression (not authorized by this ADR):

1. Replaceable external open-weight engine
2. SIONA-approved adapters / fine-tuning
3. SIONA-specialized derived models under recorded provenance
4. Future SIONA-native models trained under SIONA control

## References

- [PHASE_3B_HARDWARE_INVENTORY.md](../PHASE_3B_HARDWARE_INVENTORY.md)
- [PHASE_3B_MODEL_RUNTIME_RESEARCH.md](../PHASE_3B_MODEL_RUNTIME_RESEARCH.md)
- [PHASE_3B_INSTALLATION_RUNBOOK.md](../PHASE_3B_INSTALLATION_RUNBOOK.md)
- [adr/0002-local-open-weight-transport.md](0002-local-open-weight-transport.md)
