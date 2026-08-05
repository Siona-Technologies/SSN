# SIONA Consent and Revocation

**Status:** Foundation policy (hardened authorization semantics)

## Principles

1. Subject consent is required for private information.
2. One co-founder cannot authorize another co-founder's private information.
3. Owner authentication does not override another person's consent rights.
4. Revocation overrides prior approval.
5. Model output cannot grant consent.
6. Consent records must retain provenance (who granted, when, exact grantee, exact uses).
7. Actor identity alone is never authentication. Policy decisions require a trusted
   `PolicyContext` with `actor_authenticated=True`.

## PolicyContext

Authorization uses an immutable context:

- `actor_id`
- `actor_authenticated`
- `verified_owner`
- `authorized_company_approver_ids`

Unauthenticated actors are denied even when `actor_id` equals a subject ID.

`actor_authenticated` and `verified_owner` must be exact Python `bool` values.
Strings, integers, and other truthy/falsy types are rejected
(`deny_invalid_policy_context`).

## Approval decision API

`decide_can_approve()` is the **authoritative** public approval decision.
Internal helpers such as `_actor_has_approval_authority` are not policy
boundaries and must not be used as authorization APIs.

## Structured delegation (`ConsentRecord`)

Delegation fields (exact matching only — no free-form scope substrings):

- `subject_id`
- `grantee_id`
- `allowed_uses` (exact `AllowedUse` enum values)
- `granted`
- `granted_by` (must equal `subject_id` for subject-issued delegation)
- `timestamp` (valid ISO date or full timestamp; impossible clock times and
  offsets fail closed)
- `revoked` / `revoked_at` (`revoked_at` required and valid when revoked;
  must be empty when not revoked)
- `granted` and `revoked` must be exact Python `bool` values
  (`invalid_consent_boolean` otherwise)

Rules:

- Missing consent denies delegated use
- Revoked consent denies delegated use
- `actor_id` must exactly equal `grantee_id`
- Requested use must exactly appear in `allowed_uses`
- Consent self-issued by a delegate (`granted_by != subject_id`) is invalid
- Invalid `timestamp` or `revoked_at` fails closed
  (`invalid_consent_timestamp` / `invalid_consent_revoked_at`)

## Permission boundaries (never interchangeable)

| Permission | Authorizes |
|------------|------------|
| `OWNER_ASSISTANCE` | Assistance use only |
| `MODEL_PROMPT` | Prompt insertion only |
| `RECORD_APPROVAL` | Record approval only |

A consent record must include the **exact** requested permission. Assistance or
prompt consent never authorizes approval. Approval consent never authorizes
assistance or prompt use by itself.

Subject approval of their own valid DRAFT record may occur without a prior
delegation record. Delegated approval always requires `RECORD_APPROVAL` in
`allowed_uses`. Delegated access for other uses always requires a valid consent
record naming that exact use.

## Co-founder boundary

| Subject | Who may approve COFOUNDER_PRIVATE facts |
|---------|------------------------------------------|
| Samson Sibona Njaji | Samson (subject), or an exact authenticated delegate with valid `RECORD_APPROVAL` consent |
| James Ndodana Njaji | James (subject), or an exact authenticated delegate with valid `RECORD_APPROVAL` consent |

Samson's approval alone does **not** authorize James's private data.
James's approval alone does **not** authorize Samson's private data.

## Consent states

- Granted
- Revoked
- Missing (treated as not granted for delegated private access)

## Revocation effects

When consent or approval is revoked:

- Public use is denied
- Prompt / embedding / logging / training remain denied for private and secret classes
- `FORGET_DELETE` or an explicit deletion workflow may be required for derived caches
- Prior APPROVED status does not survive revocation
- `approval_status=REVOKED` or `revocation_status=revoked` requires a deletion workflow signal

## Training and fine-tuning

No personal information may be used for training or fine-tuning without a
**separate explicit authorization record**. `TRAINING_DATASET` is **denied** by
default.
