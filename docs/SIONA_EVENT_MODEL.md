# SIONA Event Model

## CognitiveEvent

Canonical fields:

| Field | Purpose |
|-------|---------|
| `event_id` | Unique id |
| `event_type` | Typed name (e.g. `input.text`, `sensor.imu`, `world.observation`) |
| `source` | Provenance |
| `timestamp` | Wall clock |
| `monotonic_timestamp` | **Local receipt time only** — not portable across processes/machines |
| `payload` | Bounded JSON-safe mapping |
| `priority` | `BACKGROUND` … `CRITICAL` |
| `confidence` | 0..1 |
| `trace_id` / `correlation_id` | Distributed-trace friendly |
| `tenant_id` / `session_id` | Multi-tenant / session scope |
| `privacy_class` | public / internal / personal / sensitive / owner_only |
| `ttl_ms` | Optional local TTL convenience |
| `expires_at` | **Portable** wall-clock expiry (preferred across transport) |
| `requires_attention` | Attention hint |
| `metadata` | Bounded extras |

Payload and metadata are size-bounded. Serialization is deterministic
(`json.dumps(..., sort_keys=True)`).

On `from_dict` reconstruction, `expires_at` (or `ttl_ms` + `timestamp`) preserves
TTL across transport. `monotonic_timestamp` is always refreshed to local receipt
time and must not be treated as a portable clock.

## AsyncEventBus

In-process asyncio bus (`ssn.cognition.event_bus.AsyncEventBus`):

- publish / subscribe with type filters:
  - `"sensor.imu"` exact match only
  - `"sensor.*"` prefix match
  - lists apply the same per-element rules
  - regex / predicate unchanged
- priority dequeue
- bounded queues with priority-aware backpressure:
  - admit when capacity available
  - when full, evict oldest-at-lowest-priority **only if** incoming priority is strictly higher
  - otherwise reject the incoming event
- metrics: `incoming_rejected`, `queued_evicted`, `expired_rejected`
- `dispatch_inline` for request/response paths (no queue residue)
- handler timeouts + failure isolation
- optional dead-letter recording
- graceful shutdown

No Kafka / RabbitMQ in this phase. A transport adapter can wrap the same
`CognitiveEvent` contract later.

## Example event types (extensible)

- `input.text`, `input.speech`
- `sensor.*` (camera, audio, IMU, touch, …)
- `tool.result`
- `memory.retrieval`, `memory.proposal`
- `world.observation`, `world_update`
- `embodiment.observation`
- `timer`, `attention.trigger`

## Wiring

`SSNRuntimeBuilder` attaches a `CognitiveRuntime` (bus + workspace + gateways)
alongside the existing Orchestrator. The Front Door chat path remains
request/response via Orchestrator; the event path is additive.
