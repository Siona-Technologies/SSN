# SIONA Governed Identity Response Guard (EXP-3B-009)

Explicit, opt-in identity response contract with deterministic preflight,
post-provider validation, and safe text/JSON fallback.

## Status

**IMPLEMENTED AND VALIDATED OFFLINE — EXPLICIT GOVERNED IDENTITY RESPONSE
CONTRACT, STRICT INCLUDED-RECORD VALIDATION, PRE-PROVIDER SAFETY DECISIONS,
CANONICAL POST-PROVIDER GROUNDING VALIDATION, PROVIDER-FAILURE CONTAINMENT AND
DETERMINISTIC TEXT/JSON FALLBACK ADDED. OVERSIZED PROMPTS AND RESPONSES,
PROVIDER FALLBACKS, TOOL PROPOSALS, RESPONSE-CONTRACT BYPASSES AND THE
HISTORICAL EXP-3B-008 FAILURE CLASSES ARE COVERED BY MOCKED DETERMINISTIC
TESTS. NO REAL MODEL WAS STARTED OR RERUN. MODEL-NATIVE STRUCTURED JSON REMAINS
UNVERIFIED. NO MODEL TRAINING, ADAPTER TRAINING, EMBEDDINGS, MODEL-WEIGHT
CHANGES OR MODEL-REGISTRY ACTIVATION OCCURRED.**

This does **not**:

- claim EXP-3B-008 campaign acceptance now passed;
- claim real-Qwen guarded behavior was verified;
- claim Qwen itself was fixed or changed;
- verify model-native structured JSON;
- complete Gate E;
- activate the model registry;
- train adapters or create a SIONA-native model;
- claim production readiness;
- complete Phase 3B.

Phase 3B remains **in progress**. ADR 0003 remains **Proposed**. Phase 4 remains
**not started**.

MODEL-NATIVE STRUCTURED JSON remains **UNVERIFIED**. The guarded deterministic
JSON fallback is implemented and offline tested. Controlled real-Qwen
guarded-path retest (EXP-3B-010) confirmed all 21 guarded finals pass while
model-native JSON stayed unverified; see
[SIONA_REAL_QWEN_GUARDED_RETEST.md](SIONA_REAL_QWEN_GUARDED_RETEST.md).

## Opt-in contract

```python
GovernedIdentityResponseContract(
    requested_subject_ids=("product:siona",),
    mode=GovernedResponseMode.TEXT,  # or JSON (exactly one subject)
    strict_grounding=True,
    permit_actions=False,
    permit_prompt_disclosure=False,
)
```

Supply the **exact typed** contract on `GovernedContextInput.response_contract`
together with an exact built-in `tuple`/`list` of `IdentityFactRecord` values.
No automatic registry load.

| Input shape | Behaviour |
|-------------|-----------|
| Feature flag off (`SSN_GOVERNED_CONTEXT` unset/`0`) | Intentional compatibility exception — legacy path; guard not activated |
| No `GovernedContextInput` | Legacy |
| `GovernedContextInput` without contract | Existing governed prompt-context only |
| Mapping containing `response_contract` | Fail closed (`response_contract_requires_typed_input`); provider not called |
| Exact typed contract + non-`PUBLIC_RESPONSE` audience | Fail closed (`response_contract_invalid_audience`); provider not called |
| Exact typed `GovernedContextInput` + contract + `PUBLIC_RESPONSE` | Strict identity response guard |

## Guard behaviour

1. **Included-record validation** — exact `tuple`/`list` only; exact
   `IdentityFactRecord`; bounded fields; unique subject/diagnostic IDs;
   requested/included mapping consistency. Fail closed with
   `included_records_invalid` before provider call.
2. **Preflight** — oversized prompt, unavailable subject, disclosure, action,
   private-category, and fabrication blocks with **zero** model inferences when
   safe. Blocked JSON requests return refusal/unavailable **text**, never a false
   supported JSON object.
3. **Provider call** — at most **one** inference; inference count incremented
   immediately before invoke; bounded identity rules (+ JSON instruction when
   needed) separate from record statements; contract object never exposed to the
   provider; no approval metadata in the model-visible block.
4. **Provider containment** — exceptions, `fallback_used=True`, non-empty
   `fallback_reason`, malformed metadata, and tool proposals fail closed with
   deterministic fallback. Tool proposals never execute. Unsafe strings
   (exception text, URLs, paths, tool names/args, fallback bodies) never enter
   public metadata.
5. **Canonical text grounding** — for `PUBLIC_RESPONSE` + `strict_grounding`,
   model text is accepted only when semantically identical to the canonical
   renderer (permitted whitespace normalization only). Accepted responses return
   **canonical renderer output**, not the raw model string. Multi-subject
   delimiter: `\n\n` (records sorted by subject ID). Extra sentences, dates,
   praise, titles, or paraphrases are rejected (`model_output_not_canonical`).
6. **JSON mode** — exactly one requested subject; valid model JSON is
   re-rendered as compact SIONA JSON (`MODEL_VALIDATED`); invalid JSON with an
   available approved record uses `DETERMINISTIC_GUARD_FALLBACK` without a second
   call.
7. **Bounds** — user prompt ≤ 4000 chars; model output ≤ 8000 chars;
   final response ≤ 8000 chars; provider-visible prompt ≤ 12000 chars.

## Canonical safe metadata

Every guarded response includes:

- `governed_identity_guard_applied`
- `governed_identity_preflight_blocked`
- `governed_identity_model_output_accepted`
- `governed_identity_fallback_used`
- `governed_identity_reason`
- `governed_identity_response_mode`
- `governed_identity_requested_count`
- `governed_identity_included_count`
- `governed_identity_structured_source`
- `governed_identity_model_inference_count`

The draft alias `governed_identity_guard_accepted` was **removed**. Do not expose
approved statements, rejected output, tool arguments, or diagnostic IDs in
metadata.

## Structured JSON schema

JSON mode requires **exactly one** normalized requested subject ID.

```json
{
  "subject_id": "product:siona",
  "supported_statement": "<exact approved statement>",
  "unsupported_claims": []
}
```

Sources: `MODEL_VALIDATED`, `DETERMINISTIC_GUARD_FALLBACK`, or empty when no
structured response exists (blocked/unavailable JSON requests).

## Modules

- `ssn/governance/identity_response_guard.py`
- Additive fields on `GovernedContextInput` / `GovernedContextLLMProvider`
- `ssn/core/language_engine.py` (safe metadata passthrough)
- Tests: `ssn/tests/test_governed_identity_response_guard.py`

## Next step

A separately controlled experiment may rerun failed EXP-3B-008 categories against
real Qwen **after** this implementation is reviewed and merged. That experiment
is not part of this change and was not run here.
