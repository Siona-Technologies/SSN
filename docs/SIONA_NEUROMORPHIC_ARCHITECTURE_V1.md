# SIONA Neuromorphic Architecture V1

## Status

**Current governed state:** Phase 3 and Phase 4 are complete. The local
language-model path is real and optional; the neuromorphic layer now has both a
deterministic/reference provider and an accepted explicit learned software SNN
provider for a bounded temporal-salience task.

Governing charter: [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md).  
Phase 4 acceptance: [PHASE_4_ACCEPTANCE.md](PHASE_4_ACCEPTANCE.md).

## Core platform

SIONA Core is a modular-monolith cognitive runtime and independent intelligence
platform under SIONA Technologies. Other products remain separate unless a
future integration decision explicitly approves a connection.

The working name for a future user-facing assistant embodiment is SIBONA.
SIBONA is not the name of the current runtime and is not a separate intelligence
core.

## Hybrid foundation-model / SNN design

The entire intelligence architecture should **not** be one SNN.

| Layer | Role | Current status |
|---|---|---|
| Neuromorphic runtime | Salience, temporal classification, novelty/anomaly/reflex proposal surfaces, sensor filtering | Deterministic/reference provider plus accepted explicit learned software SNN provider for `temporal_salience_v1` |
| Model gateway | Deliberative language reasoning and bounded model responses/proposals | Real optional local Qwen baseline accepted in Phase 3B; conservative capabilities only |
| Skills / embodiment | Future VLA and body adapters; proposals validated before action | Designed/mock boundaries; no real physical authority |
| Memory / world / self | Persistent context with provenance and bounds | Existing contracts/stores; future backend expansion separately governed |
| Policy / tools / owner control | Authoritative permissions, policy and capability boundary | Remains authoritative and unchanged by learned-model selection |

Why not one SNN:

1. Language reasoning currently depends on replaceable foundation models.
2. Safety and owner authority require deterministic policy/capability gates.
3. Neuromorphic backends remain swappable providers rather than being hard-coded
   into higher layers.
4. Deterministic/reference providers remain necessary for CI, fallback and
   controlled comparisons.
5. Learned SNN evidence is task-specific and must not be generalized into
   unsupported claims about the whole cognitive system.

## Accepted Phase 3 model boundary

Phase 3B accepted the first optional local language-model baseline:

- llama.cpp b9968;
- `Qwen3-1.7B-Q4_K_M`;
- exact canonical registry binding;
- bounded text/chat at context 4096;
- tools=false;
- structured_json=false;
- streaming=false;
- multimodal=false;
- siona_native=false;
- steady-state runtime stopped.

This model is external and replaceable. It does not become the neuromorphic
provider, memory authority, policy authority or owner-control authority.

## Accepted Phase 4 learned-neuromorphic boundary

Phase 4 accepted the first **real learned software SNN provider**:

- provider: `siona-neuro-learned-lif-v1`;
- task: `phase4a-temporal-salience-v1`;
- architecture: `phase4b-lif-final-membrane-v1`;
- learned input: explicit 20 × 8 binary temporal sequence;
- one governed CPU training run under EXP-4-003;
- exact canonical JSON artifact and SHA-256;
- pure-Python inference in normal runtime;
- deterministic fallback for unsupported modalities;
- strict fail-closed handling for malformed learned inputs;
- no runtime torch/snnTorch/numpy/Norse dependency;
- no tool or physical-actuator authority;
- explicit opt-in only; deterministic provider remains default.

Evidence:

- EXP-4-003 — `FIRST_CPU_SNN_TRAINING_VERIFIED`;
- EXP-4-004 — `LEARNED_SNN_PROVIDER_PARITY_VERIFIED`;
- EXP-4-005 — `PHASE4_LEARNED_SNN_BREADTH_SAFETY_VERIFIED`;
- ADR 0004 — **Accepted (Phase 4)**.

This is a software SNN milestone. It is **not** a claim of Loihi/FPGA execution,
measured neuromorphic energy efficiency, GPU training, or persistent event-by-
event asynchronous/stateful SNN streaming.

## Global cognitive workspace

The workspace is an engineering coordination surface — not a foundation model
and not a consciousness claim. It holds bounded active events, goals, task state,
attention candidates, salience, memory/world references and tool observations.
It ranks attention and emits snapshots for the cognitive loop.

## Event fabric

`CognitiveEvent` + `AsyncEventBus` provide in-process asynchronous event
publication/subscription, priority queues, backpressure, handler timeouts, dead
letters and metrics.

This software-level asynchronous event fabric is distinct from true event-driven
neuromorphic hardware execution. The accepted Phase 4 learned SNN still consumes
a complete bounded 20 × 8 temporal sequence per learned inference.

## Model gateway

`ModelRequest` / `ModelResponse` / `ModelMessage` / `ToolCallProposal` /
`ModelUsage` / `ModelCapabilities` preserve the language-model provider boundary.
The accepted local open-weight path remains optional and governed by Phase 3
registry/capability evidence.

## Memory and world model

Existing JSON/JSONL and typed service boundaries remain preserved. Production
vector/Postgres migration and semantic-memory expansion remain separate future
data architecture decisions.

## Embodiment adapters

Body-independent `DeviceDescriptor`, `ActionProposal` and `EmbodimentAdapter`
contracts preserve the mind/body split. Real MQTT/ROS2/IoT/robotics remain
separately gated. A learned SNN output is a signal/proposal, never a direct
actuator command.

## Local-first and future distributed deployment

Default operation remains local-first. Deterministic providers remain the hosted
CI path and default neuromorphic fallback. Optional learned or foundation-model
providers fail safely when artifacts/runtimes are unavailable. Future distributed
deployment must wrap the same contracts rather than bypass them.

## Logical architecture

```text
┌───────────────────────────────────────────────────────────────┐
│                    SIONA IDENTITY CORE                        │
│ Existing identity · owner control · relationships             │
└──────────────────────────────┬────────────────────────────────┘
                               │
┌──────────────────────────────▼────────────────────────────────┐
│                 GLOBAL COGNITIVE WORKSPACE                    │
│ Events · attention · goals · context · confidence             │
└────────┬─────────────────────┬───────────────────────┬─────────┘
         │                     │                       │
┌────────▼────────┐   ┌────────▼─────────┐   ┌────────▼─────────┐
│ Neuromorphic    │   │ Deliberative     │   │ Skills/Actions   │
│ Provider        │   │ Model Gateway    │   │ Future VLA/body  │
│ Ref + learned   │   │ Qwen optional    │   │ proposals only   │
└────────┬────────┘   └────────┬─────────┘   └────────┬─────────┘
         └─────────────────────┼───────────────────────┘
                               │
┌──────────────────────────────▼────────────────────────────────┐
│ MEMORY · WORLD MODEL · SELF MODEL                             │
└──────────────────────────────┬────────────────────────────────┘
                               │
┌──────────────────────────────▼────────────────────────────────┐
│ EXISTING POLICY · TOOLS · CONTROL BOUNDARIES                  │
└──────────────────────────────┬────────────────────────────────┘
                               │
┌──────────────────────────────▼────────────────────────────────┐
│                  EMBODIMENT FABRIC                            │
└───────────────────────────────────────────────────────────────┘
```

## Package layout

```text
ssn/cognition/          events, bus, workspace, attention, loop, metrics
ssn/cognition/model_gateway/
ssn/cognition/neuromorphic/
ssn/cognition/memory/
ssn/cognition/world/
ssn/embodiment/
```

## Current limitations after Phase 4 acceptance

- The accepted learned SNN is bounded to one synthetic temporal-salience task.
- It is a software SNN, not neuromorphic silicon.
- No CUDA/GPU SNN training or benchmark has been executed for SIONA Core.
- No measured SNN energy-efficiency claim exists.
- Persistent event-by-event asynchronous/stateful learned SNN streaming is not
  implemented.
- No real event-camera input is part of the accepted learned task.
- No real IoT/robot/vehicle/drone actuator authority exists.
- No physical-safety kernel is implemented for real-world actuation.
- Qwen native structured JSON remains NOT_VERIFIED and streaming remains
  unsupported on the pinned Phase 3 baseline.
- Owner-control behavior remains governed by existing policy/capability systems.

## Physical safety principle

Before real-world embodiment, SIONA requires a dedicated capability and
physical-safety kernel. Physical scaffolding must begin in simulation and use
non-executing action proposals. Owner permission does not replace deterministic
physical safety.
