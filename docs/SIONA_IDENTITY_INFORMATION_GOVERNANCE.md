# SIONA Identity and Information Governance

**Status:** Foundation (documentation + deterministic policy only)  
**Accepted main baseline:** `8c2c115476525e128efa73183c50e1aca23dc4f0`  
**Not:** runtime memory ingestion, model training, registry activation, or website modification

## Authoritative identity definitions

| Entity | Definition |
|--------|------------|
| **SIONA Technologies** | The company |
| **SIONA** | The complete unified intelligence engine/platform developed by SIONA Technologies |
| **Samson Sibona Njaji** | Co-founder of SIONA Technologies |
| **James Ndodana Njaji** | Co-founder of SIONA Technologies |

SIONA is **not** an assistant, chatbot, or external model wrapper. External models
remain **replaceable reasoning components** behind `ModelGateway`.

Do **not** assign CEO, CTO, CRO, COO, or other executive titles unless both
co-founders explicitly approve them later.

Future employees, collaborators, customers, and organizations must be recorded
under the same classification, consent, and approval rules.

## Purpose

Define what SIONA may know about the company, the platform, co-founders, and
future subjects — and under which information class, approval, and use
constraints.

This foundation does **not**:

- Ingest private personal data into runtime memory
- Train or fine-tune any model
- Start llama.cpp or load local weights
- Activate the model registry
- Scrape or modify public websites

## Core rules

1. **Deny by default** when classification is missing.
2. Public visibility requires **explicit approval**.
3. Personal information must be **purpose-limited**.
4. **Subject consent** is required for private information.
5. One co-founder **cannot** authorize another co-founder's private information.
6. **Secrets are never ordinary memory.**
7. Public website content is **not** automatically trusted or imported.
8. GitHub profile information is **not** automatically approved for public use.
9. Private repositories are **excluded by default**.
10. **Source provenance** must be retained.
11. Every fact must record: subject, classification, source type, source
    reference, approval status, approved by, approval timestamp, intended uses,
    prohibited uses, review date, revocation status.
12. **Revocation overrides** prior approval.
13. Derived summaries inherit the **strictest** classification of their inputs.
14. Model output **cannot** change a fact's classification.
15. Model output **cannot** grant consent or approval.
16. Owner authentication does **not** override another person's consent rights.
17. No personal information may be used for **training or fine-tuning** without a
    separate explicit authorization record. Training use defaults to **denied**.

## Related documents

- [SIONA_INFORMATION_CLASSIFICATION.md](SIONA_INFORMATION_CLASSIFICATION.md)
- [SIONA_CONSENT_AND_REVOCATION.md](SIONA_CONSENT_AND_REVOCATION.md)
- [SIONA_PUBLIC_PROFILE_POLICY.md](SIONA_PUBLIC_PROFILE_POLICY.md)
- [SIONA_PRIVATE_CONTEXT_POLICY.md](SIONA_PRIVATE_CONTEXT_POLICY.md)
- [SIONA_WEBSITE_CONTENT_AUDIT_PLAN.md](SIONA_WEBSITE_CONTENT_AUDIT_PLAN.md)

## Implementation

Deterministic package: `ssn.governance`

Example (non-active) seeds:
`examples/governance/public_identity_records.example.json`

## Governance status relative to Phase 3B

- Phase 3B remains **in progress**
- Phase 4 remains **not started**
- Model registry remains **inactive**
- ADR 0003 remains **Proposed**
