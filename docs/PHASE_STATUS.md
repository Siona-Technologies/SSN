# Phase Status

| Field | Value |
|-------|--------|
| Phase 1 | **Completed and hardened** (`183fa70` on `feat/siona-cognitive-runtime-v1`) |
| Phase 2 | **In progress / complete on** `feat/siona-runtime-integration-v2` |
| Acceptance gate | Offline CI green; legacy default; shadow no duplicate model; owner-control frozen |
| Current machine | Intel i7-1165G7, Iris Xe, no CUDA GPU |

## Completed capabilities

- Typed event fabric + workspace + model/neuromorphic abstractions (Phase 1)
- Priority backpressure, tenant workspace isolation, timeouts (Phase 1 hardening)
- Runtime modes: `legacy` (default), `shadow`, `cognitive_experimental`
- Shared canonical runtime wiring via `SSNRuntimeBuilder`
- Observation bridges for chat, routing, model results, perception, tools, memory, world
- Trace context continuity
- Strict structured-JSON gateway validation
- Development governance documents

## Simulated capabilities

- Dummy / deterministic language providers
- Deterministic neuromorphic salience (CPU)
- Mock embodiment
- Shadow neuromorphic reflex proposals (non-executing)

## Hardware-gated

- CUDA SNN training, large local LLM, Isaac Sim, event cameras, real IoT/robots — see `DEFERRED_CAPABILITIES.md`

## Deferred

See `DEFERRED_CAPABILITIES.md` and `TECHNICAL_DEBT_REGISTER.md`.

## Next phase

Phase 3 recommendation only — do not start automatically (evaluation harness expansion, optional local model adapter, PerceptionHub full wiring).

## Last verified tests

Record after CI run on this branch (see completion report).
