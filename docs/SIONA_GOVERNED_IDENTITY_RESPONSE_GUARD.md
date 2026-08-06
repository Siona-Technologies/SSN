# SIONA Governed Identity Response Guard (EXP-3B-009)

Explicit, opt-in identity response contract with deterministic preflight,
post-provider validation, and safe text/JSON fallback.

## Status

**IMPLEMENTED AND VALIDATED OFFLINE** — mocked deterministic tests only.

This does **not**:

- claim EXP-3B-008 campaign acceptance now passed;
- claim Qwen itself was fixed;
- verify real-model hardening;
- complete Gate E;
- activate the model registry;
- train adapters or create a SIONA-native model;
- complete Phase 3B.

MODEL-NATIVE STRUCTURED JSON remains **UNVERIFIED**. The guarded runtime JSON
contract is implemented and deterministically tested.

## Opt-in contract

```python
GovernedIdentityResponseContract(
    requested_subject_ids=("product:siona",),
    mode=GovernedResponseMode.TEXT,  # or JSON
    strict_grounding=True,
    permit_actions=False,
    permit_prompt_disclosure=False,
)
```

Supply it on `GovernedContextInput.response_contract` together with explicitly
selected records. No automatic registry load.

| Input shape | Behaviour |
|-------------|-----------|
| No `GovernedContextInput` | Legacy |
| `GovernedContextInput` without contract | Existing governed prompt-context only |
| `GovernedContextInput` + contract + `PUBLIC_RESPONSE` | Strict identity response guard |

## Guard behaviour

1. **Preflight** — unavailable / disclosure / action / private-category blocks
   with **zero** model inferences when safe.
2. **Provider call** — at most **one** inference; bounded identity rules separate
   from record statements; no approval metadata in the model-visible block.
3. **Post-validate** — reject disclosure, praise, contradiction, action claims,
   selection-boundary leaks, incomplete grounding, malformed JSON.
4. **Deterministic fallback** — approved statements or bounded refusals; no
   second model call.

## Structured JSON schema

```json
{
  "subject_id": "product:siona",
  "supported_statement": "<exact approved statement>",
  "unsupported_claims": []
}
```

Sources: `MODEL_VALIDATED` or `DETERMINISTIC_GUARD_FALLBACK`.

## Modules

- `ssn/governance/identity_response_guard.py`
- Additive fields on `GovernedContextInput` / `GovernedContextLLMProvider`
- Tests: `ssn/tests/test_governed_identity_response_guard.py`

## Next step

A separately controlled experiment may rerun failed EXP-3B-008 categories against
real Qwen **after** this implementation is reviewed and merged.
