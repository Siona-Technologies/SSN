# SIONA Neuromorphic Architecture V1

## Status

**Current governed state:** Phase 3 is complete; Phase 4 learned-neuromorphic
planning is proposed. The local language-model path is real and optional; the
neuromorphic path is still deterministic/reference-only until Phase 4 produces
and validates a learned SNN artifact.

Governing charter: [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md).

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
| Neuromorphic runtime | Salience, novelty, anomaly, temporal activity, attention triggers, reflex **proposals**, sensor filtering | Deterministic/reference provider implemented; learned SNN deferred to Phase 4 |
| Model gateway | Deliberative language reasoning and bounded model responses/proposals | Real optional local Qwen baseline accepted in Phase 3B; conservative capabilities only |
| Skills / embodiment | Future VLA and body adapters; proposals validated before action | Designed/mock boundaries; no real physical authority |
| Memory / world / self | Persistent context with provenance and bounds | Existing contracts/stores; future backend expansion separately governed |
| Policy / tools / owner control | Authoritative permissions, policy and capability boundary | Remains authoritative and unchanged by model selection |

Why not one SNN:

1. Language reasoning currently depends on replaceable foundation models.
2. Safety and owner authority require deterministic policy/capability gates.
3. Neuromorphic backends should remain swappable providers rather than being
   hard-coded into higher layers.
4. Deterministic/reference providers remain necessary for CI, fallback and
   controlled comparisons.
5. Learned SNN evidence must be task-specific and must not be generalized into
   unsupported claims about the whole cognitive system.

## Accepted Phase 3 model boundary

Phase 3B accepted the first optional local language-model baseline:

- llama.cpp b9968
- `Qwen3-1.7B-Q4_K_M`
- exact canonical registry binding
- bounded text/chat at context 4096
- tools=false
- structured_json=false
- streaming=false
- multimodal=false
- siona_native=false
- steady-state runtime stopped

This model is external and replaceable. It does not become the neuromorphic
provider, memory authority, policy authority, or owner-control authority.

## Phase 4 learned-neuromorphic direction

Phase 4 is proposed to produce the first **real learned SNN provider** for a
bounded temporal salience/classification task.

The learned provider must:

- sit behind the existing neuromorphic provider boundary;
- use governed training data/generator provenance;
- record deterministic seeds, splits, backend/version and checkpoint checksum;
- demonstrate held-out learned performance against a predeclared baseline;
- remain advisory only;
- preserve deterministic/reference fallback;
- keep hosted CI model-training-free;
- distinguish CPU evidence from later hardware-gated GPU evidence.

See [PHASE_4_ENGINEERING_SPEC.md](PHASE_4_ENGINEERING_SPEC.md) and proposed
[ADR 0004](adr/0004-learned-neuromorphic-backend-strategy.md).

## Global cognitive workspace

The workspace is an engineering coordination surface — not a foundation model
and not a consciousness claim. It holds bounded active events, goals, task state,
attention candidates, salience, memory/world references and tool observations.
It ranks attention and emits snapshots for the cognitive loop.

## Event fabric

`CognitiveEvent` + `AsyncEventBus` provide in-process asynchronous event
publication/subscription, priority queues, backpressure, handler timeouts, dead
letters and metrics. Distributed transports may be added later; they are not
required for Phase 4.

## Model gateway

`ModelRequest` / `ModelResponse` / `ModelMessage` / `ToolCallProposal` /
`ModelUsage` / `ModelCapabilities` preserve the model-provider boundary. The
accepted local open-weight path remains optional and governed by the Phase 3
registry/capability evidence.

## Memory and world model

Existing JSON/JSONL and typed service boundaries remain preserved. Production
vector/Postgres migration and semantic-memory expansion are separate future data
architecture decisions and are not part of Phase 4 learned-neuromorphic scope.

## Embodiment adapters

Body-independent `DeviceDescriptor`, `ActionProposal` and `EmbodimentAdapter`
contracts preserve the mind/body split. Real MQTT/ROS2/IoT/robotics remain
separately gated. A learned SNN output is a proposal/signal, never a direct
actuator command.

## Local-first and future distributed deployment

Default operation remains local-first. Deterministic providers remain the hosted
CI path. Optional learned or foundation-model providers must fail safely when
artifacts/runtimes are unavailable. Future distributed deployment must wrap the
same contracts rather than bypass them.

## Logical architecture

```text
┌───────────────────────────────────────────────────────────────┐
│                    SIONA IDENTITY CORE                        │
│ Existing identity · owner control · relationships             │
└──────────────────────────────┬────────────────────────────────┘
                               │
┌──────────────────────────────▼────────────────────────────────┐
│                 GLOBAL COGNITIVE WORKSPACE                    │
│ Events · attention · goals · context · confidence              │
└────────┬─────────────────────┬───────────────────────┬─────────┘
         │                     │                       │
┌────────▼────────┐   ┌────────▼─────────┐   ┌────────▼─────────┐
│ Neuromorphic    │   │ Deliberative     │   │ Skills/Actions   │
│ Provider        │   │ Model Gateway    │   │ Future VLA/body  │
│ Ref → learned   │   │ Qwen optional    │   │ proposals only   │
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

## Current limitations carried into Phase 4 planning

- The learned neuromorphic backend does not yet exist.
- No trained SNN checkpoint is currently claimed by SIONA Core.
- No CUDA/GPU SNN training or benchmark has been executed for SIONA Core.
- No real IoT/robot/vehicle/drone actuator authority exists.
- No physical-safety kernel is implemented for real-world actuation.
- Qwen native structured JSON remains NOT_VERIFIED and streaming remains
  unsupported on the pinned Phase 3 baseline; Phase 4 must not change those
  claims incidentally.
- Owner-control behavior remains governed by existing policy/capability systems.

## Physical safety principle

Before real-world embodiment, SIONA requires a dedicated capability and
physical-safety kernel. Physical scaffolding must begin in simulation and use
non-executing action proposals. Owner permission does not replace deterministic
physical safety.
