# SIONA Migration Notes — Cognitive Runtime V1

## Compatibility guarantees

| Surface | Status |
|---------|--------|
| `create_siona()` | Unchanged tool registration / Orchestrator construction |
| `SSNRuntimeBuilder.build_default()` | Adds optional `cognitive_runtime` field + deps entry |
| CLI (`siona-cli` / `python -m ssn.runtime.cli`) | Unchanged |
| HTTP (`/v1/health`, `/v1/chat`, `/v1/tool/run`) | Unchanged |
| `LanguageEngine.process(...)` | Unchanged return shape; default provider still dummy |
| `LLMProvider` / `LocalDummyLLMProvider` / `HttpLLMProvider` | Preserved |
| `SNNEngine` | Preserved; new code uses adapters / deterministic provider |
| Memory Hub / proposal→commit | Preserved |
| WorldModel JSON persistence | Preserved |
| Owner identity, master key, home law, policy semantics | **Not modified** |

## New packages

- `ssn.cognition.*`
- `ssn.embodiment.*`

## Optional env

```bash
SSN_LLM_PROVIDER=deterministic   # model gateway path via LanguageEngine
# default remains: dummy
```

## Adopting the cognitive loop

```python
from ssn.cognition.loop import CognitiveLoop, CognitiveRuntime
from ssn.bootstrap import create_siona

orch = create_siona()
rt = CognitiveRuntime.create(memory_hub=orch.memory, world_model=orch.world_model)
loop = CognitiveLoop(rt)
result = loop.process_text("hello", role="GUEST")
# result["reply"], result["proposals"] — proposals need existing validation
```

Or use `runtime.cognitive_runtime` from `SSNRuntimeBuilder.build_default()`.

## Breaking changes

None intended for Phase 1. Existing tests should continue to pass.

## Owner-control freeze

Do not use this migration as a vehicle to redesign OWNER/GUEST behaviour,
master keys, or `home_law_samson.yaml`.
