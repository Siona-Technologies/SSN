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

### Provisional runtime direction (not approved)

- **Primary first baseline:** llama.cpp native Windows x64 CPU build
- **Later experiment only:** llama.cpp SYCL on Intel Iris Xe (no speed claim)
- **Convenience comparison:** Ollama (deferred as first controlled baseline)
- **Intel-optimized alternative research path:** OpenVINO GenAI (deferred)

CPU baseline comes first because it minimizes driver/toolchain variables and
preserves exact binary + model-file control. SYCL remains experimental until
local benchmark. A background service is not preferred for the first controlled
baseline.

### Provisional model direction (not approved / not downloaded)

- **Primary first integration candidate:** Qwen3-1.7B (transport/integration gate)
  - Publisher GGUF currently publishes **Q8_0** (not Q4_K_M)
  - Requested Q4_K_M exists on **ggml-org** with distinct quantizer attribution
- **Second capability candidate:** Qwen3-4B Q4_K_M (official Qwen GGUF)
- **Additional comparison:** IBM Granite 4.0 Micro Q4_K_M (official IBM GGUF)

External models remain optional and replaceable. No SIONA-native foundation
model claim is made.

### Why no final approval is issued

- Owner approval is required before any install or download
- Local latency/RAM/thermal measurements are still outstanding
- Artefact path for 1.7B Q4_K_M vs publisher Q8_0 still needs an owner choice
- ADR status remains **Proposed** until those gates close

### Conditions required before changing ADR status from Proposed

1. Owner approves a specific runtime artefact (version + SHA256 + install path)
2. Owner approves a specific model artefact (repo + filename + SHA256)
3. Loopback-only install completes with checksum verification
4. Provider tests and real-model evaluations are recorded honestly
5. Deterministic CI remains free of real-model dependencies
6. No change to owner-control / actuator authority semantics

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

- Planning and research may proceed without installing software.
- Installation requires the staged approvals in
  [PHASE_3B_INSTALLATION_RUNBOOK.md](../PHASE_3B_INSTALLATION_RUNBOOK.md).
- CI remains deterministic; real models stay out of hosted gates unless a later
  ADR explicitly changes that policy.
- Capability claims remain conservative until artefact and behavioural
  verification are both recorded.

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
