# SIONA Event Model

## CognitiveEvent

Canonical fields:

| Field | Purpose |
|-------|---------|
| `event_id` | Unique id |
| `event_type` | Typed name (e.g. `input.text`, `sensor.imu`, `world.observation`) |
| `source` | Provenance |
| `timestamp` | Wall clock |
| `monotonic_timestamp` | Monotonic clock for TTL / ordering |
| `payload` | Bounded JSON-safe mapping |
| `priority` | `BACKGROUND` … `CRITICAL` |
| `confidence` | 0..1 |
| `trace_id` / `correlation_id` | Distributed-trace friendly |
| `tenant_id` / `session_id` | Multi-tenant / session scope |
| `privacy_class` | public / internal / personal / sensitive / owner_only |
| `ttl_ms` | Optional expiry |
| `requires_attention` | Attention hint |
| `metadata` | Bounded extras |

Payload and metadata are size-bounded. Serialization is deterministic
(`json.dumps(..., sort_keys=True)`).

## AsyncEventBus

In-process asyncio bus (`ssn.cognition.event_bus.AsyncEventBus`):

- publish / subscribe with type filters (exact, prefix `foo.`, list, regex, predicate)
- priority dequeue
- bounded queues + drop/reject backpressure
- handler timeouts + failure isolation
- optional dead-letter recording
- metrics counters
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
