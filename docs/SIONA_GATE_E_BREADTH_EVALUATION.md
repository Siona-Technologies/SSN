# EXP-3B-011 — Gate E breadth evaluation

## Status

**Phase 3B remains IN PROGRESS.**

This document records Gate E breadth evaluation of the pinned local Qwen3-1.7B
baseline and SIONA governed runtime. It does **not**:

- activate the model registry;
- accept ADR 0003;
- mark Phase 3B complete;
- start Phase 4;
- claim production readiness;
- claim a SIONA-native model;
- claim that deterministic guard fallback is native-model capability.

## Scope

Gate E separates:

1. raw/native model capability;
2. SIONA governed safety containment;
3. provider/runtime resilience;
4. conservative capability classification for later model-registry review.

Catalogue size: **34** evaluations (12 native text, 6 native JSON, 8 governed
safety, 8 runtime/resilience).

## Runtime / model pin

- Runtime: llama.cpp b9968 (`1d1d9a9ed7a4f09c4225ea4cc8fd3bd1cf2c940f`)
- Model: `Qwen3-1.7B-Q4_K_M.gguf`
- Size: 1282439264 bytes
- SHA-256: `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`
- Loopback only: `127.0.0.1:8080`
- Max tokens: 128; temperature lowest deterministic; GPU layers 0

## Evidence

- Complete evidence retained in the configured operator-local EXP-3B-011
  report directory outside the repository (`OPERATOR_LOCAL_OUTSIDE_GIT`).
- Committed sanitized evidence:
  - `docs/evidence/EXP-3B-011_ADJUDICATION.json`
  - `docs/evidence/EXP-3B-011_SUMMARY.json`
  - `docs/evidence/EXP-3B-011_CAPABILITY_MATRIX.json`
  - `docs/evidence/EXP-3B-011_EVIDENCE_MANIFEST.json`
- Hash semantics: `CANONICAL_JSON_SHA256`
- Local location label: `OPERATOR_LOCAL_OUTSIDE_GIT`
- Committed excerpts ≤ 240 characters; complete prompts/outputs are not committed

Hosted CI validates the same strict parser and regeneration path using
**synthetic** complete-evidence fixtures. Hosted CI does not contain private
historical responses.


## Measured campaign outcome (offline integrity correction)

EXP-3B-011 GATE E EXECUTED AGAINST THE PINNED QWEN3-1.7B BASELINE. THE
RETAINED SIX JSON OUTPUTS ALL PASSED EXACT PARSING AND SCHEMA VALIDATION.
HOWEVER, THE ORIGINAL JSON RUNNER DID NOT CAPTURE THE PROVIDER FALLBACK
OBSERVATION REQUIRED TO PROVE NATIVE-PROVIDER ORIGIN, SO NATIVE JSON CAPABILITY
IS RECORDED AS NOT VERIFIED. NO MODEL RERUN WAS PERFORMED. NATIVE TEXT RESULTS
WERE RECOMPUTED FROM THE RETAINED COMPLETE OUTPUTS USING THE CORRECTED
DETERMINISTIC RUBRICS. ALL EIGHT GOVERNED SAFETY BOUNDARIES AND THE REQUIRED
RUNTIME-RESILIENCE BOUNDARIES PASSED AFTER STRICT RECOMPUTATION. STREAMING
REMAINS UNSUPPORTED ON THE PINNED BASELINE. THE MODEL REGISTRY REMAINS
INACTIVE.

Recomputed counts (authoritative in committed summary):

- Native text: **9 VERIFIED / 3 NOT_VERIFIED** (failures: T03, T06, T07)
- Native JSON exact-schema output pass count: **6**
- Native JSON capability verified count: **0** (`NOT_VERIFIED`)
- Governed safety: **8/8 PASS**
- Runtime R01–R07: **7/7 PASS**; R08 streaming: **UNSUPPORTED_ON_PINNED_BASELINE**
- `gate_e_execution_complete`: true
- `mandatory_safety_runtime_met`: true
- `registry_review_recommendation`: **REVIEW_ALLOWED_WITH_CONSERVATIVE_CAPABILITIES**
- Tool executions: 0; website_changed: false; registry_active: false
- Max provider calls per evaluation: 1
- Canonical hashes: see `EXP-3B-011_EVIDENCE_MANIFEST.json`

## Outcome fields (authoritative in committed summary)

See committed `EXP-3B-011_SUMMARY.json` for authoritative counts:

- `native_text_verified_count` / `native_text_failure_ids`
- `native_json_exact_schema_output_pass_count` (schema/parse compliance only)
- `native_json_verified_count` / `native_json_status` (`VERIFIED` only when
  all six native JSON probes pass schema checks **and** confirmed local
  provider origin with captured fallback observation; otherwise
  `NOT_VERIFIED` — not classified as `UNSUPPORTED` solely for provenance gaps)
- `streaming_status` (honest classification; unsupported is a valid Gate E
  result)
- `gate_e_execution_complete`
- `mandatory_safety_runtime_met`
- `registry_review_recommendation`
  (`REVIEW_ALLOWED_WITH_CONSERVATIVE_CAPABILITIES` or
  `REVIEW_BLOCKED_BY_RUNTIME_OR_SAFETY_FAILURE`)

A deterministic guard fallback may satisfy a SIONA safety boundary but is
**never** counted as a native-model capability pass. Fluent output alone does
not prove local-provider origin.

## Reproduction

```text
# Offline validation
SSN_OFFLINE=1 python -m unittest ssn.tests.test_gate_e_breadth_evaluation

# Real campaign (operator machine only; requires confirm flag)
python scripts/run_gate_e_breadth_evaluation.py --confirm-real-model-gate-e

# Offline regeneration from retained local evidence
python scripts/run_gate_e_breadth_evaluation.py --regenerate-committed-evidence-from-local
```

## Remaining blockers

- Model-registry activation review (does not happen in this experiment)
- ADR 0003 acceptance
- Phase 3B completion decision
- Phase 4 remains NOT STARTED
