# ADR 0002 — Local open-weight transport boundary

## Status

Accepted (Phase 3A)

## Context

Phase 3 requires an optional local open-weight model path without selecting a
permanent runtime (Ollama, llama.cpp, etc.) or downloading weights in CI.

## Decision

1. Implement `LocalOpenWeightProvider` as a `ModelProvider` behind the existing
   `ModelGateway` — do not create a third provider abstraction.
2. Isolate HTTP request/response mapping in `LocalHttpTransport` so future
   runtime-specific adapters can replace mapping without rewriting the gateway.
3. Default security: loopback endpoints only; remote requires explicit
   `SSN_LOCAL_MODEL_ALLOW_REMOTE=1`.
4. Keep Front Door / `LanguageEngine` on the legacy dummy path by default;
   local activation is explicit opt-in.
5. CI validates with deterministic providers and a loopback mock HTTP server only.

## Consequences

- No permanent runtime lock-in in Phase 3A.
- Real model selection and licence/checksum verification deferred to Phase 3B.
- Shadow mode remains observation-only (no duplicate inference).
