# SIONA Neuromorphic Architecture V1

## Status

**Current governed state:** Phase 4 is complete and ADR 0004 is Accepted
(Phase 4). SIONA now has both a deterministic/reference neuromorphic provider and
an explicit learned software SNN provider for the bounded temporal-salience task.
The deterministic provider remains the default/fallback. Phase 5 is not started.

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
| Neuromorphic runtime | Salience, novelty, anomaly, temporal activity, attention triggers, reflex **proposals**, sensor filtering | Deterministic/reference provider + accepted explicit learned software SNN provider for bounded temporal salience |
| Model gateway | Deliberative language reasoning and bounded model responses/proposals | Real optional local Qwen baseline accepted in Phase 3B; conservative capabilities only |
| Skills / embodiment | Future VLA and body adapters; proposals validated before action | Designed/mock boundaries; no real physical authority |
| Memory / world / self | Persistent context with provenance and bounds | Existing contracts/stores; future backend expansion separately governed |
| Policy / tools / owner control | Authoritative permissions, policy and capability boundary | Remains authoritative and unchanged by model selection |

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

## Accepted Phase 4 learned-neuromorphic boundary

Phase 4 produced and accepted the first real learned SNN provider:

- provider: `siona-neuro-learned-lif-v1`;
- task: `phase4a-temporal-salience-v1`;
- architecture: `phase4b-lif-final-membrane-v1`;
- artifact SHA-256:
  `dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc`;
- CPU software SNN evidence only;
- standard-library-only runtime implementation;
- deterministic/reference provider preserved as default/fallback;
- no tool authority;
- no physical-actuation authority.

The provider was trained once under EXP-4-003, matched the snnTorch reference
under EXP-4-004, and passed breadth/safety hardening under EXP-4-005.

The accepted learned provider processes complete 20×8 temporal windows. True
long-lived event-by-event learned state is **not** claimed by Phase 4.

See [PHASE_4_ACCEPTANCE.md](PHASE_4_ACCEPTANCE.md) and
[ADR 0004](adr/0004-learned-neuromorphic-backend-strategy.md).

## Global cognitive workspace

The workspace is an engineering coordination surface — not a foundation model
and not a consciousness claim. It holds bounded active events, goals, task state,
attention candidates, salience, memory/world references and tool observations.
It ranks attention and emits snapshots for the cognitive loop.

## Event fabric

`CognitiveEvent` + `AsyncEventBus` provide in-process asynchronous event
publication/subscription, priority queues, backpressure, handler timeouts, dead
letters and metrics.

This software event-bus asynchrony is distinct from true event-driven learned SNN
state updates. The latter remains future work after Phase 4.

## Model gateway

`ModelRequest` / `ModelResponse` / `ModelMessage` / `ToolCallProposal` /
`ModelUsage` / `ModelCapabilities` preserve the model-provider boundary. The
accepted local open-weight path remains optional and governed by Phase 3
registry/capability evidence.

## Memory and world model

Existing JSON/JSONL and typed service boundaries remain preserved. Production
vector/Postgres migration and semantic-memory expansion are separate future data
architecture decisions.

## Embodiment adapters

Body-independent `DeviceDescriptor`, `ActionProposal` and `EmbodimentAdapter`
contracts preserve the mind/body split. Real MQTT/ROS2/IoT/robotics remain
separately gated. A learned SNN output is a proposal/signal, never a direct
actuator command.

## Local-first and future distributed deployment

Default operation remains local-first. Deterministic providers remain the hosted
CI path. The accepted learned provider is explicit opt-in and fails closed when
its artifact/input contract is invalid. Future distributed deployment must wrap
the same contracts rather than bypass them.

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
│ ref + learned   │   │ Qwen optional    │   │ proposals only   │
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

## Current limitations after Phase 4

- The learned SNN is bounded to one synthetic temporal-salience task.
- It is not a general-purpose learned SNN brain.
- It consumes complete temporal windows rather than maintaining verified
  long-lived streaming state.
- No CUDA/GPU SNN benchmark is accepted.
- No Loihi/FPGA/neuromorphic-silicon execution is accepted.
- No measured hardware energy-efficiency claim is accepted.
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
