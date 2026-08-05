# Phase 3B — Model Independence Strategy

**Status:** planning documentation  
**Scope:** ownership and architectural boundaries for optional external open-weight models  
**Non-claim:** SIONA does **not** currently own a trained foundation model

## Position

SIONA Core is an independent hybrid intelligence platform.

An external open-weight model may initially supply pretrained language and
reasoning capabilities, but it is **not** the identity or complete intelligence
architecture of SIONA.

Using an external pretrained model does **not** make SIONA merely an API wrapper.

## What SIONA Core owns and governs

SIONA Core owns and governs:

- Identity
- Owner authority
- Memory
- World model
- Context assembly
- Policy
- Permissions
- Tool governance
- Safety validation
- Provider abstraction
- Evaluation framework
- Provenance records
- Future neuromorphic layers
- Future embodiment interfaces

These layers remain authoritative regardless of which optional language model is
configured behind `ModelGateway`.

## What an external base model is

The external base model remains:

- **Replaceable**
- **Optional**
- Behind `ModelGateway`
- Unable to directly authorize tools
- Unable to directly command actuators
- Subject to SIONA sanitization, verification and fallback rules

Tool calls from a model remain advisory proposals. Existing SIONA policy and
permission layers decide what may execute.

## Terminology

| Component | Meaning |
|-----------|---------|
| Model | Learned numerical weights, such as a Qwen, Gemma or Phi checkpoint |
| Runtime | Software that loads and executes model weights |
| Provider | SIONA adapter connecting ModelGateway to a runtime |
| SIONA Core | The complete intelligence, memory, policy, safety and orchestration platform |
| SIBONA | Future user-facing embodiment powered by SIONA Core |

## Planned progression

1. **Existing open-weight model** used as a replaceable reasoning engine  
2. **SIONA-approved adapters or fine-tuning** on top of an approved base  
3. **SIONA-specialized models** derived under controlled provenance  
4. **Future SIONA-native models** trained with SIONA-controlled data, tokenizer,
   training pipeline, checkpoints and evaluations

## Ownership and licensing boundaries

- SIONA does **not** currently own a trained foundation model.
- Ownership of future adapter/checkpoint outputs depends on the base-model
  licence and dataset rights.
- A genuinely SIONA-native model requires:
  - training from random initialization (or an equivalently SIONA-controlled origin),
  - SIONA-controlled data,
  - and a SIONA-controlled training pipeline.
- Licence and provenance must be recorded before any model download or registry
  promotion beyond mock fixtures.
- Commercial-use conditions must be verified from current official sources before
  any production claim.

## Security and authority boundaries

- Secrets and authentication credentials must be removed before provider transport.
- Redirects and non-loopback endpoints remain rejected by default.
- Unverified capabilities remain conservative.
- Owner identity, master-key handling, law, policy and OWNER/GUEST semantics are
  not altered by model selection.
- Physical actuators remain outside model authority.

## Exit strategy

Because the model sits behind `ModelProvider` / `ModelGateway`:

- The runtime may be uninstalled without rewriting SIONA Core.
- The model checkpoint may be replaced without changing owner-control semantics.
- Deterministic/mock providers remain the CI and offline fallback path.

## Related documents

- [PHASE_3B_HARDWARE_INVENTORY.md](PHASE_3B_HARDWARE_INVENTORY.md)
- [PHASE_3B_MODEL_RUNTIME_RESEARCH.md](PHASE_3B_MODEL_RUNTIME_RESEARCH.md)
- [PHASE_3B_INSTALLATION_RUNBOOK.md](PHASE_3B_INSTALLATION_RUNBOOK.md)
- [adr/0003-first-local-model-strategy.md](adr/0003-first-local-model-strategy.md)
- [adr/0002-local-open-weight-transport.md](adr/0002-local-open-weight-transport.md)
- [SIONA_MODEL_GATEWAY.md](SIONA_MODEL_GATEWAY.md)
