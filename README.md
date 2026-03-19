## SIONA / SSN – Hybrid Cognitive Runtime

SIONA (SSN) is an experimental **hybrid global brain runtime** that combines:
- a pluggable spiking neural network (SNN) engine,
- a bounded world model,
- multi‑modal sensory perception,
- persistent memory + knowledge tools,
- and a policy / security layer

into a single, testable system you can drive from a CLI “front door”.

The goal is to approximate a **tool‑using, world‑aware, human‑like agent** that can perceive, reason, write to memory explicitly, and act through tools while remaining offline‑deterministic by default.

---

## Core Concepts

- **Orchestrator** (`ssn.core.orchestrator`): central coordinator wiring together senses, world model, memory, tools, and policy.
- **SNN Engine** (`SNNEngine` in `ssn.core.snn_engine`): simulated spiking neural network interface that scores anomaly and signal strength. Designed so real SNN backends (e.g. snnTorch, Loihi) can be swapped in later.
- **Language Engine / LLM** (`ssn.core.language_engine`): a facade over pluggable LLM providers that turns text + context into structured replies. The default provider is a local dummy engine; real local/remote models plug in behind the same interface.
- **World Model** (`ssn.world.world_model`): bounded belief state over entities/events, updated via `WorldStateDelta` objects from the perception pipeline.
- **Memory System** (`ssn.memory.*`): explicit proposal → pending → commit workflow for long‑term memory; includes episodic traces, semantic store, preference memory, and tools for safe inspection and approval.
- **Knowledge Store** (`ssn.knowledge.*`): local `knowledge.jsonl` plus tools to promote information from research and search it later.
- **Policy & Security** (`ssn.policy.*`, `ssn.security.*`): system and home “law” YAMLs, sandboxing, vault, and owner verification via master keys and identity helpers.

Everything is wired through a single bootstrap path in `ssn.bootstrap.create_siona`, which registers production‑grade tools (net.*, research.*, memory.*, knowledge.*) into a canonical `ToolRegistry`.

---

## Senses & Perception

The `ssn.senses` package is the **nervous system**:

- **Contracts** (`ssn.senses.contracts`):
  - `SensorEnvelope`: normalized sensory input (type, device/stream, payload, privacy/quality).
  - `PerceptionPacket`: encoder output with features, anomaly score, and confidence.
  - `WorldStateDelta`: small, bounded updates for the world model.
- **Encoders** (`ssn.senses.encoders.*`): modality‑specific encoders that map `SensorEnvelope` → `PerceptionPacket`:
  - `VisionEncoder` – images / frames.
  - `AudioEncoder` – audio chunks.
  - `IMUEncoder` – inertial / motion (vestibular & proprioception‑like).
  - `LiDAREncoder` – depth / range scans.
  - `EventCameraEncoder` – event‑based vision.
- **Encoder Registry** (`EncoderRegistry`): maps `sensor_type` → encoder and is used by the perception hub.
- **Perception Hub** (`PerceptionHub`): pulls events from `SensoryBus`, runs them through encoders and (optionally) the SNN engine, then builds and applies `WorldStateDelta`s via `DeltaBuilder`. It can also write compact trace items into the memory subsystem.

### Human‑like Sensory Modalities

Biological humans have more than just 5 senses. SIONA/SSN organizes them into **macro‑modalities** that can be mapped onto encoders:

1. **Vision** – already covered by `VisionEncoder` (`sensor_type="vision_frame"` / `cctv_frame` / similar).
2. **Audition (hearing)** – covered by `AudioEncoder` (`sensor_type="audio_chunk"`).
3. **Vestibular & Proprioception (balance / body motion)** – approximated by `IMUEncoder` (`sensor_type="imu_sample"`).
4. **Exteroceptive Range / Spatial Sensing** – via `LiDAREncoder` (`sensor_type="lidar_scan"`).
5. **Event‑based Vision** – `EventCameraEncoder` (`sensor_type="event_camera"`).

To move closer to a **full human‑like set**, the system is designed to support additional encoders:

- **Touch / Somatosensory** – e.g., `sensor_type="touch_map"` for pressure/temperature/pain maps.
- **Olfaction (smell)** – e.g., `sensor_type="olfactory_sample"` for chemical sensor arrays.
- **Gustation (taste)** – e.g., `sensor_type="gustatory_sample"`.
- **Interoception (internal body state)** – e.g., `sensor_type="interoceptive_state"` describing heartbeat, breathing, fatigue, etc.

These new modalities can be implemented as additional encoders that follow the existing pattern in `ssn.senses.encoders.*` and are registered in `EncoderRegistry` so the `PerceptionHub` can treat them uniformly.

---

## CLI / Front Door

The main entry point is the CLI in `ssn.runtime.cli`:

- `ssn-cli console` – production‑style REPL that talks to the `FrontDoor` interface.
  - Supports OWNER vs GUEST roles (OWNER requires a master key).
  - Can toggle offline/online, strict mode, tool usage, and research tools at runtime.
  - Streams answers first, then optional notes, citations, and sources.
- Additional subcommands (`chat`, `state`, `memory`, `suggest`, `world`, `sense-tick`, `run-tool`) exercise the same runtime in more targeted ways for debugging and testing.

---

## Language Engine & LLM Providers

SIONA’s language core is intentionally decoupled from any specific model:

- `LanguageEngine` (`ssn.core.language_engine`) exposes a stable API used by `BrainRouter` and `FusionEngine`:
  - `process(text: str, context: dict | None, role: str) -> dict` returning:
    - `reply`: text answer string,
    - `role`: resolved role,
    - `used_context`: whether context was used,
    - `engine`: engine/provider name.
- Internally, `LanguageEngine` delegates to an `LLMProvider` defined in `ssn.core.llm_providers`:
  - `LLMRequest(prompt, role, context)` → `LLMResponse(text, meta)`.
  - Default implementation: `LocalDummyLLMProvider`, which preserves the original Phase 1 behavior in a provider-friendly form.

This matches the V10 LLM strategy:

- **Local-first**: the default provider is local and does not depend on any external API.
- **Swappable backends**:
  - future `LocalLLMProvider` can call a quantized CPU/GPU model (vLLM, TensorRT-LLM, or an in-process PyTorch model),
  - `RemoteLLMProvider` can speak HTTP to a self-hosted inference service,
  - `FutureCustomProvider` can wrap owner-trained/distilled models.
- **Stable brain contracts**: `BrainRouter`, `FusionEngine`, tools, and the FrontDoor never depend on a specific vendor or library—only on `LanguageEngine.process(...)`.

To upgrade to a real LLM later you only need to:

1. Implement a new `LLMProvider` that:
   - accepts an `LLMRequest`,
   - calls your chosen model backend,
   - returns an `LLMResponse(text, meta)` with at least `meta["engine"]` and `meta["used_context"]`.
2. Pass that provider into `LanguageEngine(provider=...)` when wiring the runtime, or change the default provider in `language_engine.py`.
3. Keep the `process(...)` contract stable so the rest of SIONA continues to work unchanged.

All entry points use the same **canonical runtime build** (`SSNRuntimeBuilder.build_default` → `ssn.bootstrap.create_siona`) to avoid configuration drift between dev, CLI, and production.

---

## Environment & Offline / Live Modes

Environment behavior is documented in `ENVIRONMENT.md`. Key principles:

- **Deterministic by default**:
  - `SSN_OFFLINE=1` forces offline behavior.
  - Network research tools (`net.search`, `research.*`) use deterministic mocks in offline mode.
- **Opt‑in live research**:
  - `SSN_LIVE_SEARCH=1` enables live providers (Brave, DDG, Wikipedia).
  - `SSN_LIVE_STRICT=1` disables mock fallback when providers fail (good for validating real network behavior).
- **Secrets**:
  - `SSN_BRAVE_API_KEY` (and any other keys) must never be committed or written into traces or memory.
  - Local development usually uses a `.env` loaded via `SSN_AUTO_DOTENV=1`; CI keeps everything offline and key‑free.
- **State / persistence**:
  - `SSN_STATE_DIR` (default `.ssn_state`) stores proposal queues, commit history, and rate‑limit backing files.
  - `SSN_RATE_LIMIT_PATH` usually lives under `SSN_STATE_DIR`.

This makes it possible to run a fully offline, reproducible agent in CI while still allowing optional live research in local runs.

---

## Memory, Knowledge, and Tools

The system uses **tools** as the primary action interface:

- Network and research tools (`net.*`, `research.*`).
- Memory tools for proposal, commit, and inspection.
- Knowledge tools for promoting researched facts into a local knowledge base and searching it later.
- World tools for reading bounded world state.

Tool registration happens centrally in `ssn.bootstrap.create_siona`, which:

- ensures built‑in tools (like `tools.list`) are available,
- registers the production tool set only once (idempotent),
- and wires compatibility aliases on the orchestrator so older interfaces see a consistent API.

---

## Running Locally

Minimal example (offline‑deterministic console):

```bash
export SSN_OFFLINE=1
python -m ssn.runtime.cli console --role GUEST
```

With live network research (local dev only, using a `.env` you do **not** commit):

```bash
export SSN_AUTO_DOTENV=1
export SSN_OFFLINE=0
export SSN_LIVE_SEARCH=1
python -m ssn.runtime.cli console --role OWNER --strict
```

See `ENVIRONMENT.md` for more detailed guidance on safe configurations.

---

## Adding New Senses

To add a new human‑like sense:

1. Define a new `sensor_type` in `SensorEnvelope` documentation (e.g., `"touch_map"`, `"olfactory_sample"`).
2. Implement an encoder in `ssn.senses.encoders.*` that:
   - Accepts a `SensorEnvelope` payload for that sensor type.
   - Produces a bounded feature dict and anomaly/confidence scores.
   - Returns a validated `PerceptionPacket` via `_packet(...)`.
3. Register the encoder with your `EncoderRegistry` instance so `PerceptionHub` can route `SensorEnvelope`s of that type to it.
4. If appropriate, extend `DeltaBuilder` to translate the new features into `WorldStateDelta` updates.

The existing encoders (`vision`, `audio`, `imu`, `lidar`, `event_camera`) are good minimal templates to follow when you wire up touch, smell, taste, or interoception.

