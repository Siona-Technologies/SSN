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

## Optional local open-weight provider (Phase 3A/3B)

`LocalOpenWeightProvider` implements the same `ModelProvider` protocol. It is
**disabled by default** and never downloads weights or launches a runtime.

```bash
SSN_MODEL_PROVIDER=local
SSN_LOCAL_MODEL_ENDPOINT=http://127.0.0.1:<port>/generate   # siona_generate default
SSN_LOCAL_MODEL_ID=<configured-model-id>   # required — no default operational ID
# Optional:
SSN_LOCAL_MODEL_API_DIALECT=siona_generate   # or openai_chat (llama.cpp OpenAI-compatible)
SSN_LOCAL_MODEL_VERIFY_MODEL_ID=0            # default: false for siona_generate, true for openai_chat
SSN_LOCAL_MODEL_MAX_TOKENS_CAP=512           # default 512 for openai_chat; positive bounded int
SSN_LOCAL_MODEL_ALLOW_REMOTE=1               # required for non-loopback endpoints
SSN_LOCAL_MODEL_TIMEOUT_S=20
SSN_LOCAL_MODEL_MAX_RESPONSE_BYTES=1048576
```

### API dialects

- `siona_generate` (default): Phase 3A mock contract — `POST …/generate` with
  `{text: …}` responses. Preserves existing deterministic CI behaviour.
- `openai_chat`: llama.cpp / OpenAI-compatible mapping — accepts base
  `http://127.0.0.1:8080` or exact `…/v1/chat/completions`; derives `/health`
  and `/v1/models`; posts OpenAI chat payloads with `stream:false`; extracts
  `choices[0].message.content`. Ambiguous paths fail closed. Default model-ID
  verification uses `/v1/models`. Default max-tokens cap is 512.

Health is fail-closed: success only when `ok` is boolean `true` or `status` is
exactly `"ok"`. LanguageEngine local opt-in sets ModelGateway request timeout to
transport timeout + 1 second so HTTP can terminate first.

Security defaults (final gate):

- Loopback-only endpoints unless `SSN_LOCAL_MODEL_ALLOW_REMOTE=1`
- Embedded credentials, URL fragments, and HTTP redirects are rejected
- Full `ModelRequest` sanitization at the provider boundary (context, system,
  messages, metadata, tool definitions); exact configured secrets replaced
- Tool calls remain proposals (never executed by the provider)
- Unverified capability claims stay conservative (no tools/structured/context
  window invention until an explicit `capabilities` object is recorded with
  `capability_verification_status=verified`)
- Artefact verification (`artifact_verification_status`) is separate from
  behavioural capability verification
- Synchronous urllib does not support mid-request cancellation; cancel tokens
  are checked before network start only
- Response parsing bounds text, tool proposals, confidence, and usage fields
- Evaluation reports are redacted before write

Transport mapping is isolated in `LocalHttpTransport` so future Ollama /
llama.cpp adapters can be added without rewriting `ModelGateway`.

Model registry / provenance: see `ssn.cognition.model_gateway.registry`.
CI uses clearly labelled **mock** registry fixtures only. No real open-weight
entry is registered until Phase 3B verification. Loading is transactional.

### Controlled real-provider validation (EXP-3B-005)

A temporary loopback validation (2026-08-05) exercised:

`LanguageEngine` → `ModelGateway` → `LocalOpenWeightProvider` (`openai_chat`)
→ llama.cpp b9968 on `127.0.0.1:8080` → pinned `Qwen3-1.7B-Q4_K_M.gguf`.

Observed: exact `/v1/models` ID verification; healthy direct text probe;
LanguageEngine end-to-end on the real local provider; tool proposals absent;
runtime stopped afterward; deterministic fallback after shutdown. Structured
JSON remained **unverified** (probe observed failure). Registry remains
**inactive**. This is a **limited text-transport gate only** — not production
certification and not broad capability verification.

## Runtime data isolation

Tests use **per-test** temporary directories via `IsolatedTextTestRunner`.
Smoke scripts may use one process-level `SSN_RUNTIME_DATA_DIR`.
`cleanup_ensured_isolation()` only clears directories it owns.

## Evaluation

`scripts/run_eval.py --provider` runs declarative cases with hard child-process
timeouts. Results are labelled mock/deterministic. No real model is evaluated.

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

## Governed prompt-context bridge (EXP-3B-006)

Optional request-time context assembly (`SSN_GOVERNED_CONTEXT`, default off)
runs in a pre-provider wrapper installed by `LanguageEngine` before any
`LLMProvider` / `ModelGateway` / local transport call. Composite policy
(`decide_model_prompt` plus disclosure decision) filters caller-supplied
records. Only a bounded text block reaches providers. This is **not** model
training, not a LoRA/QLoRA/PEFT adapter, and not registry activation. See
[SIONA_GOVERNED_PROMPT_CONTEXT.md](SIONA_GOVERNED_PROMPT_CONTEXT.md).

Status wording: **IMPLEMENTED AND VALIDATED AGAINST DETERMINISTIC PROVIDERS
ONLY; NO ACTIVE PERSONAL RECORDS; NO MODEL TRAINING; NO REGISTRY ACTIVATION;
REAL LOCAL-MODEL CONTEXT CAMPAIGN NOT STARTED.**

Hardening (fail-closed): malformed runtime objects deny without exceptions;
hard assembler ceilings; JSON-lines serialization; exact legacy response when
unused; ambiguous consent fails closed; bounded diagnostics invariant; sanitized
correlation IDs. Final correction: O(16) candidate inspection, typed-record and
typed-consent structural preflight, delegated-consent-only scope, envelope
`input_error_reason` when candidate count is untrustworthy, `used_context` meta
assertion with provider fallback, case-insensitive script-marker neutralization.
Model-prompt injection is not solved by text filtering alone.

## Safety

Model outputs become structured proposals. Existing policy and tool layers
validate before side effects. Models must not drive actuators directly.
Model output cannot approve identity facts or grant consent.

