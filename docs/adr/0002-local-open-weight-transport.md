# ADR 0002 — Local open-weight transport boundary

## Status

Accepted (Phase 3A); extended by the final security gate

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
4. HTTP redirects are rejected by default (no loopback→remote open redirect).
5. Full `ModelRequest` sanitization is mandatory before any network send.
6. Keep Front Door / `LanguageEngine` on the legacy dummy path by default;
   local activation is explicit opt-in with both endpoint and model ID.
7. CI validates with deterministic providers and a loopback mock HTTP server only.
8. Governed tests use per-test runtime-data isolation; cleanup is ownership-safe.

## Consequences

- No permanent runtime lock-in in Phase 3A.
- Real model selection and licence/checksum verification deferred to Phase 3B.
- Shadow mode remains observation-only (no duplicate inference).
- Provider is not claimed production-secure.
