# Technical Debt Register

| ID | Description | Risk | Current mitigation | Planned phase | Acceptance criteria |
|----|-------------|------|--------------------|---------------|---------------------|
| TD-LLM-001 | Dummy language provider | Low quality replies | Deterministic offline tests; swap via ModelGateway | Phase 3 | Local optional provider + fallback |
| TD-NEURO-001 | Deterministic simulated neuromorphic provider | Not trained SNN | Clearly labelled simulated | Phase 4 | Real backend behind same protocol |
| TD-NEURO-002 | Legacy random SNNEngine | Non-determinism | New path uses deterministic provider; legacy preserved | Phase 3 | Opt-in facade in offline mode |
| TD-STOR-001 | JSON/JSONL development storage | Scale/consistency | Bounds + atomic writes | Later | Transactional backend behind contracts |
| TD-EMB-001 | Mock embodiment adapter | No real devices | Simulation-only; proposals non-executing | Later | Safety kernel + real adapters |
| TD-TO-001 | Sync provider timeout cannot kill threads | Abandoned work may continue | Bounded pool; documented limitation | Phase 3 | Prefer async providers |
| TD-STREAM-001 | Streaming fallback limitations | Partial streams | Cancel checks between chunks | Phase 3 | Full async streaming |
| TD-EVAL-001 | No real model evaluation | Quality unknown | Deterministic fixtures | Phase 3 | Eval harness for local models |
| TD-SAFE-001 | No physical safety kernel | Critical if hardware attached | No real actuators in Phase 1–2 | Before IoT/robot | Dedicated safety kernel |
| TD-TEST-001 | Pre-existing owner-adjacent test failures | Confusion vs regressions | Documented baseline; not silenced | Parallel | Fix without changing owner semantics |
| TD-HTTP-001 | Development HTTP-server limitations | Not production-hardened | stdlib server for local use | Later | Production ASGI if needed |
