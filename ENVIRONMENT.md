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
