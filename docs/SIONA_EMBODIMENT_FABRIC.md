# SIONA Embodiment Fabric

## Principle

> SIONA owns the persistent mind; each physical or digital body provides an
> embodiment adapter.

Transferable mind state (future): identity, approved long-term memory,
preferences, relationships, knowledge, policies, learned task concepts,
high-level skills, self-model history.

Body-local state: joint geometry, motor limits, camera calibration, actuator
drivers, balance controllers, force constraints, body serial numbers, local
emergency systems.

Humanoid motor control is **not** implemented in Phase 1.

## Contracts

- `DeviceDescriptor` — id, type, location, owner/tenant, capabilities, state,
  risk, connectivity, protocol metadata
- `CapabilityDescriptor`
- `SensorObservation`
- `ActionProposal` — capability, target, parameters, reason, confidence, risk,
  required confirmation, trace id, expiry, expected outcome
- `ActionAuthorization` / `ActionResult`
- `EmbodimentState` / `EmbodimentAdapter`

## Mock adapter

`MockEmbodimentAdapter` simulates a lamp and thermostat.

- `propose_action` always returns a non-executing proposal
- `simulate_action` without authorization → rejected
- with authorization → **in-memory mock state only** (`simulated=True`)
- never connects to real doors, vehicles, appliances, motors, or actuators

## Future protocol adapters (boundaries only)

MQTT, Matter, ROS 2, Zenoh, OPC UA, HTTP/WebSocket — listed in
`FUTURE_PROTOCOL_ADAPTERS`. Dependencies are **not** added in this phase.

## Physical safety (future)

A dedicated capability and physical-safety kernel is required before real-world
embodiment. Phase 1 does not change owner authority or law files; it keeps new
paths simulation-only.
