# SIONA Phase Roadmap

## Phase 1 (this work) — Cognitive runtime foundation

Completed scope:

- Event fabric + workspace + attention
- Model gateway contracts + legacy adapters
- Neuromorphic provider abstraction + deterministic reference
- Cognitive loop skeleton
- Memory / world boundaries
- Embodiment contracts + mock adapter
- Docs + deterministic tests
- Owner-control freeze respected

## Phase 2 (recommended next) — Wire and harden

Do **not** start automatically; requires a new instruction.

1. Optionally route a subset of Front Door / sense-tick traffic through the
   event bus while keeping Orchestrator authoritative for identity/policy.
2. Share a single `LanguageEngine` / model gateway instance across
   BrainRouter and FusionEngine.
3. Offer `NeuromorphicSNNFacade` as an opt-in replacement for random
   `SNNEngine` in offline mode (`SSN_OFFLINE=1`).
4. Wire real `PerceptionHub(bus, EncoderRegistry)` in `runtime_builder`
   instead of the dummy fallback where possible.
5. Add FAST/DEEP HTTP endpoint selection (`SSN_LLM_ENDPOINT_FAST` / `_DEEP`).
6. Expand evaluation fixtures for event→workspace→proposal traces.
7. Design (docs + interfaces only) the capability / physical-safety kernel
   without changing owner semantics.
8. First real local model adapter (e.g. llama.cpp / Ollama HTTP) behind
   `ModelProvider`, still offline-testable with deterministic fallback.

## Later phases (sketch)

- Vector / Postgres memory backends behind existing contracts
- Transactional world-model store
- First MQTT or ROS 2 adapter (still gated, confirmation required)
- Learned neuromorphic backends (snnTorch / Norse) as providers
- Product API stability for Pulse / Weza AI
