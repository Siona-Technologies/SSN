# SIONA Private Context Policy

**Status:** Foundation policy

## OWNER_PRIVATE

- Verified owner assistance only
- No public use
- No guest visibility
- No public documentation or logs
- No training by default
- Model prompt insertion only when explicitly intended and otherwise authorized

## COFOUNDER_PRIVATE

- Belongs to the co-founder subject
- Requires that person's explicit consent
- The other co-founder cannot approve by default
- No public use
- No training by default

## COMPANY_CONFIDENTIAL

- Internal authorized use only
- Not for public responses or public websites
- Not for ordinary guest-facing memory

## LEGAL_RESTRICTED

- Legal workflow only
- Never general conversational memory
- Never ordinary embeddings or public logs

## SECRET

Deny:

- Public use
- Owner conversational memory as ordinary facts
- Model prompts
- Embeddings / indexes
- Logging
- Training datasets

Secrets are never ordinary memory.

## FORGET_DELETE

- Deny all use
- Require deletion workflow for active indexes and derived caches
- Revocation may trigger the same deletion path
