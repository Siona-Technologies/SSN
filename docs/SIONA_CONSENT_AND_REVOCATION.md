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

## Structured delegation (`ConsentRecord`)

Delegation fields (exact matching only — no free-form scope substrings):

- `subject_id`
- `grantee_id`
- `allowed_uses` (exact `AllowedUse` enum values)
- `granted`
- `granted_by` (must equal `subject_id` for subject-issued delegation)
- `timestamp`
- `revoked` / `revoked_at`

Rules:

- Missing consent denies delegated use
- Revoked consent denies delegated use
- `actor_id` must exactly equal `grantee_id`
- Requested use must exactly appear in `allowed_uses`
- Consent self-issued by a delegate (`granted_by != subject_id`) is invalid

Subject approval of their own record may occur without a prior delegation record.
Delegated access always requires a valid consent record.

## Co-founder boundary

| Subject | Who may approve COFOUNDER_PRIVATE facts |
|---------|------------------------------------------|
| Samson Sibona Njaji | Samson (subject), or an exact authenticated delegate with valid consent |
| James Ndodana Njaji | James (subject), or an exact authenticated delegate with valid consent |

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
