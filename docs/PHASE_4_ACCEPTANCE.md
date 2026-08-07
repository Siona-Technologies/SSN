# Phase 4 Acceptance Record

**Status:** Accepted  
**Acceptance date:** 2026-08-07  
**Accepted evidence baseline:** `05de2b04279a72ece4834a984461a505de1188b3`  
**Scope:** Learned Neuromorphic Backend & Evaluation

## Decision

Phase 4 is accepted as complete for its defined learned-neuromorphic software
scope.

SIONA now has its first genuine learned SNN component, trained under governed
conditions, integrated behind the existing neuromorphic-provider contract,
verified against its snnTorch reference, and hardened through a separate
breadth/safety gate.

## Accepted evidence chain

- **EXP-4-001** — readiness/task/data/backend governance defined.
- **EXP-4-003** — `FIRST_CPU_SNN_TRAINING_VERIFIED`.
- **EXP-4-004** — `LEARNED_SNN_PROVIDER_PARITY_VERIFIED`.
- **EXP-4-005** — `PHASE4_LEARNED_SNN_BREADTH_SAFETY_VERIFIED`.

## Accepted learned artifact

- task: `phase4a-temporal-salience-v1`
- architecture: `phase4b-lif-final-membrane-v1`
- provider: `siona-neuro-learned-lif-v1`
- canonical artifact:
  `artifacts/neuromorphic/phase4b-lif-final-membrane-v1.json`
- SHA-256:
  `dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc`

## Verified boundaries

- CPU software SNN only;
- deterministic/reference provider preserved as default/fallback;
- pure-Python learned runtime;
- no torch/snnTorch/numpy runtime dependency;
- no Qwen calls or registry capability changes;
- no tools;
- no learned reflex proposals;
- no physical authority;
- no private/user/company/website training data;
- no CUDA/GPU claim;
- no neuromorphic-silicon claim;
- no production-security certification.

## Governance disposition

- ADR 0004: **Accepted (Phase 4)**
- Phase 4: **Complete**
- Phase 5: **Not Started**

Phase 4 completion does not authorize Phase 5 implementation. The next phase
must begin with a separate governed planning decision that chooses one bounded
objective and defines its evidence and safety gates before implementation.
