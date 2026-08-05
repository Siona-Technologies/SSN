# SIONA Information Classification

**Status:** Foundation policy  
**Rule:** Deny by default when classification is missing.

## Mandatory information classes

### 1. PUBLIC_COMPANY

- Approved company facts
- Approved product descriptions
- Public websites
- Approved public contacts
- Public press and announcements

Public use requires `approval_status=APPROVED` and no revocation/expiry.

### 2. PUBLIC_PROFESSIONAL

- Approved biographies
- Approved education and experience
- Approved public projects
- Published research and public achievements

Draft biographies are **not** public until explicitly approved.

### 3. OWNER_PRIVATE

- Private context usable only for the verified owner
- Never exposed to guests or public interfaces
- Never written to public documentation or logs
- No training by default

### 4. COFOUNDER_PRIVATE

- Private context belonging to another co-founder
- Requires that person's explicit consent
- Samson's approval alone does **not** authorize James's private data (and the reverse)

### 5. COMPANY_CONFIDENTIAL

- Internal plans
- Unreleased products
- Commercial strategy
- Private agreements
- Internal team and financial information

Internal authorized use only.

### 6. LEGAL_RESTRICTED

- Registration records
- Shareholding records
- Contracts
- Signatures
- Government-issued documents

Access only through specifically authorized legal workflows. Never general
conversational memory.

### 7. SECRET

- Passwords, API keys, authentication tokens, recovery codes
- Private keys, session cookies, banking credentials, encryption secrets

SECRET data must **never** enter conversational memory, model prompts,
embeddings, logs, datasets, or public files.

### 8. FORGET_DELETE

- Incorrect or outdated facts
- Revoked consent
- Information the subject requests to remove
- Data that must be deleted from active indexes and derived caches

Deny all use and require a deletion workflow.

## Classification inheritance

Derived summaries inherit the **strictest** classification among inputs.
Missing classification is treated as fail-closed (stricter than all known
classes for policy purposes).

Model output cannot reclassify a fact to a weaker class.

## Privacy exclusions

Personal email addresses, personal phone numbers, and home addresses must not
appear in repository data, public profile files, examples, fixtures, logs,
tests, or documentation.

Represent exclusions as:

```text
personal_email: excluded
personal_phone: excluded
personal_address: excluded
```

Do not write actual personal contact values into the repository.
