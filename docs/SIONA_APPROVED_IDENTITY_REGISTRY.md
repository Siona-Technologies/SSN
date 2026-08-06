# SIONA Approved Identity Registry

**Status:** IMPLEMENTED — explicit governed retrieval only  
**Experiment:** EXP-3B-007  
**Approval record:** 2026-08-06 (`#approval-record-2026-08-06`)

## Purpose

Provide SIONA’s first minimal owner-approved public identity registry: three
approved public facts that may be **explicitly selected** and passed through
the merged governed prompt-context bridge (`GovernedContextInput`).

This is approved identity data and request-time context. It is **not** model
training, fine-tuning, embeddings, website ingestion, automatic runtime memory,
or model registry activation.

## Owner approval (2026-08-06)

Owner: Samson Sibona Njaji (`person:samson-sibona-njaji`)  
Approval timestamp: `2026-08-06T08:20:00Z`  
Review date: `2027-08-06`  
Revocation: set `revocation_status` to `revoked` in a future registry revision
(subject to owner re-approval workflow; not implemented in this loader).

## Approved records (exact three)

| Subject ID | Subject | Classification |
|------------|---------|----------------|
| `company:siona-technologies` | SIONA Technologies | `PUBLIC_COMPANY` |
| `product:siona` | SIONA | `PUBLIC_COMPANY` |
| `person:samson-sibona-njaji` | Samson Sibona Njaji | `PUBLIC_PROFESSIONAL` |

### Exact approved statements

**SIONA Technologies:**

> SIONA Technologies is an African-founded technology company developing
> software, intelligent systems and digital infrastructure.

**SIONA:**

> SIONA is the unified intelligence engine and platform developed by SIONA
> Technologies.

**Samson Sibona Njaji:**

> Samson Sibona Njaji is a Kenyan software engineer and technology entrepreneur,
> a co-founder of SIONA Technologies, and is involved in the design and
> development of SIONA.

## Allowed uses (each record)

- `PUBLIC_RESPONSE`
- `MODEL_PROMPT`
- `RETRIEVAL`

`PUBLIC_WEBSITE` is **not** approved in this batch. Website publication requires
a separate approval path.

## Prohibited uses (each record)

- `TRAINING_DATASET` (required in `prohibited_uses`)

## Personal contact boundary

`personal_email`, `personal_phone`, and `personal_address` are fixed exclusion
markers (`excluded`). No emails, phones, or addresses are stored in the registry.

This batch does **not** include James Ndodana Njaji, Griff, executive titles,
education details, or website-derived facts.

## Registry file

Path: `config/governance/approved_identity_records.json`  
Schema version: `1`  
Loader: `ssn/governance/identity_registry.py`

Hard limits:

- maximum file size: 64 KiB (checked before JSON parse)
- maximum records in file: 16
- active approved records: exactly 3
- maximum selection subject IDs per call: 16

## Strict loader behaviour

- local JSON only; no network or URL following
- independent canonical manifest in `ssn/governance/identity_registry.py`
  pins every approved field; manifest entries and mapping are runtime immutable
  (`MappingProxyType`); unauthorized JSON edits fail atomically
- JSON duplicate object keys rejected at every object level (`object_pairs_hook`);
  diagnostics name the duplicate key only (no duplicated value)
- `notes` may be absent or exactly empty (`""`); JSON `null` and other types rejected
- file size checked via `stat` before bounded binary read (max 64 KiB + 1)
- atomic failure — any invalid record rejects the entire load
- intended and prohibited uses must match exact approved sets (no extras,
  no duplicates, no missing entries)
- deterministic ordering by `subject_id`
- duplicate subject IDs or statements rejected
- only `PUBLIC_COMPANY` and `PUBLIC_PROFESSIONAL` classifications
- only `APPROVED` status; draft, rejected, revoked, and expired records rejected
- `approved_by` must be exactly `person:samson-sibona-njaji`

## Explicit retrieval only

The registry does **not** inject records into `LanguageEngine`, `FrontDoor`,
`BrainRouter`, `FusionEngine`, `ModelGateway`, memory, world model, prompts,
tools, or HTTP requests.

Trusted callers must:

1. `load_approved_identity_registry()` or use `ApprovedIdentityRegistry` methods
2. `select_by_subject_ids(...)` or `public_response_records(...)`
3. Build `GovernedContextInput(records=selected, policy_context=..., audience=...)`
4. Pass through `GovernedContextAssembler` / `GovernedContextLLMProvider`

The registry does not construct `PolicyContext` or authentication.

## Non-goals

- No model training or fine-tuning
- No LoRA / QLoRA / PEFT adapters
- No embeddings or vector storage in this task
- No GGUF or weight changes
- No model registry activation
- No llama.cpp lifecycle
- No website repository changes
- No automatic model injection

## Status

IMPLEMENTED AND VALIDATED DETERMINISTICALLY; THREE OWNER-APPROVED PUBLIC
IDENTITY RECORDS AVAILABLE THROUGH EXPLICIT GOVERNED RETRIEVAL; NO AUTOMATIC
MODEL INJECTION; NO MODEL TRAINING; NO EMBEDDINGS; NO MODEL REGISTRY
ACTIVATION; REAL LOCAL-MODEL IDENTITY CAMPAIGN NOT STARTED.

Phase 3B remains **in progress**. ADR 0003 remains **Proposed**. Phase 4 is
**not started**.
