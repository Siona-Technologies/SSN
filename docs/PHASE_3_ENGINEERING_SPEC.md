# Phase 3 Engineering Specification

**Working title:** SIONA Local Model and Evaluation Layer  
**Status:** Phase 3 **in progress** — Phase 3A completed and merged (`d6c17d0` → `2e6abb6`, PR #2); Phase 3B first baseline installed and artifact-verified locally; controlled real-provider text path validated (runtime stopped)  
**Phase 3A:** completed — provider foundation + evaluation scaffold (deterministic/mock only); hosted-CI accepted  
**Phase 3B:** in progress — baseline installed/verified locally; limited loopback
inference completed; `openai_chat` transport dialect implemented; controlled
real-provider text-path validation recorded (EXP-3B-005); registry, Gate E
evaluation, broad capability verification and ADR acceptance pending  

This document remains the Phase 3 engineering specification. Phase 3A did **not**
install or download a real model. The Phase 3A final security/isolation gate
hardens redirects, request sanitization, per-test isolation, registry validation,
and declarative hard-timeout evaluations — still without a real model.

Governing charter: [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md)

---

## Primary objective

Introduce the first **real optional local language-model provider** and a
**reproducible evaluation framework** without:

- Replacing deterministic offline testing
- Requiring a GPU
- Claiming a SIONA-native trained foundation model
- Changing owner-control semantics

---

## Intended deliverables

1. Local open-weight model provider contract
2. Optional CPU-capable local runtime adapter
3. Model registry and metadata
4. Deterministic fallback
5. Evaluation dataset format
6. Prompt and task fixtures
7. Reproducible evaluation runner
8. Quality and latency metrics
9. Structured-output evaluation
10. Tool-proposal evaluation
11. Provider health and fallback evaluation
12. Experiment-log integration
13. Hardware and environment recording
14. Model provenance and licence recording

---

## Local model requirements

Future implementation **must**:

- Use an **open-weight** model
- Run locally or through a user-controlled local model service
- Remain **optional**
- **Not** download models during CI
- Preserve deterministic offline CI
- Support **CPU** execution for small models
- Allow later GPU acceleration
- Remain behind the existing `ModelProvider` / model-gateway abstraction
- **Not** hard-code one runtime permanently
- Record model name, version, quantization, source, licence, and checksum
- **Never** claim the selected open-weight model is a SIONA-native foundation
  model

Possible runtimes may be evaluated later. **Do not select or install one in this
closeout task.**

---

## Evaluation categories

The future evaluation harness should measure:

- Response correctness
- Instruction adherence
- Structured JSON compliance
- Tool-call proposal validity
- Fallback correctness
- Provider timeout handling
- Cancellation handling
- Latency
- Memory use
- Token throughput where available
- Determinism where applicable
- Hallucination indicators
- Safety-policy compatibility
- Redaction compliance
- Tenant/session isolation
- No duplicate inference in shadow mode

---

## Non-objectives (explicit exclusions)

Phase 3 must **not**:

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

Phase 3B gates **passed** (local operator evidence, 2026-08-05):

- Owner selection
- Pre-install environment verification
- Runtime artifact acquisition and local verification
- Model artifact acquisition and local verification
- Portable installation
- Initial CPU-only loopback startup
- Basic transport smoke probe
- Normal non-force shutdown
- Controlled real SIONA provider text-path validation (EXP-3B-005):
  exact model-ID verification; LanguageEngine → local provider → llama.cpp;
  deterministic fallback after shutdown

Phase 3B gates remaining **open**:

- Model registry activation
- Security validation campaign with real runtime
- Structured-output capability verification
- Timeout/cancellation validation
- Streaming validation
- Behavioral / Gate E evaluation suite
- Capability verification (beyond observed text path)
- ADR acceptance
- Phase 3B completion

Additional standing gates:

Phase 3 may be accepted only when:

1. Optional local provider runs successfully when explicitly enabled
2. Deterministic CI still passes **without** model files
3. Provider fallback remains correct
4. No proprietary API is required
5. Evaluation reports are reproducible
6. Model metadata and licence are recorded
7. Existing legacy Front Door behaviour remains compatible
8. No owner-control regressions (owner-adjacent baseline reported separately)
9. No model directly executes tools
10. Phase 4 is **not** started automatically

---

## Capability honesty

Classify Phase 3 work using the Vision Charter taxonomy:

- Implemented and tested
- Implemented as simulation
- Software-ready but hardware-gated
- Designed but not implemented
- Deferred to a named phase

An optional local open-weight provider is **not** a SIONA-native foundation
model. Deterministic CI providers remain the authority for offline green builds.

---

## Relationship to Phase 2

Phase 2 (`7b92114` accepted implementation gate) remains the stable cognitive
runtime and integration baseline. Phase 3 builds **on** that baseline; it does
not reopen Phase 2 scope or silently begin later phases.

---

## Related documents

- [SIONA_VISION_CHARTER.md](SIONA_VISION_CHARTER.md)
- [PHASE_2_ACCEPTANCE.md](PHASE_2_ACCEPTANCE.md)
- [PHASE_STATUS.md](PHASE_STATUS.md)
- [DEFERRED_CAPABILITIES.md](DEFERRED_CAPABILITIES.md)
- [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md)
