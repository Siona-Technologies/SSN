# SIONA Public Profile Policy

**Status:** Foundation policy  
**Identity:** SIONA is the unified intelligence engine/platform of SIONA Technologies

## What may become public

Only facts classified `PUBLIC_COMPANY` or `PUBLIC_PROFESSIONAL` with:

- `approval_status = APPROVED`
- `revocation_status` not revoked
- review date not expired (invalid dates fail closed)
- the exact requested public use present in intended uses
  (`PUBLIC_WEBSITE` and/or `PUBLIC_RESPONSE` — not interchangeable)
- no prohibited public use
- structurally valid provenance fields

Draft records remain non-public.

## Approved minimal public fact candidates

### SIONA Technologies (company)

Candidate public statement (must remain DRAFT until owner reviews exact wording):

> African-founded technology company developing software, intelligent systems
> and digital infrastructure.

### SIONA (platform)

Approved product identity statement:

> Unified intelligence engine/platform developed by SIONA Technologies.

Prohibited descriptions: chatbot, OpenAI service, external model wrapper.

### Samson Sibona Njaji (co-founder)

Approved **candidate** public facts (remain DRAFT until reviewed):

- Full name: Samson Sibona Njaji
- Kenyan software engineer and technology entrepreneur
- Co-founder of SIONA Technologies
- Studied Bachelor of Science in Software Development at KCA University
- Works in software engineering, full-stack systems, APIs, databases, cloud
  systems and applied AI/ML
- Involved in the design and development of SIONA

**Excluded:** personal email, personal phone, home address, national ID/passport,
banking information, university registration numbers, private family information,
private ChatGPT conversations, private employment applications, private GitHub
repository data.

`personal_email: excluded`

### James Ndodana Njaji (co-founder)

Approved **candidate** public facts (remain DRAFT until reviewed):

- Full name: James Ndodana Njaji
- Engineer and researcher
- Co-founder of SIONA Technologies
- Research interests include intelligent systems and advanced engineering
- Further public academic/professional facts require source review and explicit
  classification

**Excluded:** ChatGPT conversations, emails, university records, research
correspondence, visa records, scholarship information, banking information,
addresses, and any private personal information. Public academic information may
be reviewed later; private information must not be inferred from account access
or conversation history.

No executive titles unless both co-founders explicitly approve later.

## Approved identity registry (EXP-3B-007)

Three owner-approved public records are available in
`config/governance/approved_identity_records.json` for **explicit** selection
via `ApprovedIdentityRegistry` and `GovernedContextInput`. The registry does
not auto-inject into this bridge. See
[SIONA_APPROVED_IDENTITY_REGISTRY.md](SIONA_APPROVED_IDENTITY_REGISTRY.md).

## Non-automatic sources

- Public website content is not automatically trusted or imported
- GitHub profile information is not automatically approved for public use
- Private repositories are excluded by default
- Source provenance must be retained for every fact
