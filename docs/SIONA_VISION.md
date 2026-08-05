# SIONA Vision

> **Governing charter:** see [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md).
> This page is a short orientation summary; the charter is authoritative.

SIONA is the core intelligence platform of SIONA Technologies.

It is not merely a chatbot. It is intended to become a persistent, multimodal,
hybrid neuromorphic intelligence that can operate as a private
future user-facing assistant embodiment and later inhabit IoT environments,
vehicles, robots, drones, and humanoid embodiments.

The current working name for the future assistant embodiment is SIBONA. SIBONA
is not part of the Phase 2 runtime and does not yet introduce a separate product
dependency.

## Product relationship

SIONA Core is being developed as an independent intelligence platform under
Siona Technologies. Integration with other Siona Technologies products is a
future business and architectural decision and is outside the present scope.

| Product | Role |
|---------|------|
| **SIONA Core (SSN)** | Shared cognitive runtime, memory, world model, policy, tools, embodiment contracts |
| Future apps | Consume Core contracts when an integration is explicitly approved; do not fork intelligence architecture |

## Deployment models

### Future user-facing assistant embodiment

Local-first runtime on a trusted computer or home hub:

- CLI and HTTP front door
- Owner-controlled identity and policy (unchanged)
- Offline-capable dummy / local model providers
- Persistent memory and bounded world model

### IoT

Embodiment adapters expose devices as capabilities and sensor observations.
Phase 1 provides **mock adapters only** — no real doors, appliances, or actuators.

### Robotics / humanoid

Future adapters (ROS 2, etc.) attach bodies without relocating the mind.
Principle: **SIONA owns the persistent mind; each body is an adapter.**

## What Phase 1 delivers

An asynchronous hybrid cognitive-runtime **foundation**:

- Typed cognitive events + in-process event bus
- Bounded global cognitive workspace + attention arbitration
- Model gateway contracts (chat, tools, JSON, streaming, fallback)
- Neuromorphic provider abstraction (deterministic reference + legacy SNN adapter)
- Cognitive loop skeleton (proposals, not autonomous execution)
- Memory / world service boundaries
- Embodiment / IoT contracts + mock adapter
- Observability counters and deterministic tests

## What Phase 1 is not

- Not consciousness, AGI, or human-equivalent intelligence
- Not a full trained neuromorphic brain
- Not unrestricted autonomy
- Not a rewrite of owner-control, policy, or law files
- Not a microservices / Kafka deployment

## Honesty about simulation

Default language replies use `LocalDummyLLMProvider` (template replies).
Default neuromorphic signals use a **deterministic simulated** reference provider.
The legacy `SNNEngine` remains a random simulation wrapped by an adapter.
Mock embodiment never touches hardware.
