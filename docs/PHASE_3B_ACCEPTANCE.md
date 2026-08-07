# Phase 3B Acceptance Record

**Status:** Accepted  
**Acceptance date:** 2026-08-07  
**Accepted evidence baseline:** `1e1237e1a635dda52a0868a080a84623c74950ec`  
**Closeout branch:** `feat/phase-3b-closeout`  

Phase 3B is accepted as the first **real optional local open-weight model and
registry-bound runtime baseline** for SIONA Core.

This acceptance does **not** constitute production certification, automatic
model startup, tool authority, or a SIONA-native trained foundation model.

---

## Scope accepted

- Pinned portable local runtime: llama.cpp b9968
- Pinned open-weight baseline: `Qwen3-1.7B-Q4_K_M`
- Artifact provenance and checksum verification
- `openai_chat` local transport path behind `ModelGateway`
- Governed prompt/context bridge
- Approved public identity registry with explicit retrieval only
- Governed response guard and deterministic containment
- Controlled real-Qwen identity and guarded-path evaluation
- Gate E breadth evaluation
- Conservative canonical model registry
- Exact `(provider_id, model_id)` registry binding
- Controlled State C registry-bound real-runtime verification
- Runtime shutdown and deterministic fallback after real-model execution
- Offline evidence-integrity recomputation for State C

---

## Key evidence chain

| Evidence | Accepted result |
|---|---|
| EXP-3B-005 | Real local provider text path validated; fallback verified after shutdown |
| EXP-3B-006 | Governed prompt-context bridge validated |
| EXP-3B-007 | Approved public identity registry established with explicit retrieval |
| EXP-3B-008 | Controlled real-Qwen identity campaign recorded; acceptance not met, leading to response hardening |
| EXP-3B-009 | Governed identity response guard implemented and offline validated |
| EXP-3B-010 | 21/21 final guarded responses passed; native structured JSON remained unverified |
| EXP-3B-011 | Gate E breadth recorded; governed safety 8/8; required runtime checks recorded; streaming unsupported on pinned baseline; native JSON not verified |
| EXP-3B-012 | Model-registry activation review passed with conservative exact binding |
| EXP-3B-013 | `STATE_C_VERIFIED`: canonical registry → exact entry → real LocalOpenWeightProvider → loopback llama.cpp/Qwen → bounded real responses → shutdown |

State C evidence is independently recomputed by the offline regression suite
rather than trusted only from the stored decision label.

---

## Accepted architecture

The accepted Phase 3B architecture is:

```text
SIONA LanguageEngine / governed runtime
        ↓
ModelGateway
        ↓
canonical config/model_registry.json
        ↓
exact approved provider/model binding
        ↓
LocalOpenWeightProvider
        ↓
loopback llama.cpp b9968
        ↓
Qwen3-1.7B-Q4_K_M
```

The external model remains optional and replaceable. SIONA remains the authority
for governance, memory/context selection, policy, permissions, response
validation, fallback and tool authority.

---

## Accepted capability matrix

| Capability | Accepted value | Evidence status |
|---|---:|---|
| chat | `true` | Conservatively verified at tested context |
| context window | `4096` | Locally tested baseline |
| tools | `false` | Disabled; no model tool authority |
| structured_json | `false` | Native capability `NOT_VERIFIED` |
| streaming | `false` | `UNSUPPORTED_ON_PINNED_BASELINE` |
| multimodal | `false` | Unverified/disabled |
| siona_native | `false` | External replaceable weights |

The six retained Gate E JSON outputs passed exact parsing/schema validation, but
that is recorded separately and is **not** treated as proof of native-provider
JSON capability.

---

## Runtime steady state

State C does not mean automatic or permanent startup.

At Phase 3B closeout:

- Qwen runtime is stopped
- llama.cpp is stopped
- port 8080 is closed
- no automatic restart is approved
- no machine-wide persistent model environment is approved
- deterministic fallback remains available
- hosted CI remains model-free

---

## Explicit non-claims and deferred work

Phase 3B acceptance does **not** claim or authorize:

- Production-security certification
- Automatic/permanent local-model startup
- Remote model exposure
- Native structured JSON support
- Streaming support on the pinned baseline
- Model tool execution
- Multimodal capability
- LoRA/QLoRA/PEFT training
- Any trained SIONA adapter
- Embedding training or model-weight modification
- A SIONA-native foundation model
- A final permanent runtime or model family
- Phase 4 execution

Broader adversarial/security hardening beyond the recorded Gate E catalogue is
future production-certification work and does not invalidate this conservative
Phase 3B architecture acceptance.

---

## ADR decision

ADR 0003 — First local model strategy is **Accepted (Phase 3B)**.

The acceptance is intentionally conservative: unsupported or unverified optional
capabilities remain disabled rather than being promoted to make the phase appear
more complete.

---

## Phase decision

**Phase 3B is COMPLETE.**

Because Phase 3A was already accepted and Phase 3B is now accepted, **Phase 3 is
COMPLETE** for its defined local-model/evaluation scope.

Phase 4 remains **NOT STARTED**. Phase 3 completion makes Phase 4 eligible for a
separate planning/authorization decision; it does not start Phase 4
automatically.

---

## Related documents

- [PHASE_STATUS.md](PHASE_STATUS.md)
- [PHASE_3_ENGINEERING_SPEC.md](PHASE_3_ENGINEERING_SPEC.md)
- [SIONA_STATE_C_REGISTRY_BOUND_RUNTIME_VERIFICATION.md](SIONA_STATE_C_REGISTRY_BOUND_RUNTIME_VERIFICATION.md)
- [SIONA_MODEL_REGISTRY_ACTIVATION_REVIEW.md](SIONA_MODEL_REGISTRY_ACTIVATION_REVIEW.md)
- [SIONA_GATE_E_BREADTH_EVALUATION.md](SIONA_GATE_E_BREADTH_EVALUATION.md)
- [adr/0003-first-local-model-strategy.md](adr/0003-first-local-model-strategy.md)
