# SIONA Private Context Policy

**Status:** Foundation policy (hardened authorization semantics)

## Authentication requirement

Private, confidential, prompt, and approval decisions require a trusted
`PolicyContext` with `actor_authenticated=True`. Spoofed requester IDs are
ignored without authentication.

## OWNER_PRIVATE

Active private use requires **all** of:

- Authenticated actor
- `verified_owner=True`
- `actor_id` exactly equals `record.subject_id`
- `approval_status=APPROVED`
- Record structurally valid and not revoked/expired
- Requested use present in `intended_uses` and not prohibited

DRAFT private records are **not** active private context. A narrow
`decide_draft_review` path may allow the authenticated subject to review their
own DRAFT; it does **not** authorize prompting, retrieval, logging, or normal
assistance.

## COFOUNDER_PRIVATE

Subject access requires:

- `actor_authenticated=True`
- `actor_id` exactly equals `subject_id`
- `approval_status=APPROVED`
- Requested use intended and not prohibited

Delegated access requires an exact, valid `ConsentRecord` (subject-issued,
exact `grantee_id`, exact `allowed_uses`). One co-founder does not gain access
to the other co-founder's private data merely because both are owners.

## COMPANY_CONFIDENTIAL

- Authenticated verified owner **or** exact authorized company approver
- `APPROVED`
- Requested use intended and not prohibited
- Not for public responses or public websites

## LEGAL_RESTRICTED

- Legal workflow only
- Never general conversational memory
- Never ordinary embeddings, prompts, or public logs

## SECRET

**Secrets are never ordinary memory.** Deny public use, ordinary owner
conversational memory, model prompts, embeddings/indexes, logging, and training
datasets. Secrets cannot be approved into ordinary memory.

## FORGET_DELETE

- Deny all use
- Require deletion workflow for active indexes and derived caches
- Revocation may trigger the same deletion path

## Model prompts

`intended_uses` alone is not authorization. MODEL_PROMPT additionally requires
class-specific authentication/approval rules. Always deny MODEL_PROMPT for
SECRET, FORGET_DELETE, and LEGAL_RESTRICTED. Do not permit DRAFT private or
confidential records in model prompts.
