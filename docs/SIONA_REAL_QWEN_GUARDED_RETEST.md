# SIONA Real-Qwen Guarded-Path Retest (EXP-3B-010)

Controlled comparison of raw Qwen output versus final SIONA-guarded responses
on the pinned local baseline.

## Status

**CONTROLLED REAL LOCAL-MODEL GUARDED-PATH RETEST EXECUTED AGAINST THE PINNED
QWEN3-1.7B BASELINE. ALL 21 FINAL SIONA-GUARDED RESPONSES PASSED THE DEFINED
IDENTITY, SELECTION, UNSUPPORTED-INFORMATION, INSTRUCTION-RESISTANCE,
NO-RECORD AND STRUCTURED-OUTPUT BOUNDARIES. TWO REAL MODEL OUTPUTS WERE
ACCEPTED DIRECTLY; NINETEEN FINAL RESPONSES USED DETERMINISTIC GUARD
CONTAINMENT. ALL SIX JSON PROBES REQUIRED DETERMINISTIC FALLBACK, SO
MODEL-NATIVE STRUCTURED JSON REMAINS UNVERIFIED. COMPLETE RAW QWEN RESPONSES
AND FINAL SIONA RESPONSES WERE RETAINED IN AN OPERATOR-LOCAL DIRECTORY OUTSIDE
GIT. COMMITTED EVIDENCE CONTAINS ONLY SANITIZED TRUNCATED EXCERPTS,
PER-RESPONSE HASHES AND STRICTLY RECOMPUTED ADJUDICATION METADATA. THE MODEL
ARTIFACT WAS VERIFIED BY PINNED SIZE AND SHA-256; THE PROVIDER WAS BOUND TO THE
SINGLE SERVER-REPORTED MODEL ID, BUT AN INDEPENDENT EXPECTED SERVER-ID MATCH
WAS NOT ESTABLISHED. RUNTIME PROCESS TERMINATION COMPLETED AND POST-RUN LOCAL
PROCESS/PORT STATE WAS VERIFIED CLOSED; THE ORIGINAL RUNNER'S SHUTDOWN-LOG
PATH REPORTED AN ERROR AND HAS BEEN CORRECTED FOR FUTURE REPRODUCTIONS. NO
TOOL EXECUTION, WEBSITE CHANGE, TRAINING, ADAPTER TRAINING, EMBEDDINGS,
MODEL-WEIGHT CHANGE OR MODEL-REGISTRY ACTIVATION OCCURRED.**

This does **not** claim:

- raw Qwen passed 21/21;
- Qwen was trained or fixed;
- SIONA is a native model;
- model-native JSON verification;
- production readiness;
- Gate E completion;
- model registry activation;
- Phase 3B completion;
- ADR 0003 acceptance.

Phase 3B remains **IN PROGRESS**. ADR 0003 remains **PROPOSED**. Phase 4 remains
**NOT STARTED**.

## Baseline

| Item | Value |
|------|--------|
| Main SHA | `0bf01e0fb82d796a1c6c7230ac8840ef6e909ec1` |
| Runtime | llama.cpp b9968 |
| Runtime source commit | `1d1d9a9ed7a4f09c4225ea4cc8fd3bd1cf2c940f` |
| Model | `Qwen3-1.7B-Q4_K_M.gguf` |
| Model size | 1282439264 bytes (MATCH) |
| Model SHA-256 | `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5` (MATCH) |
| Endpoint | loopback only |
| Max tokens | 128 |

## Catalogue (21 probes)

- Positive: P1–P4
- Selection: S1–S2
- Unsupported: U1–U3, U6
- Instruction: A1–A4
- No-record: N2
- JSON: J1A/J1B, J2A/J2B, J3A/J3B

## Outcomes

| Metric | Result |
|--------|--------|
| Guarded campaign acceptance | **true** (21/21) |
| Model outputs accepted directly | **2** |
| Deterministic guard containment | **19** |
| Model-native JSON verified | **false** (0/6 MODEL_VALIDATED; 6/6 DETERMINISTIC_GUARD_FALLBACK) |
| Actual tool executions | 0 |
| Website changed | false |
| Model registry | inactive |

Raw-control responses may fail; they demonstrate base-model behaviour and do
not fail the guarded campaign.

## Evidence integrity

| Kind | Location |
|------|----------|
| Complete local responses | Operator-local EXP-3B-010 report directory outside the repository (`OPERATOR_LOCAL_OUTSIDE_GIT`) |
| Committed adjudication | `docs/evidence/EXP-3B-010_ADJUDICATION.json` |
| Committed summary | `docs/evidence/EXP-3B-010_SUMMARY.json` |
| Committed manifest | `docs/evidence/EXP-3B-010_EVIDENCE_MANIFEST.json` |

Hash semantics: **CANONICAL_JSON_SHA256** (canonical-object hashes of adjudication
and summary; the manifest references those hashes and does not hash itself).

Committed excerpts are sanitized and capped at 240 characters. Complete raw and
final texts are retained locally only. Absolute operator paths are not committed.

Complete local evidence was revalidated locally with a strict non-coercive parser
that independently recomputes adjudication labels. Hosted CI validates the same
strict parser and offline regeneration path using synthetic complete-evidence
fixtures; hosted CI does not contain the private historical complete responses.
No Qwen rerun occurred for integrity corrections. Historical per-response hashes
remain unchanged.

## Server model-ID wording

SERVER REPORTED EXACTLY ONE NON-EMPTY MODEL ID AND THE PROVIDER WAS BOUND TO
THAT REPORTED ID. THE MODEL ARTIFACT ITSELF WAS INDEPENDENTLY VERIFIED BY THE
PINNED GGUF SIZE AND SHA-256 BEFORE SERVER STARTUP.

## Runtime shutdown wording

RUNTIME PROCESS TERMINATION COMPLETED AND POST-RUN LOCAL PROCESS/PORT STATE WAS
VERIFIED CLOSED. THE ORIGINAL RUNNER'S SHUTDOWN-LOG PATH REPORTED AN ERROR;
THIS PR CORRECTS THAT RUNNER DEFECT FOR FUTURE REPRODUCTIONS.

## Runner

```bash
# Offline regeneration from retained local complete evidence (no model):
python scripts/run_real_guarded_identity_retest.py --regenerate-committed-evidence-from-local

# Real campaign (mutually exclusive with regeneration):
SSN_OFFLINE=1 python scripts/run_real_guarded_identity_retest.py --confirm-real-model-campaign
```

## Next

Phase 3B remains **in progress**. Next blocker: model-registry activation
review; ADR 0003 acceptance; Phase 3B completion decision. Gate E breadth
(EXP-3B-011) is recorded.
activation review; ADR 0003 acceptance; Phase 3B completion decision. Model
registry activation must not occur before those results are reviewed.
