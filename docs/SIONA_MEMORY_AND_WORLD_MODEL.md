# SIONA Memory and World Model

## Memory boundaries (Phase 1)

Existing stores remain the development backends:

- Semantic, episodic, preference/profile, trace
- Proposal store (`memory.propose` → pending → OWNER `memory.commit`)

New scaffolding (`ssn.cognition.memory`):

- `MemoryRecord` with provenance, confidence, freshness, timestamps, source,
  tenant/session, retention, approval, versioning, supersession/conflicts
- Kinds: working, episodic, semantic, preference, profile, trace
- Placeholders: procedural, spatial, social, safety_incident, self_model
- `MemoryServiceBoundary.propose()` — **does not auto-commit**

### Future storage

Contracts allow PostgreSQL, vector stores, and object storage later.
No risky database migration in this phase. JSON / JSONL remain default.

## World model boundaries

Existing `WorldModel` (bounded entities/events, atomic JSON persistence) is
preserved.

New scaffolding (`ssn.cognition.world`):

- Entity / relation / observation / prediction views
- Confidence, source, freshness, affordances, uncertainty
- `WorldUpdateProposal` → `WorldModel.apply_update` packet shape
- `WorldEventAdapter` — CognitiveEvent → proposal (apply optional)

### Future transactional backend

Replace the JSON file with a transactional store behind the same
`apply_update` / `snapshot` methods. Event adapters stay unchanged.

## Proposal discipline

Memory and world writes originating from the cognitive loop are **proposals**.
Authoritative commits continue through existing tools and owner/policy gates.
