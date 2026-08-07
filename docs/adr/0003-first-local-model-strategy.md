# ADR 0003 — First local model strategy

## Status

Accepted (Phase 3B)

## Context

Phase 3A delivered an optional `LocalOpenWeightProvider`, registry provenance
schema, sanitization boundary, loopback policy and deterministic evaluation
scaffold — without installing a real runtime or downloading weights.

Phase 3B had to decide whether and how SIONA Core may use a first optional
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
5. For the accepted Phase 3B baseline, the approved optional local pairing is
   **llama.cpp b9968 + Qwen3-1.7B-Q4_K_M**, bound through the canonical model
   registry and existing provider/gateway boundary. This acceptance is limited
   to the conservative verified capability set recorded below. It is not a
   production-security certification and is not a SIONA-native model claim.

## Official-source research outcome (2026-08-05)

Research recorded in
[PHASE_3B_MODEL_RUNTIME_RESEARCH.md](../PHASE_3B_MODEL_RUNTIME_RESEARCH.md).

### Historical pre-closeout ADR header

For chronology and compatibility with the pre-closeout evidence suite, the ADR
header immediately before the Phase 3B acceptance decision was:

```text
## Status

Proposed
```

This code block is a **historical snapshot only**. The authoritative current
status is the first `## Status` section at the top of this ADR: **Accepted
(Phase 3B)**.

### Historical pre-install runtime direction

*(State at the official-source research gate, before owner download/install
authorization.)*

- **Primary first baseline:** llama.cpp native Windows x64 CPU build
- **Later experiment only:** llama.cpp SYCL on Intel Iris Xe (no speed claim)
- **Convenience comparison:** Ollama (deferred as first controlled baseline)
- **Intel-optimized alternative research path:** OpenVINO GenAI (deferred)

CPU baseline came first because it minimized driver/toolchain variables and
preserved exact binary + model-file control. SYCL remains experimental until a
separate local benchmark. A background service was not selected for the first
controlled baseline.

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

**Accepted Phase 3B state:** OWNER-AUTHORIZED DOWNLOAD AND PORTABLE INSTALLATION COMPLETED; ARTIFACT-VERIFIED LOCALLY; LIMITED LOOPBACK EXECUTION COMPLETED; OPENAI_CHAT TRANSPORT IMPLEMENTED; CONTROLLED REAL-PROVIDER TEXT PATH VALIDATED (EXP-3B-005); GATE E BREADTH RECORDED (EXP-3B-011); MODEL-REGISTRY ACTIVATION REVIEW PASSED (EXP-3B-012); REGISTRY RECORD AVAILABLE; BINDING SOFTWARE SUPPORTED; STATE C CONTROLLED REGISTRY-BOUND REAL-RUNTIME VERIFICATION PASSED (EXP-3B-013); RUNTIME CURRENTLY STOPPED; ADR 0003 ACCEPTED; PHASE 3B COMPLETE

The selected baseline is locally installed and artifact-verified. Limited
loopback execution completed. The `openai_chat` transport was implemented and
merged. Controlled real-provider text-path validation (EXP-3B-005) succeeded,
then the runtime was stopped. Gate E breadth was recorded (EXP-3B-011).
Model-registry activation review passed with conservative capability binding
(EXP-3B-012). State C controlled registry-bound real-runtime verification passed
under EXP-3B-013 and the runtime was shut down afterward. The Phase 3B closeout
accepted this ADR while retaining every recorded capability limitation.
Production certification remains explicitly **not issued** and Phase 4 is not
started automatically by this acceptance.

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
- State C controlled registry-bound real-runtime verification **passed**
  (EXP-3B-013) and the runtime was shut down afterward.
- ADR acceptance does not promote any capability beyond the accepted registry
  matrix.

## Acceptance evidence

Local operator evidence recorded outside Git and governed evidence committed in
Git establish the accepted baseline:

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
- Governed prompt-context, approved-identity, and response-guard work was merged
  and validated through EXP-3B-006 through EXP-3B-010
- Gate E breadth was recorded under EXP-3B-011 with governed safety 8/8 and
  required runtime checks recorded honestly
- Model-registry activation review passed under EXP-3B-012 with exact binding and
  conservative capability advertisement
- State C passed under EXP-3B-013: canonical registry loaded, exact entry bound,
  pinned loopback runtime reached, real bounded text responses returned with no
  fallback or tools, then the runtime shut down and deterministic fallback
  remained available
- Runtime is **stopped** after validation and port 8080 is not left listening
- Deterministic CI remains model-free

### Acceptance basis and retained limitations

ADR 0003 is accepted because all required Phase 3B architectural conditions are
now met while unsupported or unverified optional capabilities remain disabled.
Acceptance therefore records the following conservative boundaries rather than
silently promoting them:

- Registry record availability and exact binding software support are complete
  under EXP-3B-012; State C real-runtime verification passed under EXP-3B-013
- Gate E breadth is recorded under EXP-3B-011
- Identity-guard model-native JSON remains unverified under EXP-3B-010
- EXP-3B-011 retained six JSON outputs that passed exact parsing/schema
  validation, but native JSON capability remains **NOT_VERIFIED** because the
  original provider-origin/fallback observation required to prove native-model
  provenance was not captured
- Streaming is `UNSUPPORTED_ON_PINNED_BASELINE` (Gate E R08)
- Accepted registry capabilities remain: `chat=true` only at tested 4096 context;
  `tools=false`; `structured_json=false`; `streaming=false`; `multimodal=false`
- Broader adversarial/security campaigns beyond the Gate E catalogue remain
  future hardening / production-certification work, not a condition retroactively
  added to this conservative Phase 3B acceptance
- Production certification is not part of this acceptance and is not issued
- Deterministic CI remains free of real-model dependencies
- Owner-control / actuator authority semantics are unchanged

### Acceptance conditions and disposition

1. Owner-approved artifacts remain pinned and checksum-verified — **satisfied**.
2. Model registry activation review completes under policy — **satisfied** by
   EXP-3B-012; State C registry-bound real-runtime verification **passed** under
   EXP-3B-013 and the runtime was stopped afterward.
3. Gate E provider tests and real-model evaluations are recorded honestly —
   **satisfied**, with limitations retained rather than promoted.
4. Security and required runtime-resilience gates pass; optional behavioural
   capabilities are either explicitly verified or conservatively disabled —
   **satisfied** for the accepted baseline. Bounded text/chat is the only
   positively verified registry behaviour at context 4096; tools, structured
   JSON, streaming and multimodal remain false.
5. Deterministic CI remains free of real-model dependencies — **satisfied**.
6. Owner-control / actuator authority semantics remain unchanged — **satisfied**.

### State C clarification (not automatic startup)

STATE C DOES NOT MEAN AUTOMATIC OR PERMANENT MODEL STARTUP.

State C was a controlled verification that:

- started the already pinned llama.cpp/Qwen baseline;
- explicitly enabled the local provider;
- loaded the canonical registry;
- proved the exact registry entry was bound;
- proved the provider reached the real pinned model through that binding;
- confirmed safe registry observability;
- performed no tool execution;
- kept loopback-only operation;
- then shut the runtime down and verified port/process closure.

EXP-3B-013 recorded `STATE_C_VERIFIED`. The runtime is currently **stopped**.

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

- The portable baseline is **locally installed and artifact-verified** under
  explicit owner authorization; the governed real-provider and registry-bound
  runtime paths have been verified; the runtime is currently **stopped**.
- Phase 3B is complete under the conservative capability matrix recorded in this
  ADR and `config/model_registry.json`.
- Further capability expansion, production certification, automatic startup,
  alternate runtimes/models, adapters/fine-tuning, and Phase 4 execution require
  separate governed decisions; none is granted by this ADR acceptance.
- CI remains deterministic; real models stay out of hosted gates unless a later
  ADR explicitly changes that policy.
- Capability claims remain conservative and distinguish artifact verification,
  behavioural verification, and production certification.

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

- [PHASE_3B_ACCEPTANCE.md](../PHASE_3B_ACCEPTANCE.md)
- [PHASE_3B_HARDWARE_INVENTORY.md](../PHASE_3B_HARDWARE_INVENTORY.md)
- [PHASE_3B_MODEL_RUNTIME_RESEARCH.md](../PHASE_3B_MODEL_RUNTIME_RESEARCH.md)
- [PHASE_3B_INSTALLATION_RUNBOOK.md](../PHASE_3B_INSTALLATION_RUNBOOK.md)
- [adr/0002-local-open-weight-transport.md](0002-local-open-weight-transport.md)
