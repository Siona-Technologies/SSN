# ADR 0001 — Hybrid runtime integration

## Status

Accepted (Phase 2)

## Context

SIONA needs an event-driven cognitive foundation while preserving a working
Orchestrator, BrainRouter, Front Door, tools, memory, and owner-controlled
policy path. The development laptop has no CUDA GPU. SIONA Core is being
developed as an independent intelligence platform under Siona Technologies;
integration with other Siona Technologies products is a future business and
architectural decision and is outside the present scope.

## Decision

1. Keep a **hybrid** architecture: neuromorphic path for salience/anomaly;
   model gateway for deliberative language; existing policy/tools as authority.
2. Keep **legacy** mode as the production default so existing responses remain
   unchanged.
3. Integrate cognitive observation in **shadow** mode before any replacement of
   the authoritative path — observe without duplicate model calls or side effects.
4. Keep SNN and foundation-model roles separate; do not pretend one SNN is the
   whole brain.
5. **Freeze owner-control** behaviour during Phase 1–2 (no law/identity/permission changes).
6. Keep compute providers replaceable behind interfaces (dummy, deterministic,
   future local/remote).
7. Continue software development on the current CPU-only laptop; gate GPU work
   explicitly rather than blocking architecture.

## Consequences

- Slight complexity from dual modes and bridges.
- Clear honesty about simulated vs real components.
- Hardware-gated work tracked in deferred capabilities / hardware roadmap.
- Phase 3 can deepen evaluation and optional local models without rewriting Core.
