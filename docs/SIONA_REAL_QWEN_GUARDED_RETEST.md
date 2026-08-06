# SIONA Real-Qwen Guarded-Path Retest (EXP-3B-010)

Controlled comparison of raw Qwen output versus final SIONA-guarded responses
on the pinned local baseline.

## Status

**CONTROLLED REAL LOCAL-MODEL GUARDED-PATH RETEST EXECUTED AGAINST THE PINNED
QWEN3-1.7B BASELINE. ALL 21 FINAL SIONA-GUARDED RESPONSES PASSED THE DEFINED
IDENTITY, SELECTION, UNSUPPORTED-INFORMATION, INSTRUCTION-RESISTANCE,
NO-RECORD AND STRUCTURED-OUTPUT BOUNDARIES. RAW QWEN RESPONSES AND FINAL
SIONA RESPONSES WERE RETAINED LOCALLY; ONLY SANITIZED TRUNCATED EXCERPTS,
HASHES AND ADJUDICATION METADATA WERE COMMITTED. NO TOOL EXECUTION, WEBSITE
CHANGE, TRAINING, ADAPTER TRAINING, EMBEDDINGS, MODEL-WEIGHT CHANGE OR
MODEL-REGISTRY ACTIVATION OCCURRED. RUNTIME WAS SHUT DOWN AFTER TESTING.**

**MODEL-NATIVE STRUCTURED JSON REMAINS UNVERIFIED; GUARDED DETERMINISTIC JSON
FALLBACK CONTAINED THE FAILURES.**

This does **not** claim:

- Qwen was trained or fixed;
- SIONA is a native model;
- production readiness;
- Gate E completion;
- model registry activation;
- Phase 3B completion;
- ADR 0003 acceptance.

## Baseline

| Item | Value |
|------|--------|
| Main SHA | `0bf01e0fb82d796a1c6c7230ac8840ef6e909ec1` |
| Runtime | llama.cpp b9968 |
| Runtime source commit | `1d1d9a9ed7a4f09c4225ea4cc8fd3bd1cf2c940f` |
| Model | `Qwen3-1.7B-Q4_K_M.gguf` |
| Model size | 1282439264 bytes (MATCH) |
| Model SHA-256 | `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5` (MATCH) |
| Endpoint | loopback `127.0.0.1:8080` only |
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
| Model-native JSON verified | **false** (0/6 MODEL_VALIDATED; 6/6 DETERMINISTIC_GUARD_FALLBACK) |
| Actual tool executions | 0 |
| Website changed | false |
| Model registry | inactive |

Raw-control responses may fail; they demonstrate the base-model behaviour and
do not fail the guarded campaign.

## Evidence

| Kind | Location |
|------|----------|
| Complete local responses | `C:\Users\njaji\SIONA\reports\EXP-3B-010` (outside Git) |
| Committed adjudication | `docs/evidence/EXP-3B-010_ADJUDICATION.json` |
| Committed summary | `docs/evidence/EXP-3B-010_SUMMARY.json` |
| Committed manifest | `docs/evidence/EXP-3B-010_EVIDENCE_MANIFEST.json` |

Committed excerpts are sanitized and capped at 240 characters. Complete raw and
final texts are retained locally only.

## Runner

```bash
SSN_OFFLINE=1 python scripts/run_real_guarded_identity_retest.py --confirm-real-model-campaign
```

Without `--confirm-real-model-campaign`, the runner fails closed before contacting
the server.

## Next

Phase 3B remains **in progress**. Next blocker: Gate E breadth; model-registry
activation review; ADR 0003 acceptance; Phase 3B completion decision. Model
registry activation must not occur before those results are reviewed.
