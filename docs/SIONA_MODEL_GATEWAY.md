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

`ModelGateway.complete()` tries providers in order, records usage/metrics, and
returns a structured failure response if all fail. `stream()` uses the first
provider that supports streaming, else chunks a complete response.

## Deterministic test provider

`DeterministicModelProvider` is **not** real intelligence. It produces stable
hash-based replies for offline CI.

## Legacy compatibility

| Legacy | Adapter |
|--------|---------|
| `LLMProvider.generate(LLMRequest)` | `LegacyLLMProviderAdapter` → `ModelProvider` |
| `LanguageEngine.process(...)` | unchanged; inject `ModelGatewayAsLLMProvider` |
| `LocalDummyLLMProvider` / `HttpLLMProvider` | preserved; default env still `dummy` |

Env additions (optional):

```bash
SSN_LLM_PROVIDER=deterministic   # or gateway
```

Default remains `dummy` so existing tests are unchanged.

## Safety

Model outputs become structured proposals. Existing policy and tool layers
validate before side effects. Models must not drive actuators directly.
