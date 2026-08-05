# SIONA Model Gateway

## Purpose

Vendor-neutral deliberative model access for chat, structured JSON, tool-call
proposals, streaming, health, usage, and fallback — without hard-coding OpenAI,
Anthropic, Ollama, vLLM, or llama.cpp.

## Contracts

- `ModelMessage` — system / user / assistant / tool roles
- `ModelRequest` — messages, SIONA role, tools, multimodal refs, timeout, cancel
- `ModelResponse` — text, tool proposals, structured JSON, usage, fallback flags
- `ToolCallProposal` — never executes tools directly
- `ModelUsage` / `ModelCapabilities`
- `ModelProvider` / streaming protocols

## Gateway behaviour

`ModelGateway.complete()` tries providers in order with:

- enforced `timeout_s` for sync providers via a **bounded shared thread pool**
  (max 4 workers; no unbounded thread growth)
- cancellation checks before execution and between fallback attempts
- usability checks: unhealthy / `finish_reason=error` / empty content /
  missing structured JSON / provider stub (`fallback_reason`) all trigger fallback
- usage / timeout / fallback metrics

**Timeout limitation:** after a timeout, the abandoned synchronous call may
continue until its underlying transport terminates. The gateway stops waiting
and tries the next provider; it does not forcibly kill the worker thread.

`stream()` checks cancellation between chunks where possible.

Legacy HTTP stub responses are marked unhealthy by `LegacyLLMProviderAdapter`
when used inside the gateway, so they do not masquerade as real inference.
Standalone `HttpLLMProvider` / `LocalDummyLLMProvider` behaviour is unchanged
for direct callers.

## Deterministic test provider

`DeterministicModelProvider` is **not** real intelligence. It produces stable
hash-based replies for offline CI.

## Optional local open-weight provider (Phase 3A)

`LocalOpenWeightProvider` implements the same `ModelProvider` protocol. It is
**disabled by default** and never downloads weights or launches a runtime.

```bash
SSN_MODEL_PROVIDER=local
SSN_LOCAL_MODEL_ENDPOINT=http://127.0.0.1:<port>/generate
SSN_LOCAL_MODEL_ID=<configured-model-id>
# Optional:
SSN_LOCAL_MODEL_ALLOW_REMOTE=1   # required for non-loopback endpoints
SSN_LOCAL_MODEL_TIMEOUT_S=20
SSN_LOCAL_MODEL_MAX_RESPONSE_BYTES=1048576
```

Security defaults:

- Loopback-only endpoints unless `SSN_LOCAL_MODEL_ALLOW_REMOTE=1`
- Context scrubbed via existing redaction before send
- Tool calls remain proposals (never executed by the provider)
- Unhealthy/local failures fall through to deterministic providers when wired
  through `ModelGateway`

Transport mapping is isolated in `LocalHttpTransport` so future Ollama /
llama.cpp adapters can be added without rewriting `ModelGateway`.

Model registry / provenance: see `ssn.cognition.model_gateway.registry`.
CI uses clearly labelled **mock** registry fixtures only. No real open-weight
entry is registered until Phase 3B verification.

## Legacy compatibility

| Legacy | Adapter |
|--------|---------|
| `LLMProvider.generate(LLMRequest)` | `LegacyLLMProviderAdapter` → `ModelProvider` |
| `LanguageEngine.process(...)` | unchanged; inject `ModelGatewayAsLLMProvider` |
| `LocalDummyLLMProvider` / `HttpLLMProvider` | preserved; default env still `dummy` |

Env additions (optional):

```bash
SSN_LLM_PROVIDER=deterministic   # or gateway
SSN_MODEL_PROVIDER=local         # Phase 3A optional local path
```

Default remains `dummy` so existing tests are unchanged.

## Runtime data isolation

Tests and smoke scripts set `SSN_RUNTIME_DATA_DIR` to a temporary directory so
tracked `ssn/data/*` files are never mutated by CI. See `ssn.runtime.paths`.

## Safety

Model outputs become structured proposals. Existing policy and tool layers
validate before side effects. Models must not drive actuators directly.
