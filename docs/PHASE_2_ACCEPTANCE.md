# Phase 2 Acceptance Record

**Status:** Accepted  
**Branch:** `feat/siona-runtime-integration-v2`  
**Acceptance date:** 2026-08-05  

Phase 2 is accepted as the stable **cognitive-foundation and runtime-integration
baseline**. It does **not** yet constitute a trained SIONA-native intelligence
model.

---

## Scope delivered

- Cognitive event fabric
- Priority-aware backpressure
- Tenant/session workspace isolation
- Model gateway abstraction
- Structured JSON validation
- Neuromorphic provider abstraction
- Memory and world boundaries
- Embodiment contracts
- Runtime integration modes (`legacy`, `shadow`, `cognitive_experimental`)
- Legacy Front Door compatibility (exact pre-Phase-2 chat response keys)
- Shadow observation without duplicate model inference
- Cognitive experimental proposal mode (non-authoritative)
- Runtime event bridges (chat, routing, model, tools, perception, memory, world)
- Trace continuity and isolation (no per-request state on shared runtime deps)
- Safe async observation task lifecycle (`drain` / `shutdown`)
- Governance documentation (roadmap, deferred capabilities, hardware, debt, ADR)

---

## Accepted commits

| Milestone | Commit |
|-----------|--------|
| Phase 1 hardening | `183fa70` |
| Phase 2 initial implementation / governance tip before hardening close | `0cf3372` |
| Phase 2 hardening | `81aada0` |
| Phase 2 trace-isolation gate (**accepted implementation gate**) | `7b92114` |
| Phase 2 status record before closeout | `5f0d3ae` |

---

## Test evidence

| Suite | Result |
|-------|--------|
| Offline CI (`SSN_OFFLINE=1 python scripts/run_tests.py`) | **199 passed, 4 skipped** |
| HTTP smoke (`scripts/smoke_http.py`) | Passed |
| CLI smoke (`ssn.runtime.cli chat --role GUEST`) | Passed |
| Front Door smoke (`scripts/smoke_frontdoor.py`) | Passed |

---

## Owner-adjacent baseline

Owner-control semantics were **not** modified to clear these suites. Results were
reconciled in clean git worktrees with the same Python environment.

| Reference | Result |
|-----------|--------|
| Baseline `0cf3372` | **1 failure + 3 errors** (of 8) |
| Accepted Phase 2 gate (`7b92114` / clean compare) | **1 failure + 3 errors** (of 8) |
| New regressions | **None** |

### Exact affected test IDs

**Errors:**

1. `ssn.tests.test_phase43_owner_handoff_and_redaction.TestPhase43OwnerHandoffAndRedaction.test_master_key_passed_as_argument_and_context_sanitized`  
   — `KeyError: 'master_key'`
2. `ssn.tests.test_phase43_owner_handoff_and_redaction.TestPhase43OwnerHandoffAndRedaction.test_no_master_key_results_in_none_passed`  
   — `KeyError: 'master_key'`
3. `ssn.tests.test_phase43_cli_smoke.TestPhase43CliSmoke.test_cli_chat_smoke`  
   — `UnicodeEncodeError` (`\u2192` / cp1252)

**Failure:**

4. `ssn.tests.test_phase66_identity_enrollment.TestPhase66IdentityEnrollment.test_guest_blocked`  
   — `AssertionError: False is not true`

These remain **technical debt**. They were **not** fixed by changing owner
semantics, identity verification, master-key handling, law files, or
OWNER/GUEST permissions.

---

## Capability classification

### Real and tested

- Event bus with priority queues, filters, and backpressure metrics
- Workspace registry with tenant/session isolation
- Model gateway with timeouts, fallback, and strict structured-JSON validation
- Runtime modes and IntegrationFacade observation bridges
- Exact legacy Front Door response shape
- Single canonical `routing.selected` with shared TraceContext
- Trace isolation from shared runtime deps
- Async observation drain/shutdown semantics
- Offline CI and smoke suites listed above

### Simulated

- Dummy / deterministic language providers
- Deterministic neuromorphic salience (CPU reference provider)
- Mock embodiment adapters
- Shadow neuromorphic reflex **proposals** (non-executing)

### Hardware-gated

- CUDA SNN training
- Large local LLM acceleration
- Isaac Sim / event cameras
- Real IoT, vehicles, drones, robots, humanoids

### Deferred

- Production database migrations
- Training a SIONA-native foundation model
- Training a real SNN
- User-facing assistant embodiment (SIBONA)
- Product integrations with other Siona Technologies products
- See `DEFERRED_CAPABILITIES.md` and `TECHNICAL_DEBT_REGISTER.md`

---

## Acceptance statement

**Phase 2 is accepted as the stable cognitive-foundation and runtime-integration
baseline. It does not yet constitute a trained SIONA-native intelligence model.**

Phase 3 is **specified** in `PHASE_3_ENGINEERING_SPEC.md` and remains
**not started**.

---

## Related documents

- [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md)
- [PHASE_3_ENGINEERING_SPEC.md](PHASE_3_ENGINEERING_SPEC.md)
- [PHASE_STATUS.md](PHASE_STATUS.md)
