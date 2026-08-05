# Phase Status

| Field | Value |
|-------|--------|
| Phase 1 | **Completed and hardened** (`183fa70` on `feat/siona-cognitive-runtime-v1`) |
| Phase 2 | **Completed and hardened** |
| Accepted Phase 2 implementation gate | `7b92114` |
| Phase 2 pre-closeout status record | `5f0d3ae` |
| Closeout documentation | This branch after Vision Charter review (`docs/SIONA_VISION_CHARTER.md`, `docs/PHASE_2_ACCEPTANCE.md`, `docs/PHASE_3_ENGINEERING_SPEC.md`) |
| Phase 3 | **Specified but not started** |
| Acceptance date | 2026-08-05 |
| Test totals (accepted gate evidence) | Offline CI: **199 passed, 4 skipped** |
| Current machine | Intel i7-1165G7, Iris Xe, no CUDA GPU |

## Governing documents

- [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md) — permanent architectural charter
- [PHASE_2_ACCEPTANCE.md](PHASE_2_ACCEPTANCE.md) — formal Phase 2 acceptance evidence
- [PHASE_3_ENGINEERING_SPEC.md](PHASE_3_ENGINEERING_SPEC.md) — Phase 3 specification only (no implementation)

## Completed capabilities (Phase 1–2)

- Typed event fabric + workspace + model/neuromorphic abstractions (Phase 1)
- Priority backpressure, tenant workspace isolation, timeouts (Phase 1 hardening)
- Runtime modes: `legacy` (default), `shadow`, `cognitive_experimental`
- Shared canonical runtime wiring via `SSNRuntimeBuilder`
- Exact legacy Front Door response key compatibility
- Single canonical `routing.selected` with Front Door TraceContext
- Trace isolation: no per-request state on shared runtime deps
- Async shutdown with safe pending-task lifecycle
- Product-scope independence: SIONA Core as independent platform
- Assistant terminology: future user-facing assistant embodiment (SIBONA working name only)

## Known limitations

- Shadow / experimental observation is CPU-local and non-authoritative
- Neuromorphic path remains deterministic / simulated (no CUDA)
- Owner-adjacent baseline vs `0cf3372`: identical **1 failure + 3 errors** (technical debt; see `PHASE_2_ACCEPTANCE.md`)
- No trained SIONA-native foundation model
- Product integrations with other Siona Technologies products remain out of scope
- SIBONA is a working name only — not part of the Phase 2 runtime

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

Phase 3 is **specified** in `PHASE_3_ENGINEERING_SPEC.md` and remains **not started**.
No Phase 3 branch has been created.
