# SIONA Phase 5A — Streaming Neuromorphic Readiness (EXP-5-001)

**Status:** Streaming contract/state-machine readiness VERIFIED  
**Decision:** `PHASE5_STREAMING_READINESS_VERIFIED`  
**Date:** 2026-08-08  
**Base main:** `d4e25ce3be08c8d8df37fe68faf301cb0d906cae`  
**ADR 0005:** Proposed  
**Phase 5:** In progress — stateful learned provider implementation not accepted  
**Next blocker:** EXP-5-002 — pure-Python stateful provider + full Phase 4 parity

## Decision

EXP-5-001 freezes the Phase 5A streaming neuromorphic contract before any
stateful learned-provider implementation. The reserved identity
`siona-neuro-streaming-lif-v1` is recorded only. It is not activated, is not
the system default, and is not an accepted implementation.

The accepted Phase 4 artifact remains the sole learned-weight authority:

- path: `artifacts/neuromorphic/phase4b-lif-final-membrane-v1.json`
- SHA-256: `dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc`

This experiment did not retrain the SNN, mutate weights, regenerate the artifact,
start Qwen, wire `AsyncEventBus`, or grant tool/physical authority.

## Frozen streaming step contract

One claimed streaming learned event represents exactly one temporal timestep of
the accepted Phase 4 `20 × 8` binary sequence.

Required envelope:

- modality: `temporal_salience_stream_v1`
- bounded `event_id` (1..128 characters)
- exact feature keys: `stream_id`, `sequence_index`, `channels`
- `stream_id`: non-empty string, max 128 characters
- `sequence_index`: integer `0..19` (booleans rejected)
- `channels`: exactly 8 numeric binary values `{0, 1}`
- NaN, infinity, strings such as `"1"`, and boolean substitutes are rejected
- no silent coercion of malformed values
- no arbitrary-length feature vectors

Explicit stream reset uses the same modality with exact keys
`stream_id` + `lifecycle_op="stream_reset"`. Provider-wide reset is a method, not
an implicit event.

## Lifecycle state machine

States:

`NONEXISTENT → ACTIVE → COMPLETED`

Legal transitions:

| From | Event | To |
|------|-------|----|
| NONEXISTENT | valid step 0 | ACTIVE (create) |
| ACTIVE | valid next step 1..18 | ACTIVE |
| ACTIVE | valid final step 19 | COMPLETED |
| ACTIVE | explicit stream reset | NONEXISTENT (remove) |
| COMPLETED | explicit stream reset | NONEXISTENT (remove) |
| ACTIVE or COMPLETED | idle TTL expiry | NONEXISTENT (that stream only) |
| any resident | provider-wide reset | NONEXISTENT (all removed) |

Rejected with no implicit restart:

- step ≠ 0 against a nonexistent stream
- duplicate sequence index
- skipped sequence index
- backwards / out-of-order index
- any step after COMPLETED
- malformed claimed streaming events
- new stream while at capacity after deterministic expiry cleanup

A completed stream cannot accept extra steps. Reuse of the same `stream_id`
after completion, reset, or expiry requires a new explicit lifecycle starting at
step 0.

## Atomic mutation

A claimed streaming event is fully validated before any learned-stream mutation.
Rejected input must not change membrane state, spike/reset state, cumulative
spike count, next expected index, completion flag, success counters, successful
activity timestamps, learned output, or lifecycle state.

Failure/diagnostic counters may increment so the failed event cannot appear
successfully processed.

## Bounds

| Bound | Value | Rationale |
|-------|-------|-----------|
| Maximum resident learned streams | 256 | Matches Phase 4 `MAX_LEARNED_BATCH_EVENTS` |
| Maximum stream ID length | 128 characters | Matches Phase 4 `MAX_EVENT_ID_CHARS` |
| Channels per step | exactly 8 | Phase 4 window width |
| Steps per stream | exactly 20 | Phase 4 window length |
| Sequence index | 0..19 | Inclusive range |
| Stored raw temporal payload history | 0 | Retain only future LIF computational state |
| Idle TTL | 30000 milliseconds | Longer than `AsyncEventBus` handler timeout (2 s); forbids indefinite residency |

Resident count includes ACTIVE and COMPLETED records until expiry or reset.

## Capacity

When the resident-stream limit is reached:

1. deterministically expire idle streams first;
2. if still full, **FAIL CLOSED**;
3. do not silently evict an active learned stream;
4. do not use LRU eviction of active streams.

## Multi-stream isolation

Interleaved streams are strictly isolated. Processing `A0, B0, A1, B1, …, A19,
B19` must produce the same final learned outputs as processing A and B
independently. No stream may read or mutate another stream's learned state.

## Future EXP-5-002 parity (frozen now, not executed)

Against all 128 accepted frozen Phase 4 test sequences:

- predicted-class agreement: 128/128
- spike-count agreement: 128/128
- maximum absolute logit difference: `<= 1e-12`
- maximum absolute probability difference: `<= 1e-12`

Any later tolerance change requires a separate governed decision before that
acceptance experiment.

## AsyncEventBus

The existing bus was inspected read-only. Integration is deferred to EXP-5-004.
Required future invariants: queue/backpressure preserved; event TTL respected;
provenance preserved; handler failure cannot corrupt stream state; shutdown
clears streaming state safely; no event grants tool or physical authority.

## Authority and non-claims

- tool authority: false
- physical actuation authority: false
- policy authority: false
- memory-mutation authority: false
- training runs: 0
- Qwen runs: 0
- no CUDA/GPU, Loihi/FPGA/silicon, or measured-energy claim
- Phase 5 is not complete
- ADR 0005 remains Proposed

## Evidence

- [config/phase5a_streaming_neuromorphic_contract.json](../config/phase5a_streaming_neuromorphic_contract.json)
- [docs/evidence/EXP-5-001_STREAMING_NEUROMORPHIC_READINESS.json](evidence/EXP-5-001_STREAMING_NEUROMORPHIC_READINESS.json)
