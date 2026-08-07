# Phase 3 Engineering Specification

**Working title:** SIONA Local Model and Evaluation Layer  
**Status:** Phase 3 **completed** — Phase 3A accepted; Phase 3B accepted under ADR 0003 with conservative local-model capabilities  
**Phase 3A:** completed — provider foundation + evaluation scaffold (deterministic/mock only); hosted-CI accepted  
**Phase 3B:** completed — pinned llama.cpp/Qwen baseline installed and verified; `openai_chat` transport validated; governed context/identity/response controls merged; Gate E recorded; conservative model registry binding reviewed; State C registry-bound real-runtime verification passed; ADR 0003 accepted  

This document is the accepted Phase 3 engineering specification. Phase 3A
established the optional provider/evaluation boundary without a real model.
Phase 3B then selected, verified and governed a replaceable real local
open-weight baseline without converting it into a SIONA-native or production
model.

Governing charter: [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md)

---

## Primary objective

Introduce the first **real optional local language-model provider** and a
**reproducible evaluation framework** without:

- Replacing deterministic offline testing
- Requiring a GPU
- Claiming a SIONA-native trained foundation model
- Changing owner-control semantics

This objective is satisfied for the accepted Phase 3 scope.

---

## Delivered scope

1. Local open-weight model provider contract
2. Optional CPU-capable local runtime adapter
3. Model registry and metadata
4. Deterministic fallback
5. Evaluation dataset format
6. Prompt and task fixtures
7. Reproducible evaluation runner
8. Quality and latency evidence
9. Structured-output evaluation with conservative non-verification where provenance was insufficient
10. Tool-proposal/safety evaluation with tool authority kept disabled
11. Provider health and fallback evaluation
12. Experiment-log integration
13. Hardware and environment recording
14. Model provenance and licence recording
15. Governed prompt/context and approved identity integration
16. Governed response hardening
17. Gate E breadth evaluation
18. Exact registry-bound State C real-runtime verification and shutdown

---

## Local model requirements

The accepted Phase 3 implementation:

- Uses an **open-weight** model
- Runs through a user-controlled local runtime
- Remains **optional**
- Does **not** download models during CI
- Preserves deterministic offline CI
- Supports **CPU** execution for the accepted small baseline
- Allows later acceleration experiments without changing the gateway contract
- Remains behind the existing `ModelProvider` / `ModelGateway` abstraction
- Does **not** hard-code one runtime permanently into SIONA Core
- Records model name, version, quantization, source, licence, and checksum
- Does **not** claim the selected open-weight model is a SIONA-native foundation model

Accepted Phase 3B baseline:

- Runtime: llama.cpp b9968
- Model: `Qwen3-1.7B-Q4_K_M`
- Context: 4096
- Steady-state runtime: stopped; no automatic/permanent startup

---

## Evaluation categories

Phase 3 evaluation covered or explicitly classified:

- Response correctness
- Instruction adherence
- Structured JSON compliance
- Tool-call proposal validity / tool authority safety
- Fallback correctness
- Provider timeout handling
- Cancellation handling
- Latency observations
- Determinism where applicable
- Hallucination/unsupported-content containment
- Safety-policy compatibility
- Redaction/governed-context behavior
- No duplicate inference in shadow mode
- Registry binding and runtime provenance

Not every optional capability was positively verified. Phase 3 acceptance uses a
verify-or-disable rule rather than converting unsupported features into success
claims.

---

## Non-objectives (explicit exclusions)

Phase 3 did **not**:

- Train a SIONA foundation model
- Train a real SNN
- Require CUDA
- Deploy a cloud cluster
- Perform production database migration
- Implement the SIBONA interface
- Add IoT control
- Add vehicle control
- Add drone control
- Add robotics or humanoid simulation as executable control
- Add physical actuation
- Change owner-control semantics
- Connect other company products to SIONA Core
- Immediately replace the existing Orchestrator

---

## Acceptance gates

Phase 3A acceptance gates are completed and merged.

Phase 3B acceptance evidence includes:

- Owner selection
- Pre-install environment verification
- Runtime artifact acquisition and local verification
- Model artifact acquisition and local verification
- Portable installation
- CPU-only loopback startup
- Basic transport smoke probe
- Controlled shutdown
- Controlled real SIONA provider text-path validation (EXP-3B-005)
- Governed prompt-context bridge (EXP-3B-006)
- Approved public identity registry (EXP-3B-007)
- Controlled real-Qwen identity campaign (EXP-3B-008)
- Governed identity response hardening (EXP-3B-009)
- Controlled guarded-path real-Qwen retest (EXP-3B-010)
- Gate E breadth evaluation (EXP-3B-011)
- Model-registry activation review (EXP-3B-012)
- State C controlled registry-bound real-runtime verification (EXP-3B-013),
  recorded as `STATE_C_VERIFIED` with runtime shut down afterward
- ADR 0003 acceptance
- Phase 3B acceptance record

### Conservative capability disposition

These are accepted **limitations**, not unresolved Phase 3B gates:

- Native JSON / `structured_json`: evaluated; `NOT_VERIFIED`; disabled in registry
- Streaming: evaluated; `UNSUPPORTED_ON_PINNED_BASELINE`; disabled in registry
- Tools: disabled; no model tool authority
- Multimodal: unverified/disabled
- Bounded text/chat is the only positively verified registry behaviour at the
  tested 4096 context
- Broader adversarial/security follow-on work beyond the Gate E catalogue is
  future production-certification hardening

The six retained Gate E JSON outputs passed exact parsing/schema validation, but
that result remains separate from native-provider JSON capability verification.

### Standing acceptance conditions

Phase 3 acceptance requires and records:

1. Optional local provider runs successfully when explicitly enabled — **passed**
2. Deterministic CI passes **without** model files — **passed**
3. Provider fallback remains correct — **passed**
4. No proprietary API is required — **passed**
5. Evaluation evidence is reproducible/auditable within recorded limits — **passed**
6. Model metadata and licence are recorded — **passed**
7. Existing legacy Front Door behaviour remains compatible — **passed**
8. No owner-control regressions are introduced by Phase 3 — **passed under the recorded baseline/technical-debt treatment**
9. No model directly executes tools — **passed; tools remain false**
10. Phase 4 is **not** started automatically — **preserved**

---

## Capability honesty

Phase 3 uses the Vision Charter taxonomy and keeps separate:

- Implemented and tested
- Implemented as simulation
- Software-ready but hardware-gated
- Designed but not implemented
- Deferred to a named phase

An optional local open-weight provider is **not** a SIONA-native foundation
model. Deterministic CI providers remain the authority for offline green builds.

Accepted registry capabilities for the first baseline remain:

- `chat=true`
- `tools=false`
- `structured_json=false`
- `streaming=false`
- `multimodal=false`
- `context_window=4096`
- `siona_native=false`

---

## Relationship to Phase 2

Phase 2 (`7b92114` accepted implementation gate) remains the stable cognitive
runtime and integration baseline. Phase 3 built **on** that baseline and did not
reopen Phase 2 scope.

---

## Phase 4 boundary

Phase 3 completion does **not** start Phase 4 automatically.

Phase 4 remains **Not Started** until a separate governed planning/authorization
decision establishes its exact scope, gates, data/model-training policy, and any
hardware requirements.

---

## Related documents

- [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md)
- [PHASE_2_ACCEPTANCE.md](PHASE_2_ACCEPTANCE.md)
- [PHASE_3B_ACCEPTANCE.md](PHASE_3B_ACCEPTANCE.md)
- [PHASE_STATUS.md](PHASE_STATUS.md)
- [SIONA_STATE_C_REGISTRY_BOUND_RUNTIME_VERIFICATION.md](SIONA_STATE_C_REGISTRY_BOUND_RUNTIME_VERIFICATION.md)
- [adr/0003-first-local-model-strategy.md](adr/0003-first-local-model-strategy.md)
- [DEFERRED_CAPABILITIES.md](DEFERRED_CAPABILITIES.md)
- [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md)
