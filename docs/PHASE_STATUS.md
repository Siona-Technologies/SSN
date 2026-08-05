# Phase Status

| Field | Value |
|-------|--------|
| Phase 1 | **Completed and hardened** (`183fa70` on `feat/siona-cognitive-runtime-v1`) |
| Phase 2 | **Completed and hardened** on `feat/siona-runtime-integration-v2` |
| Acceptance date | 2026-08-05 |
| Final commit | *(recorded at commit time)* |
| Test totals | Offline CI: **183 passed, 4 skipped** |
| Acceptance gate | Exact legacy chat shape; one routing event; trace continuity; safe async observation; owner-control frozen |
| Current machine | Intel i7-1165G7, Iris Xe, no CUDA GPU |

## Completed capabilities

- Typed event fabric + workspace + model/neuromorphic abstractions (Phase 1)
- Priority backpressure, tenant workspace isolation, timeouts (Phase 1 hardening)
- Runtime modes: `legacy` (default), `shadow`, `cognitive_experimental`
- Shared canonical runtime wiring via `SSNRuntimeBuilder`
- Observation bridges for chat, routing, model results, perception, tools, memory, world
- Exact legacy Front Door response key compatibility (no Phase-2 metadata on ordinary chat)
- Single canonical `routing.selected` with Front Door TraceContext
- Trace propagation through tools and perception (`TraceContext.extract_or_create`)
- Bounded pending-task registry for async observation (`drain` / `shutdown`)
- Strict structured-JSON gateway validation
- Product-scope documentation: SIONA Core as independent platform
- Development governance documents

## Known limitations

- Shadow / experimental observation is CPU-local and non-authoritative
- Neuromorphic path remains deterministic / simulated (no CUDA)
- Owner-adjacent suites (`phase43`, `phase66`, `phase67`) retain pre-existing baseline failures (not Phase-2 regressions)
- Product integrations with other Siona Technologies products remain out of scope

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

Phase 3 remains **not started**.
