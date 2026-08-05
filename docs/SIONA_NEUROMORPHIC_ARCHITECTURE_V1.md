# SIONA Neuromorphic Architecture V1

## Core platform

SIONA (SSN) is a modular monolith cognitive runtime. SIONA Core is being
developed as an independent intelligence platform under Siona Technologies.
Integration with other Siona Technologies products is a future business and
architectural decision and is outside the present scope. The primary local-first
mode is a future user-facing assistant embodiment; IoT and robotics attach via
embodiment adapters.

The current working name for the future assistant embodiment is SIBONA. SIBONA
is not part of the Phase 2 runtime and does not yet introduce a separate product
dependency.

## Hybrid LLM / SNN design

The entire brain should **not** initially be one SNN.

| Layer | Role |
|-------|------|
| Neuromorphic runtime | Salience, novelty, anomaly, temporal activity, attention triggers, reflex **proposals**, sensor filtering |
| Model gateway | Deliberative language reasoning, planning sketches, structured JSON, tool-call **proposals** |
| Skills / embodiment | Future VLA and body adapters — proposals validated before any action |
| Memory / world / self | Persistent context with provenance and bounds |
| Policy / tools / owner control | Existing authoritative control boundary (unchanged in this phase) |

Why not one SNN first:

1. Language reasoning quality still depends on foundation models.
2. Safety and owner authority require deterministic policy gates.
3. Neuromorphic backends (snnTorch, Norse, Lava, Loihi, FPGA) will arrive as
   swappable providers — higher layers must not hard-code one backend.
4. Deterministic testing requires seeded/reference providers, not opaque trained
   weights, for Phase 1 CI.

Evolution path: replace `DeterministicNeuromorphicProvider` and model adapters
without changing workspace, event fabric, or product APIs. Later,
neuromorphic-native models can absorb more of salience and short-horizon control
while deliberative models remain available for deep reasoning.

## Global cognitive workspace

Engineering coordination surface — **not** an LLM and **not** a consciousness
claim. It holds bounded active events, goals, task state, attention candidates,
salience, memory/world refs, and tool observations. It ranks attention and
emits snapshots for the cognitive loop.

## Event fabric

`CognitiveEvent` + `AsyncEventBus` (asyncio, in-process). Publish/subscribe,
priority queues, backpressure, handler timeouts, dead letters, metrics.
Transport adapters can be added later; Kafka is not required now.

## Model gateway

`ModelRequest` / `ModelResponse` / `ModelMessage` / `ToolCallProposal` /
`ModelUsage` / `ModelCapabilities` with provider fallback, streaming hooks,
JSON mode, and usage accounting. Legacy `LLMProvider` and
`LanguageEngine.process(...)` remain via adapters.

## Memory and world model

Existing JSON/JSONL backends preserved. New typed records and service
boundaries add provenance, confidence, retention, and proposal objects.
World updates can originate from cognitive events through adapters.

## Embodiment adapters

Body-independent `DeviceDescriptor`, `ActionProposal`, `EmbodimentAdapter`.
Phase 1 ships `MockEmbodimentAdapter` only. Future: MQTT, Matter, ROS 2,
Zenoh, OPC UA, HTTP/WebSocket — dependencies not added yet.

Mind vs body: transferable cognitive state stays in SIONA; joint geometry,
motor limits, calibration, serials, and emergency systems stay body-local.

## Local-first and future distributed deployment

Default path runs offline with deterministic providers. HTTP LLM and embed
endpoints are optional. Future distributed deployment can wrap the same event
contract; Phase 1 intentionally stays a modular monolith.

## Logical architecture

```text
┌───────────────────────────────────────────────────────────────┐
│                    SIONA IDENTITY CORE                        │
│ Existing identity · Existing owner control · Relationships    │
└──────────────────────────────┬────────────────────────────────┘
                               │
┌──────────────────────────────▼────────────────────────────────┐
│                 GLOBAL COGNITIVE WORKSPACE                    │
│ Events · Attention · Goals · Context · Confidence              │
└────────┬─────────────────────┬───────────────────────┬─────────┘
         │                     │                       │
┌────────▼────────┐   ┌────────▼─────────┐   ┌────────▼─────────┐
│ Neuromorphic    │   │ Deliberative     │   │ Skills/Actions   │
│ Runtime         │   │ Model Gateway    │   │ Future VLA layer │
│ Salience/reflex │   │ Reasoning/plans  │   │ Body adapters    │
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
ssn/cognition/memory/   service boundaries
ssn/cognition/world/    service boundaries + event adapters
ssn/embodiment/         contracts + mock adapter + mind/body scaffold
```

## Current limitations

- Cognitive loop is a skeleton; Front Door still uses Orchestrator/BrainRouter.
- Neuromorphic and dummy LLM paths are simulated.
- No real IoT/robot execution.
- No capability/physical-safety kernel yet (documented as future work).
- Owner-control behaviour intentionally frozen.

## Future safety (documentation only)

Before real-world embodiment, SIONA will need a dedicated capability and
physical-safety kernel. Phase 1 does **not** alter owner authority, owner
policy outcomes, override logic, authentication, or law files. Physical
scaffolding uses simulation-only adapters and non-executing action proposals.
