# SIONA / SSN Environment Configuration

This document describes runtime environment variables used by SIONA (SSN) for:
- offline-deterministic operation,
- optional live network research,
- state persistence for proposal/commit workflows,
- safe rate limiting.

## Principles
- Default behavior should be deterministic and offline-safe.
- Live network access must be explicitly enabled.
- Secrets (API keys) must never be stored in traces, memory, or committed to git.
- CI must remain deterministic: offline tests always pass; live tests are optional and env-gated.

---

## Mode Flags

### `SSN_OFFLINE`
- Values: `0` or `1`
- When `1`, forces offline behavior:
  - `net.search` uses deterministic mock results
  - `research.*` tools behave accordingly
- Recommended:
  - CI: `SSN_OFFLINE=1`
  - Local development: set to `0` only when doing live research tests

### `SSN_LIVE_SEARCH`
- Values: `0` or `1`
- Enables live search providers in `net.search` (Brave, DDG fallbacks, Wikipedia).
- Recommended:
  - CI: `0`
  - Local/manual: `1` when validating live behavior

### `SSN_LIVE_STRICT`
- Values: `0` or `1`
- Strict live mode disables mock fallback when providers fail.
- Intended for validating real network behavior.
- Recommended:
  - CI: `0`
  - Local/manual: `1` only when you want failure instead of mock fallback

---

## Provider Configuration (Brave Search)

### `SSN_BRAVE_API_KEY`
- Brave Search API token used by `net.search` provider "brave-search".
- Must never be committed.
- Must never appear in tool traces or memory.

Optional tuning:
- `SSN_BRAVE_COUNTRY` (e.g., `KE`, `US`, `GB`)
- `SSN_BRAVE_LANG` (e.g., `en`, `en-US`, `sw`)

---

## State / Persistence

### `SSN_STATE_DIR`
- Directory used for stateful, file-backed workflows, including:
  - memory proposal pending store
  - commit history store (idempotency)
- Recommended default: `.ssn_state`

### `SSN_RATE_LIMIT_PATH`
- Path to file-backed rate limit store used by ToolRegistry.
- Recommended default: `${SSN_STATE_DIR}/rate_limits.json`

**Important:** `.ssn_state/` should be gitignored and treated as local runtime state.

---

## Debugging (Optional)

### `SSN_DEBUG` / `SSN_TOOL_DEBUG`
- Values: `0` or `1`
- Enables additional diagnostics.
- Must remain safe: no secrets in traces.

---

## LLM Provider (Phase 1)

### `SSN_LLM_PROVIDER`
- Values: `dummy` (default) | `http`
- `dummy` → `LocalDummyLLMProvider` (offline, deterministic)
- `http` → `HttpLLMProvider` (local/remote inference server)

### `SSN_LLM_ENDPOINT`
- Required when `SSN_LLM_PROVIDER=http`
- Example: `http://127.0.0.1:8000/generate`
- Mock dev server: `python scripts/mock_llm_server.py`

### `SSN_LLM_ENDPOINT_FAST` / `SSN_LLM_ENDPOINT_DEEP` (planned)
- Optional mode-specific endpoints for BrainRouter fast/deep modes
- Fallback: `SSN_LLM_ENDPOINT`

See `LLM_STRATEGY_V10.md` for the HTTP JSON contract.

---

## Identity (OWNER)

### `SSN_MASTER_KEY`
- Master key for OWNER verification in CLI/HTTP (local dev)
- Must never be committed, traced, or stored in memory

---

## Knowledge Store

### `SSN_KNOWLEDGE_PATH`
- Path to curated knowledge JSONL (default: `ssn/knowledge/knowledge.jsonl`)

---

## Law configuration (Phase 3)

### `SSN_HOME_LAW_PATH`
- Path to OWNER home law YAML (default: `ssn/policy/home_law_samson.yaml`)

### `SSN_WORLD_LAW_PATH`
- Path to world law YAML (default: `ssn/policy/world_law.yaml`)

### `SSN_SYSTEM_LAW_PATH`
- Path to system law YAML (default: `ssn/policy/system_law.yaml`)

### `SSN_TENANT_ID`
- Optional default tenant id for HTTP deployments

See `deploy/README.md` for multi-tenant layout examples.

---

## HTTP Front Door (Phase 2)

### `SSN_HTTP_HOST` / `SSN_HTTP_PORT`
- Bind address for `python -m ssn.runtime.http_server` (default: `127.0.0.1:8080`)

### `SSN_HTTP_QUIET`
- Set to `1` to suppress HTTP access logs

Start server:
```bash
SSN_OFFLINE=1 python -m ssn.runtime.http_server --port 8080
```

Chat request:
```bash
curl -X POST http://127.0.0.1:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"hello","role":"GUEST","offline":true}'
```

OWNER auth header: `X-SSN-Master-Key: <your-key>` (never commit).

Sessions persist under `${SSN_STATE_DIR}/sessions/`.

---

## Voice / speech (Phase 4)

Optional offline speech backends. CI uses dummy backends (no mic/speaker). Install optional deps from `requirements-voice.txt`.

### `SSN_STT_BACKEND`
- Values: `dummy` (default) | `text` | `whisper_cli` | `faster_whisper`
- `dummy` — structured response, no microphone (CI-safe)
- `text` — requires `--text`, tool `args.text`, or `SSN_STT_TEXT`
- `whisper_cli` — whisper.cpp `main` binary; set `SSN_WHISPER_CLI` if not on PATH
- `faster_whisper` — Python `faster-whisper` + `sounddevice` for mic capture

### `SSN_STT_TEXT`
- Optional fixed transcript for dev/CI when bypassing mic

### `SSN_WHISPER_CLI` / `SSN_WHISPER_ARGS` / `SSN_WHISPER_MODEL`
- whisper.cpp CLI path and args; model size for faster-whisper (default `base`)

### `SSN_TTS_BACKEND`
- Values: `dummy` (default) | `stdout` | `pyttsx3` | `piper_cli`
- `stdout` — prints `[TTS:lang] text` (CI-safe simulation)
- `pyttsx3` — local CPU TTS via SAPI/espeak
- `piper_cli` — Piper neural TTS; set `SSN_PIPER_CLI` and `SSN_PIPER_MODEL`

### CLI voice loop
```bash
SSN_OFFLINE=1 SSN_MASTER_KEY=dev-key SSN_TTS_BACKEND=stdout \
  python -m ssn.runtime.cli voice-once --text "hello" --offline
```

Sense tick demo:
```bash
SSN_OFFLINE=1 python scripts/sense_tick_demo.py
```

---

## Recommended Configurations

### CI (Deterministic)
- `SSN_OFFLINE=1`
- `SSN_LIVE_SEARCH=0`
- `SSN_LIVE_STRICT=0`
- No API keys

### Local Development (Offline by default)
- `SSN_OFFLINE=1` (default)
- When testing live:
  - `SSN_OFFLINE=0`
  - `SSN_LIVE_SEARCH=1`
  - optionally `SSN_LIVE_STRICT=1`
  - set `SSN_BRAVE_API_KEY` in your local `.env` (never commit)

---

## Security Notes
- API keys must not be logged, traced, or stored in memory.
- All network tools must remain bounded: timeouts, max bytes, and max chars.
- Live tests must be env-gated and never required for CI green.
