# SIONA Core Vision Charter

**Status:** Governing architectural charter  
**Applies to:** All future SIONA Core phases  
**Owner:** Siona Technologies  

This document is the authoritative vision and architectural governance charter for
SIONA Core. New implementations must preserve this charter unless a formal
Architecture Decision Record (ADR) explicitly amends it.

---

## A. Ownership and identity

SIONA Core is an **independent intelligence platform** developed and owned by
**Siona Technologies**.

SIONA Core is **not** merely a chatbot or application. It is the shared
intelligence foundation from which future digital and physical embodiments may
be built.

Other Siona Technologies products remain independent unless a future integration
decision is explicitly approved. Product integrations are business and
architectural decisions outside the present Core scope and must not be assumed
in Core design.

---

## B. Governing vision

### One brain, many bodies.

The long-term objective is **one intelligence architecture** that can operate
through multiple controlled forms. Those forms are **future embodiments and
interfaces**, not Phase 2 functionality.

Intended future embodiments and interfaces include:

- Conversational interfaces
- Voice assistants
- Desktop systems
- Developer and IDE assistance
- Private computer agents
- IoT environments
- Smart buildings
- Vehicles
- Drones
- Robots
- Humanoids

Principle: **SIONA Core owns the persistent mind; each body is an adapter.**
Embodiments consume Core contracts; they do not fork or reimplement the
intelligence architecture.

---

## C. SIBONA working name

The current working name for the future user-facing assistant embodiment is
**SIBONA**.

Clarifications:

- SIBONA is **not** implemented in Phase 2.
- SIBONA is **not** a separate intelligence core.
- SIBONA would be a **user-facing embodiment powered by SIONA Core**.
- The working name may later undergo formal branding and legal review.
- Existing SIONA Core modules must **not** be renamed to SIBONA.

---

## D. Hybrid intelligence architecture

SIONA Core is intentionally a **hybrid** system. No single layer is the whole
intelligence.

### Intended layers

1. **Hard safety and autonomic kernel** — deterministic constraints, e-stop
   readiness, non-bypassable safety boundaries
2. **Asynchronous SNN reflex and salience layer** — temporal event processing
   and low-latency proposals
3. **Learned skill and vision-language-action layer** — skill modules and future
   VLA adapters (proposals validated before action)
4. **Deliberative multimodal foundation model** — language, reasoning, planning,
   coding, multimodal understanding
5. **World model** — bounded situational state with provenance
6. **Multiple memory systems** — episodic, semantic, preference, and related
   stores behind explicit contracts
7. **Global Cognitive Workspace** — attention, context assembly, and
   tenant/session isolation
8. **Tool and capability framework** — proposals, approvals, and capability
   enforcement
9. **Embodiment and IoT fabric** — adapters for bodies and environments

### Role of SNN / neuromorphic components

Used for:

- Temporal event processing
- Salience
- Novelty
- Anomaly detection
- Attention prioritisation
- Sensor fusion
- Low-latency **reflex proposals**
- Energy-efficient event processing

**SNNs are not the whole intelligence system.**

### Role of foundation models

Used for:

- Language
- Reasoning
- Planning
- Coding
- Tool proposals
- Multimodal understanding
- Deliberative decision support

### Role of deterministic and symbolic systems

Used for:

- Permissions
- Policy
- Verification
- Mathematics
- Rules
- Safety constraints
- Auditability
- Capability enforcement

---

## E. Physical safety principle

Models must **never** directly command unrestricted physical actuators.

- Real devices require a dedicated safety and control layer.
- Physical systems require emergency-stop mechanisms.
- Physical safety checks must remain deterministic where appropriate.
- **Reflex proposals are not actuator commands.**
- Owner permissions do **not** replace physical safety requirements.
- Robotics and humanoid work must begin in **simulation** before physical
  deployment.

---

## F. Independence principle

SIONA should progressively own:

- Architecture
- Runtime
- Model interfaces
- Tokenizer strategy
- Dataset governance
- Training pipeline
- Checkpoints
- Evaluation framework
- Memory
- World model
- Neuromorphic stack
- Tools
- Safety and policy controls
- Compute orchestration

Temporary rented compute or third-party infrastructure may be used, but it must
**not** create permanent architectural dependence.

**Do not claim that SIONA already owns a trained foundation model.** Phase 2
provides interfaces, providers, and governance — not a SIONA-native trained
foundation model.

---

## G. Hardware portability

- Development must continue on the current **CPU-only** laptop.
- GPU work must be **hardware-gated**, not forgotten.
- Providers must remain **replaceable**.
- The architecture must support:
  - Current CPU laptop
  - Future local GPU workstation
  - Temporary rented compute
  - Future multi-GPU infrastructure
- Hardware acquisition must **not** require rewriting SIONA Core.

---

## H. Truthfulness and capability classification

Every capability must be classified as one of:

1. **Implemented and tested**
2. **Implemented as simulation**
3. **Software-ready but hardware-gated**
4. **Designed but not implemented**
5. **Deferred to a named phase**

Never describe:

- Dummy models as trained intelligence
- Deterministic neuromorphic simulations as trained SNNs
- Mock embodiment as physical robotics
- Proposed functionality as completed
- Hardware-gated functionality as operational

---

## I. Owner-control governance

- Existing owner-control semantics are **frozen** during current
  cognitive-runtime development unless a separately approved owner-control phase
  changes them.
- **Trace IDs are not authentication.**
- **Cognitive events are not permission decisions.**
- **Model output is not authorization.**
- Policy and capability systems remain authoritative.

---

## J. Phase discipline

- Every phase requires explicit objectives and non-objectives.
- Every phase must define tests and acceptance criteria.
- No phase may silently start the following phase.
- New implementations must preserve this Vision Charter unless a formal
  architecture decision explicitly amends it.
- Architectural deviations require an **ADR**.
- Hardware-gated work must remain recorded.
- Technical debt must remain visible.

---

## Related documents

- [PHASE_2_ACCEPTANCE.md](PHASE_2_ACCEPTANCE.md) — formal Phase 2 acceptance
- [PHASE_3_ENGINEERING_SPEC.md](PHASE_3_ENGINEERING_SPEC.md) — Phase 3 specification only
- [PHASE_STATUS.md](PHASE_STATUS.md) — current phase board
- [adr/0001-hybrid-runtime-integration.md](adr/0001-hybrid-runtime-integration.md)
