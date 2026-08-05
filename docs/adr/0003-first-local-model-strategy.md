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

## Alternatives

| Alternative | Notes |
|-------------|-------|
| Remain deterministic/mock-only indefinitely | Safest for CI; delays optional local capability |
| Cloud-only LLM dependency | Conflicts with local/offline goals and increases external control surface |
| Hard-wire one runtime into core | Creates permanent lock-in; rejected |
| Claim a SIONA-native foundation model now | False; SIONA does not own trained foundation weights |
| Skip provenance/licence gates | Unacceptable for ownership and commercial-use clarity |

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
