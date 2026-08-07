# SIONA Model Registry Activation Review (EXP-3B-012)

**Experiment ID:** EXP-3B-012  
**Date:** 2026-08-07  
**Status:** MODEL-REGISTRY ACTIVATION REVIEW PASSED WITH CONSERVATIVE CAPABILITY BINDING

## Decision

**ACTIVATION_RECOMMENDED_WITH_CONSERVATIVE_CAPABILITIES**

This decision is computed from evidence and implementation review. Operator overrides cannot change it.

## Scope

EXP-3B-012 prepares the first real SIONA model-registry binding for the approved and evaluated Qwen3-1.7B local baseline. It does **not**:

- start Qwen or llama.cpp;
- open port 8080;
- rerun Gate E or EXP-3B-010;
- train models, create adapters, or modify weights;
- modify `ssn/data` or the protected `world_model.json`;
- accept ADR 0003;
- mark Phase 3B complete or start Phase 4;
- claim production readiness or a SIONA-native model.

## Activation semantics (three distinct states)

| State | Meaning | EXP-3B-012 |
|-------|---------|------------|
| **A — Registry record available** | Canonical metadata exists and validates | **Complete** — `config/model_registry.json` |
| **B — Registry entry bound** | Explicit local provider configuration selects the exact approved entry | **Software support complete** — `build_local_provider_from_env()` |
| **C — Model runtime running** | llama.cpp is running and accepting inference | **Not in scope** — remains operator-controlled |

Registry binding does **not** imply Qwen is always active.

## Approved baseline metadata

| Field | Value |
|-------|-------|
| Provider ID | `siona-local-open-weight-v1` |
| Model ID | `Qwen3-1.7B-Q4_K_M` |
| Model family / version | Qwen3 / 1.7B |
| Runtime | llama.cpp b9968 |
| Format / quantization | GGUF / Q4_K_M |
| Context window (verified locally) | 4096 |
| Source | `ggml-org/Qwen3-1.7B-GGUF` @ `daeb8e2d528a760970442092f6bf1e55c3b659eb` |
| Licence | Apache-2.0 |
| Artifact SHA-256 | `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5` |
| Artifact verification | verified |
| Capability verification | verified (conservative) |

Model ID source: retained local evidence and configured `SSN_LOCAL_MODEL_ID` (`Qwen3-1.7B-Q4_K_M`) — bounded basename only; no paths, credentials, or secrets in the registry manifest.

## Verified registry capabilities (conservative)

| Capability | Status | Notes |
|------------|--------|-------|
| chat | **true** | Bounded local text/chat inference with EXP-3B-011 evidence (9/12 native text VERIFIED) |
| tools | **false** | No direct tool authority |
| structured_json | **false** | Native JSON NOT_VERIFIED; Gate E exact-schema 6/6 recorded separately |
| streaming | **false** | UNSUPPORTED on pinned baseline |
| multimodal | **false** | Not verified |
| context_window | **4096** | Locally executed context only — not the model's advertised 32768 |

## Recorded limitations

- Native text: **9/12 VERIFIED** under EXP-3B-011; **T03, T06, T07 NOT_VERIFIED**
- Native JSON capability: **NOT_VERIFIED** (provider-origin/fallback not captured in original JSON runner)
- Identity-guard native JSON: unverified under EXP-3B-010
- Synchronous mid-request cancellation: not supported
- External open-weight model; optional and replaceable; **not SIONA-native**; **not production certification**

## Implementation summary

1. **Strict registry schema** — exact-type validation; no coercion of string booleans or numeric strings; reject NaN/Infinity; bounded file size; duplicate JSON key rejection; transactional loading; recursive secret-key rejection.
2. **Canonical manifest** — `config/model_registry.json` (metadata only; no endpoints, paths, or secrets).
3. **Provider binding** — `build_local_provider_from_env()` loads registry and binds by exact `(provider_id, model_id)` composite key; mismatch fails closed to deterministic gateway fallback.
4. **Opt-in activation** — default `SSN_LLM_PROVIDER` / `SSN_MODEL_PROVIDER` remain model-free; registry load performs no network, subprocess, or GGUF access.
5. **Observability** — safe metadata: `model_registry_entry_bound`, `model_registry_artifact_status`, `model_registry_capability_status`, `model_registry_activation_status`.

## Prerequisites satisfied

- Gate E recommendation: **REVIEW_ALLOWED_WITH_CONSERVATIVE_CAPABILITIES** (EXP-3B-011)
- Approved artifact provenance and checksum match recorded evidence
- Default CI remains model-free (deterministic/dummy paths unchanged)
- ADR 0003 remains **PROPOSED**; Phase 3B **IN PROGRESS**; Phase 4 **NOT STARTED**

## Wording (authoritative)

MODEL-REGISTRY ACTIVATION REVIEW PASSED WITH CONSERVATIVE CAPABILITY BINDING. THE APPROVED QWEN3-1.7B BASELINE MAY BE REPRESENTED AS A LOCAL OPTIONAL OPEN-WEIGHT REGISTRY ENTRY. VERIFIED REGISTRY CAPABILITIES ARE LIMITED TO BOUNDED TEXT/CHAT INFERENCE AT THE LOCALLY TESTED 4096 CONTEXT. TOOLS, STRUCTURED JSON, STREAMING AND MULTIMODAL CAPABILITIES REMAIN FALSE. REGISTRY BINDING DOES NOT START THE MODEL RUNTIME, DOES NOT GRANT TOOL AUTHORITY, AND DOES NOT MAKE THE EXTERNAL MODEL SIONA-NATIVE.

## Remaining blocker

Operator-controlled runtime startup (state C) and ADR 0003 acceptance remain required before any production capability claim beyond this conservative registry representation.

STATE C DOES NOT MEAN AUTOMATIC OR PERMANENT MODEL STARTUP.

State C means a future controlled verification that:

- starts the already pinned llama.cpp/Qwen baseline;
- explicitly enables the local provider;
- loads the canonical registry;
- proves the exact registry entry is bound;
- proves the provider reaches the real pinned model through that binding;
- confirms safe registry observability;
- performs no tool execution;
- keeps loopback-only operation;
- then shuts the runtime down and verifies port/process closure.

This must be a separate authorized experiment after PR #17 merges.
