# SIONA Consent and Revocation

**Status:** Foundation policy

## Principles

1. Subject consent is required for private information.
2. One co-founder cannot authorize another co-founder's private information.
3. Owner authentication does not override another person's consent rights.
4. Revocation overrides prior approval.
5. Model output cannot grant consent.
6. Consent records must retain provenance (who granted, when, scope).

## Co-founder boundary

| Subject | Who may approve COFOUNDER_PRIVATE facts |
|---------|------------------------------------------|
| Samson Sibona Njaji | Samson (subject), or an explicitly recorded delegate scoped by Samson |
| James Ndodana Njaji | James (subject), or an explicitly recorded delegate scoped by James |

Samson's approval alone does **not** authorize James's private data.
James's approval alone does **not** authorize Samson's private data.

## Consent states

- Granted
- Revoked
- Missing (treated as not granted for private classes)

## Revocation effects

When consent or approval is revoked:

- Public use is denied
- Prompt / embedding / logging / training remain denied for private and secret classes
- `FORGET_DELETE` or an explicit deletion workflow may be required for derived caches
- Prior APPROVED status does not survive revocation

## Training and fine-tuning

No personal information may be used for training or fine-tuning without a
**separate explicit authorization record**. The default policy decision for
`TRAINING_DATASET` is **denied**.
