# SIONA boot path (canonical)

Every entry point must converge on one initialization chain.

## Flow

```
CLI / HTTP / Voice (planned)
        │
        ▼
  Front Door (ssn/interfaces/front_door.py)
  handle_user_message(...)  OR  InterfaceGateway.handle(...)
        │
        ├── HTTP API (ssn/runtime/http_server.py)  ← Phase 2
        │     POST /v1/chat · POST /v1/tool/run · GET /v1/health
        │
        ▼
  Interface Gateway (ssn/interfaces/gateway.py)
  policy scrub · handler routing · secret redaction
        │
        ▼
  Orchestrator (ssn/core/orchestrator.py)
  identity · policy · brain routing · tools
        │
        ├── BrainRouter → LanguageEngine → LLMProvider
        ├── ToolRegistry (net.*, research.*, memory.*, …)
        ├── MemoryHub / KnowledgeStore
        ├── WorldModel + PerceptionHub
        ├── PolicyEngine (world + system + home law)
        └── CognitiveRuntime (additive; ssn/cognition)
              events · workspace · model gateway · neuromorphic
```

## Canonical construction

```python
from ssn.bootstrap import create_siona
from ssn.runtime.runtime_builder import SSNRuntimeBuilder

# Preferred for CLI / services:
runtime = SSNRuntimeBuilder.build_default(default_role="GUEST")
gateway = runtime.gateway
orchestrator = runtime.orchestrator

# Lower-level (tools/tests):
orch = create_siona()
```

## LLM plug-in (Phase 1)

```bash
# Terminal 1
python scripts/mock_llm_server.py

# Terminal 2 — CLI
export SSN_LLM_PROVIDER=http
export SSN_LLM_ENDPOINT=http://127.0.0.1:8000/generate
python -m ssn.runtime.cli console --role GUEST
```

## HTTP API (Phase 2)

```bash
# Terminal 1 — optional mock LLM
python scripts/mock_llm_server.py

# Terminal 2 — HTTP Front Door
export SSN_OFFLINE=1
export SSN_LLM_PROVIDER=http
export SSN_LLM_ENDPOINT=http://127.0.0.1:8000/generate
python -m ssn.runtime.http_server --port 8080

# Terminal 3 — chat
curl -X POST http://127.0.0.1:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"hello","role":"GUEST","offline":true}'
```

## Rules

1. Do not construct parallel ToolRegistry / MemoryHub instances in entry points.
2. Register tools only via `create_siona()` (idempotent).
3. All OWNER writes go through policy + tool gates.
4. `SSN_OFFLINE=1` for CI and deterministic tests.

See `docs/SIONA_BUILD_PLAN.md` for the full roadmap.
