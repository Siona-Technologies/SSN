# SIONA State C — Registry-Bound Real-Runtime Verification (EXP-3B-013)

**Experiment ID:** EXP-3B-013  
**Date:** 2026-08-07  
**Base main SHA:** `256a0e6b0dcb0cfa4f819bc207ace83bdf3e2dde`  
**Decision:** `STATE_C_VERIFIED`

## Authoritative wording

STATE C CONTROLLED REGISTRY-BOUND REAL-RUNTIME VERIFICATION PASSED.

STATE C DOES NOT MEAN AUTOMATIC OR PERMANENT MODEL STARTUP.

## Activation states (must not be collapsed)

| State | Meaning | EXP-3B-013 |
|-------|---------|------------|
| **A — Registry record available** | Canonical metadata exists and validates | **True** — `config/model_registry.json` |
| **B — Registry entry bound** | Exact approved entry selected via `build_local_provider_from_env()` | **True** before inference |
| **C — Real runtime running** | Pinned llama.cpp accepting loopback inference | **True during experiment only** |
| **D — Real inference completed** | Real bounded text response via LocalOpenWeightProvider | **True** (2/2 probes) |
| **E — Runtime shut down** | Process/port closed; no auto-restart | **True** after experiment |

## Path proven

SIONA → canonical `config/model_registry.json` → exact approved registry entry →
`LocalOpenWeightProvider` → real loopback llama.cpp → `Qwen3-1.7B-Q4_K_M` →
bounded real response → safe registry observability → controlled shutdown.

## Approved baseline (unchanged)

| Field | Value |
|-------|-------|
| Provider ID | `siona-local-open-weight-v1` |
| Model ID | `Qwen3-1.7B-Q4_K_M` |
| Runtime | llama.cpp b9968 (`PINNED_LLAMA_CPP_B9968`) |
| Artifact | `Qwen3-1.7B-Q4_K_M.gguf` (`APPROVED_QWEN3_1_7B_Q4_K_M`) |
| Artifact SHA-256 | `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5` |
| Location class | `OPERATOR_LOCAL_OUTSIDE_GIT` |
| `siona_native` | false |

## Capabilities (before and after inference)

| Capability | Value |
|------------|-------|
| chat | true |
| tools | false |
| structured_json | false |
| streaming | false |
| multimodal | false |
| context_window | 4096 |

A successful text response did **not** auto-promote any other capability.
`config/model_registry.json` was **not** mutated.

## Runtime startup (sanitized)

Pinned EXP-3B-005 command reused with `-a Qwen3-1.7B-Q4_K_M` so `/v1/models`
advertises the approved registry model ID for exact `VERIFY_MODEL_ID` binding:

```text
PINNED_LLAMA_CPP_B9968/llama-server.exe
  -m APPROVED_QWEN3_1_7B_Q4_K_M/Qwen3-1.7B-Q4_K_M.gguf
  --host 127.0.0.1 --port 8080 -c 4096 -n 512 -ngl 0 -t 4
  --reasoning off -a Qwen3-1.7B-Q4_K_M
```

- Bind: loopback only (`127.0.0.1:8080`); not `0.0.0.0`
- PID: 4688
- Health: HTTP 200 / `status=ok`
- Startup result: SUCCESS

## Provider binding (process-local env only)

```text
SSN_LLM_PROVIDER=local
SSN_MODEL_PROVIDER=local
SSN_LOCAL_MODEL_ID=Qwen3-1.7B-Q4_K_M
SSN_LOCAL_MODEL_ENDPOINT=http://127.0.0.1:8080
SSN_LOCAL_MODEL_API_DIALECT=openai_chat
SSN_LOCAL_MODEL_VERIFY_MODEL_ID=1
```

Canonical registry path used (no `SSN_MODEL_REGISTRY_PATH` override).
Provider constructed only via `build_local_provider_from_env()`.

Pre-inference observability required and observed:

- `model_registry_entry_bound=true`
- provider=`siona-local-open-weight-v1`
- model=`Qwen3-1.7B-Q4_K_M`
- artifact/capability verification=`verified`
- conservative capabilities as above
- `siona_native=false` / `trained_siona_native=false`

## Controlled probes

| ID | Real? | Latency | Excerpt | SHA-256 |
|----|-------|---------|---------|---------|
| SC-T01 | yes | 1464.8 ms | This is a bounded local text inference test. | `d2eec60f0c989553edefd96860e14fd68a6849a7b45f1eaf3a2e421f9e4b89dc` |
| SC-T02 | yes | 457.9 ms | 4 | `4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a` |

- Real provider calls: 2
- Real model responses: 2
- Deterministic fallback during live probes: 0
- Tool executions: 0
- llama.cpp server log grew during probes (588 → 2134 bytes)

Deterministic fallback was **not** counted as State C success.

## Shutdown and post-checks

- Shutdown method: `terminate` (success)
- Port 8080: CLOSED
- llama.cpp: STOPPED
- Qwen: STOPPED
- Local model unavailable after shutdown: true
- Deterministic fallback after shutdown: works (`siona-deterministic-model-v1`)
- Automatic restart: not observed

## Explicit non-claims

- ADR 0003 remains **Proposed**
- Phase 3B remains **In Progress**
- Phase 4 remains **Not Started**
- No production readiness claim
- No SIONA-native model claim
- No tools / structured_json / streaming / multimodal enablement
- No training, LoRA/QLoRA/PEFT, embeddings, weight modification, model download
- No website or `ssn/data` changes
- No persistent auto-start or machine-wide environment persistence

## Remaining blocker

**ADR 0003 ACCEPTANCE + PHASE 3B COMPLETION DECISION**

That closeout is **not** executed by this experiment.

## Evidence

- `docs/evidence/EXP-3B-013_STATE_C.json`
- Operator-local raw artifacts: `OPERATOR_LOCAL_OUTSIDE_GIT`
