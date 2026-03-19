## SIONA / SSN LLM Strategy (V10)

This document explains how the language core is wired so that you can:

- start with a **dummy local provider** (no external model, deterministic),
- move to a **local HTTP-based inference server** later,
- and eventually plug in **owner-trained / custom models**

without changing `BrainRouter`, `FusionEngine`, or tools.

---

## 1. Core Abstractions

- `LanguageEngine` (`ssn.core.language_engine`):
  - Used by `BrainRouter` and `FusionEngine`.
  - Stable contract:
    - `process(text: str, context: dict | None, role: str) -> dict` with:
      - `reply`: text answer,
      - `role`: resolved role (`OWNER`/`GUEST`),
      - `used_context`: bool,
      - `engine`: engine/provider name.
  - Optional helper:
    - `generate_reply(prompt=..., role=..., context=...) -> {"text", "meta"}` (used by tests).

- `LLMProvider` (`ssn.core.llm_providers`):
  - Protocol with:
    - `generate(request: LLMRequest) -> LLMResponse`
  - Data classes:
    - `LLMRequest(prompt, role, context)`
    - `LLMResponse(text, meta)`

`LanguageEngine` is just a thin facade that turns its `process(...)` calls into an `LLMRequest` and delegates to whichever `LLMProvider` is selected.

---

## 2. Built-in Providers (Current)

All in `ssn.core.llm_providers`:

- **LocalDummyLLMProvider**
  - Name: `ssn-local-dummy-llm-v1`
  - Behavior: reproduces the original Phase 1 dummy behavior:
    - OWNER: rich, context-aware template reply.
    - GUEST: short echo-style reply.
  - Purpose: keep tests and behavior stable while providing a clean provider abstraction.

- **HttpLLMProvider** (local/remote-ready)
  - Name: `ssn-http-llm-v1`
  - Reads base URL from:
    - constructor arg `base_url`, or
    - `SSN_LLM_ENDPOINT` env var.
  - Request/response JSON schema:
    - Request body:
      ```json
      {
        "prompt": "<string>",
        "role": "<OWNER|GUEST>",
        "context": { "...": "..." }
      }
      ```
    - Response body:
      ```json
      {
        "text": "<model reply text>",
        "meta": {
          "engine": "your-model-name",
          "used_context": true
        }
      }
      ```
  - Error handling:
    - On any configuration/HTTP/JSON error, falls back to a deterministic stub reply and sets `fallback_reason` in `meta`.
  - Purpose: production-capable HTTP adapter for a local/remote inference server with safe fallback behavior.

---

## 3. Environment-Based Provider Selection

Provider selection lives in:

- `get_default_provider_from_env()` in `ssn.core.llm_providers`

Env variables:

- **`SSN_LLM_PROVIDER`**
  - Controls which provider is used by default when `LanguageEngine()` is constructed without an explicit provider.
  - Supported values (case-insensitive):
    - `"dummy"` (default): use `LocalDummyLLMProvider`.
    - `"http"`: use `HttpLLMProvider`.
  - Example:

  ```bash
  export SSN_LLM_PROVIDER=http
  export SSN_LLM_ENDPOINT=http://localhost:8000/generate
  ```

- **`SSN_LLM_ENDPOINT`**
  - Base URL for `HttpLLMProvider` (e.g. `http://localhost:8000/generate`).
  - Safe to leave unset when using the dummy provider.

`LanguageEngine.__init__` logic:

- if a provider instance is passed explicitly: use it;
- otherwise: call `get_default_provider_from_env()` and use the result.

This keeps brain code simple and lets you switch providers purely via environment configuration in production.

---

## 4. Upgrading to a Real Local Model (Future)

When you have hardware and a model ready, you have two main options:

### Option A: HTTP-Based Local Inference Server

1. Run a local model server (e.g., vLLM, text-generation-webui, custom FastAPI) on `localhost` or your LAN.
2. Change `HttpLLMProvider.generate(...)` to:
   - build a JSON payload from `LLMRequest` (prompt, role, context),
   - send an HTTP POST to `self.base_url`,
   - parse JSON response into `LLMResponse(text, meta)`.
3. Set env vars:

   ```bash
   export SSN_LLM_PROVIDER=http
   export SSN_LLM_ENDPOINT=http://localhost:8000/generate
   ```

4. Restart SIONA; no brain code changes required.

### Option B: In-Process Local Model (PyTorch/JAX)

1. Implement a new provider class, e.g. `LocalLLMProvider`, that:
   - loads your model weights (once) in `__init__`,
   - runs inference in `generate(...)`,
   - returns `LLMResponse(text, meta)`.
2. Either:
   - update `get_default_provider_from_env()` to recognize a new value, e.g. `"local"` → `LocalLLMProvider`, or
   - construct `LanguageEngine(provider=LocalLLMProvider(...))` explicitly in your runtime builder.

This option is more tightly coupled to your Python runtime but avoids HTTP overhead. It works best when SIONA and the model live in the same process and machine.

---

## 5. Model Portfolio (Future Roadmap)

The V10 blueprint calls for a small portfolio of models:

1. **Fast small model** – for quick responses and low-cost tasks.
2. **Higher-quality reasoning model** – for deep OWNER queries.
3. **Embedding model** – for retrieval / RAG over memory + knowledge.

This maps cleanly to providers:

- Fast vs deep can be handled either by:
  - separate endpoints in `HttpLLMProvider`, or
  - routing logic inside a future `MultiModelProvider`.
- Embeddings can be a separate provider interface or extra method on an advanced provider (e.g., `embed(texts: list[str]) -> vectors`), wired into semantic memory and tools.

For now, SIONA uses:

- `LocalDummyLLMProvider` for all text generation,
- no embeddings provider (semantic store is key/value + simple scoring).

---

## 6. Safety & Policy (LLM-Specific Notes)

- All LLM usage remains **tool-gated** and role-aware via:
  - Front Door → Policy Engine → BrainRouter.
- When you plug in a real model, you should:
  - enforce **output length caps** (max tokens),
  - avoid logging raw prompts/responses that contain secrets,
  - consider post-processing for redaction or safety classification (especially for OWNER tools that can perform writes).

These rules are in addition to the existing SIONA policies for tools, research, and memory.

---

## 7. Summary

- Brain code (`BrainRouter`, `FusionEngine`, tools, world, memory) talks only to `LanguageEngine`.
- `LanguageEngine` delegates to an `LLMProvider` selected by:
  - explicit constructor argument, or
  - environment (`SSN_LLM_PROVIDER`, `SSN_LLM_ENDPOINT`).
- Today: dummy provider + HTTP stub.
- Tomorrow: swap in:
  - a local HTTP server,
  - an in-process PyTorch model,
  - or a future custom/owner-trained model

without touching the rest of SIONA’s architecture.

