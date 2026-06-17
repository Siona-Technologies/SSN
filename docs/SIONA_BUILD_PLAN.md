# SIONA Platform Build Plan

**Author:** Samson Sibona Njaji · SSN / SIONA  
**Status:** Active — build-before-code reference  
**Last updated:** 2026-06-17  
**Audience:** Samson + future contributors  

---

## 1. North star

SIONA is a **law-bound, deployable cognitive runtime** — infrastructure others can run, not a personal chatbot only.

| Principle | Meaning |
|-----------|---------|
| **One brain, many deployments** | Same `create_siona` bootstrap; different law YAML, state dir, models per tenant |
| **Law before scale** | Policy, audit, proposal→approval→commit are the product moat |
| **Brain before weights** | Runtime stable first; LLM is a swappable organ |
| **PC today, GPU tomorrow** | Phases 0–6 run on a normal developer machine |
| **Samson = deployment #1** | `home_law_samson.yaml` is the first instance of “law as code” |

Long-term arc: personal Jarvis → deployable platform → regional sovereign AI (OpenAI/Meta-class **institution**, not a wrapper).

---

## 2. Current baseline (as of 2026-06-17)

### 2.1 What is built and strong

| Area | Location | Notes |
|------|----------|-------|
| Canonical bootstrap | `ssn/bootstrap.py` → `create_siona()` | Single init path; idempotent tool registration |
| Runtime wrapper | `ssn/runtime/runtime_builder.py` → `SSNRuntimeBuilder.build_default()` | Wires gateway, shell, perception fallback |
| Front Door (CLI) | `ssn/interfaces/front_door.py`, `ssn/runtime/cli.py` | OWNER/GUEST, offline, tools, research |
| Interface gateway | `ssn/interfaces/gateway.py` | Secret redaction, handler routing |
| Policy engine | `ssn/policy/policy_engine.py` | world + system + Samson home law |
| Brain / fusion | `ssn/core/brain_router.py`, `fusion_engine.py`, `brain_modes.py` | LLM + SNN hybrid, fast/deep/hybrid modes |
| LLM abstraction | `ssn/core/llm_providers.py` | `LocalDummyLLMProvider`, `HttpLLMProvider` |
| Tools platform | `ssn/tools/*`, `ssn/bootstrap.py` | net.*, research.*, memory.*, knowledge.*, speech.* (stub) |
| Senses pipeline | `ssn/senses/*` | Encoders, SensoryBus, PerceptionHub, DeltaBuilder |
| World model | `ssn/world/world_model.py` | Bounded entities/events |
| Memory / knowledge | `ssn/memory/*`, `ssn/knowledge/store.py` | Proposal/commit; JSONL knowledge (keyword search) |
| Eval harness | `ssn/eval/runner.py`, `scenarios.py` | 4 deterministic scenarios (gateway doubles) |
| Docs | `README.md`, `ENVIRONMENT.md`, `LLM_STRATEGY_V10.md`, `docs/SIONA_AWS_ARCHITECTURE_SHOWCASE.md` | |
| Tests | `ssn/tests/` (~106 tests collected) | Broad phase coverage |

### 2.2 What is not built yet

| Gap | Roadmap phase |
|-----|---------------|
| Mock / real inference server | Phase 1 |
| HTTP Front Door (REST API) | Phase 2 |
| Configurable law paths (multi-tenant) | Phase 3 |
| Real STT/TTS (speech tools stubbed) | Phase 4 |
| Vector embeddings / semantic RAG | Phase 5 |
| systemd / production deploy layout | Phase 6 |
| Local GPU models + fine-tuning | Phase 7 (hardware) |
| GitHub Actions CI | Phase 0 |
| Web / dashboard UI | Post Phase 2 |

### 2.3 Dependencies today

```
requirements.txt:
  python-dotenv==1.2.1
  PyYAML==6.0.3
```

No FastAPI, no pytest in requirements — tests use `unittest`. New HTTP layers should prefer **stdlib `http.server`** first to avoid dependency sprawl; FastAPI optional later.

---

## 3. Attention items (review before coding)

These were found during codebase review. **Resolve or track each item in the phase where noted.**

### 3.1 Critical — Phase 0

| ID | Issue | Detail | Action |
|----|-------|--------|--------|
| **A-01** | Test suite not green locally | `unittest discover` → **26 failures, 25 errors** (106 tests) | Audit failures; fix or quarantine with explicit markers; target green offline CI |
| **A-02** | No CI pipeline | No `.github/workflows/` | Add GitHub Action: `SSN_OFFLINE=1`, run unittest |
| **A-03** | Eval harness bypasses full runtime | `build_default_eval_gateway()` uses dummy orchestrator, not `create_siona` | Add `build_production_eval_gateway()` using `SSNRuntimeBuilder` |
| **A-04** | Only 4 eval scenarios | `ssn/eval/scenarios.py` | Expand to 15+ covering policy, memory, research offline, redaction |

### 3.2 Architecture — address in Phases 1–3

| ID | Issue | Detail | Action |
|----|-------|--------|--------|
| **A-05** | Policy law paths hard-coded | `PolicyEngine.__init__` loads fixed filenames from `ssn/policy/` | Phase 3: `SSN_HOME_LAW_PATH`, `SSN_WORLD_LAW_PATH`, `SSN_SYSTEM_LAW_PATH` |
| **A-06** | Single LLM endpoint | `BrainRouter` → one `LanguageEngine()`; no fast/deep split | Phase 1: `SSN_LLM_ENDPOINT_FAST` / `SSN_LLM_ENDPOINT_DEEP` + router wiring |
| **A-07** | PerceptionHub import fallback path | `runtime_builder.py` tries `ssn.perception.perception_hub`; real module is `ssn.senses.perception_hub` | Fix import path; add smoke test |
| **A-08** | ENVIRONMENT.md incomplete | Missing `SSN_LLM_*`, `SSN_MASTER_KEY`, `SSN_KNOWLEDGE_PATH`, `SSN_AUTO_DOTENV` | Update when each phase lands |
| **A-09** | `.env.example` incomplete | No `SSN_MASTER_KEY`, `SSN_KNOWLEDGE_PATH`, law paths, LLM fast/deep | Extend in Phase 1/3 |

### 3.3 Platform readiness — Phases 4–6

| ID | Issue | Detail | Action |
|----|-------|--------|--------|
| **A-10** | Speech tools are stubs | `ssn/tools/speech_tools.py` — no mic/speaker I/O | Phase 4: optional deps + offline backends |
| **A-11** | Knowledge search is keyword-only | `KnowledgeStore._tokenize` — no vectors | Phase 5: `EmbeddingProvider` |
| **A-12** | Semantic memory is KV JSON | `ssn/memory/semantic_store.py` — no embeddings | Phase 5: optional vector index |
| **A-13** | No session / tenant model | Only `SSN_STATE_DIR` partially isolates state | Phase 2: session store; Phase 3: tenant example layout |
| **A-14** | No structured audit log export | Traces in memory hub; no JSON log sink | Phase 6: structured logging for deployments |
| **A-15** | No packaging (`pyproject.toml`) | Manual `python -m` invocations | Phase 6: optional `pyproject.toml` + console entry points |
| **A-16** | WorldModel test API drift | Tests expect `WorldModelConfig` / `apply_delta`; implementation uses `apply_update` | Phase 5 world model sync or update tests |
| **A-17** | Guest tool policy gap | `tools.public_list` denied for GUEST at policy layer | Phase 3: allowlist guest-safe introspection tools in policy |

### 3.5 Sprint 1 completed (2026-06-17)

| Item | Status |
|------|--------|
| Mock LLM server | `ssn/runtime/mock_llm_server.py`, `scripts/mock_llm_server.py` |
| HttpLLM integration test | `ssn/tests/test_mock_llm_integration.py` |
| Front Door `_orch_call` + `llm_route` | `ssn/interfaces/front_door.py` |
| PerceptionHub import fix | `ssn/runtime/runtime_builder.py` |
| CI workflow | `.github/workflows/ci.yml` |
| CI test runner | `scripts/run_tests.py` (55 tests, offline) |
| Eval harness expanded | 6 default + 1 production scenarios |
| Eval runner | `build_production_eval_gateway()` |
| Script test import guards | Manual/demo tests wrapped in `__main__` |
| BOOT_PATH doc | `docs/BOOT_PATH.md` |
| ENVIRONMENT.md LLM vars | Updated |

### 3.6 Sprint 2 completed (2026-06-17)

| Item | Status |
|------|--------|
| HTTP server | `ssn/runtime/http_server.py` |
| Session store | `ssn/runtime/session_store.py` |
| Shared context helpers | `ssn/runtime/frontdoor_context.py` |
| HTTP tests | `ssn/tests/test_http_front_door.py` (9 tests) |
| Smoke script | `scripts/smoke_http.py` |
| CLI refactor | Uses shared `frontdoor_context` |
| CI | HTTP tests + smoke in workflow |

**Exit criteria met:**
```bash
SSN_OFFLINE=1 python -m ssn.runtime.http_server --port 8080
curl -X POST http://127.0.0.1:8080/v1/chat -H "Content-Type: application/json" \
  -d '{"message":"hello","role":"GUEST","offline":true}'
```

### 3.4 Intentional deferrals (not bugs)

| Item | Reason |
|------|--------|
| Real vision models | Encoders exist; models wait for GPU / Phase 7 |
| Multi-tenant AWS | Phase 7 / post Phase 6 |
| Bedrock / vendor APIs | Provider abstraction allows later; not priority |
| Foundation model pretraining | Fine-tune/distill path in Phase 7, not from-scratch pretrain |

---

## 4. Build phases

Each phase has: **goal**, **deliverables**, **files to create/touch**, **exit criteria**, **hardware**.

---

### Phase 0 — Foundation lock

**Goal:** Trustworthy regression base; one documented boot path; CI green offline.

**Duration estimate:** ~1 week  

| Task | Deliverable |
|------|-------------|
| 0.1 | Fix or document all failing/erroring tests (**A-01**) |
| 0.2 | Add `.github/workflows/ci.yml` — Python 3.11+, `SSN_OFFLINE=1`, unittest (**A-02**) |
| 0.3 | Add `docs/BOOT_PATH.md` — diagram: CLI/HTTP → Front Door → Gateway → Orchestrator |
| 0.4 | Add `build_production_eval_gateway()` in `ssn/eval/runner.py` (**A-03**) |
| 0.5 | Expand `ssn/eval/scenarios.py` to 15+ scenarios (**A-04**) |
| 0.6 | Add `scripts/run_eval.py` CLI wrapper |
| 0.7 | Update `ENVIRONMENT.md` with all known env vars (**A-08**) |

**Exit criteria:**
```bash
SSN_OFFLINE=1 python -m unittest discover -s ssn/tests -p "test_*.py"
SSN_OFFLINE=1 python scripts/run_eval.py   # all scenarios pass
```

**Hardware:** Normal PC.

---

### Phase 1 — Inference layer

**Goal:** External mind plugs in via HTTP; fast/deep routing ready for two models later.

**Duration estimate:** ~2 weeks  
**Depends on:** Phase 0 (tests green)

| Task | Deliverable |
|------|-------------|
| 1.1 | `scripts/mock_llm_server.py` — stdlib HTTP, `POST /generate`, JSON contract per `LLM_STRATEGY_V10.md` |
| 1.2 | `ssn/tests/test_mock_llm_integration.py` — server up → real response (not stub fallback) |
| 1.3 | `MultiEndpointLLMProvider` or extend `HttpLLMProvider` with mode-aware URL selection (**A-06**) |
| 1.4 | Wire `BrainRouter` / `LanguageEngine` to pick endpoint by `BrainModes.get_mode()` |
| 1.5 | Env vars: `SSN_LLM_ENDPOINT_FAST`, `SSN_LLM_ENDPOINT_DEEP` (fallback to `SSN_LLM_ENDPOINT`) |
| 1.6 | Update `.env.example`, `ENVIRONMENT.md`, `LLM_STRATEGY_V10.md` |
| 1.7 | Fix PerceptionHub import in `runtime_builder.py` (**A-07**) |

**New env vars:**
```bash
SSN_LLM_PROVIDER=http          # dummy | http
SSN_LLM_ENDPOINT=http://127.0.0.1:8000/generate
SSN_LLM_ENDPOINT_FAST=http://127.0.0.1:8000/generate
SSN_LLM_ENDPOINT_DEEP=http://127.0.0.1:8001/generate
```

**Exit criteria:**
```bash
# Terminal 1
python scripts/mock_llm_server.py --port 8000

# Terminal 2
SSN_OFFLINE=1 SSN_LLM_PROVIDER=http SSN_LLM_ENDPOINT=http://127.0.0.1:8000/generate \
  python -m ssn.runtime.cli console --role GUEST
# Answer comes from mock server, not dummy template
```

**Hardware:** Normal PC.

---

### Phase 2 — HTTP Front Door (platform API)

**Goal:** First public API surface — how external apps and future tenants talk to SIONA.

**Duration estimate:** ~2–3 weeks  
**Depends on:** Phase 1

| Task | Deliverable |
|------|-------------|
| 2.1 | `ssn/runtime/http_server.py` — stdlib or minimal ASGI |
| 2.2 | `POST /v1/chat` — wraps `handle_user_message` |
| 2.3 | `POST /v1/tool/run` — OWNER-gated tool execution |
| 2.4 | `GET /v1/health` — liveness |
| 2.5 | `ssn/runtime/session_store.py` — file-backed sessions under `${SSN_STATE_DIR}/sessions/` (**A-13**) |
| 2.6 | Auth: `Authorization: Bearer` or `X-SSN-Master-Key` for OWNER; optional API key for GUEST |
| 2.7 | `ssn/tests/test_http_front_door.py` |
| 2.8 | `scripts/smoke_http.py` |
| 2.9 | `python -m ssn.runtime.http_server` entry |

**Request shape (chat):**
```json
{
  "message": "hello",
  "role": "GUEST",
  "session_id": "optional-uuid",
  "context": {},
  "offline": true
}
```

**Response shape:** Same bounded fields as CLI Front Door (`answer`, `notes`, `citations`, `sources`, `used_tools`).

**Exit criteria:**
```bash
SSN_OFFLINE=1 python -m ssn.runtime.http_server --port 8080
curl -X POST http://127.0.0.1:8080/v1/chat -H "Content-Type: application/json" \
  -d '{"message":"hello","role":"GUEST","offline":true}'
```

**Hardware:** Normal PC.

---

### Phase 3 — Law & tenant readiness

**Goal:** Samson law = instance #1; second deployment uses different law without code fork.

**Duration estimate:** ~2 weeks  
**Depends on:** Phase 2

| Task | Deliverable |
|------|-------------|
| 3.1 | `PolicyEngine` accepts env law paths (**A-05**) |
| 3.2 | `deploy/tenant.example/` — sample org law YAML + `.env.example` |
| 3.3 | `deploy/samson.home/` — document Samson deployment #1 layout |
| 3.4 | Tests: same action allowed under Samson law, denied under stricter tenant law |
| 3.5 | Document tenant isolation: separate `SSN_STATE_DIR`, `SSN_KNOWLEDGE_PATH`, law paths |
| 3.6 | HTTP server: optional `X-SSN-Tenant-ID` header → state dir suffix (simple v1) |

**New env vars:**
```bash
SSN_HOME_LAW_PATH=ssn/policy/home_law_samson.yaml
SSN_WORLD_LAW_PATH=ssn/policy/world_law.yaml
SSN_SYSTEM_LAW_PATH=ssn/policy/system_law.yaml
SSN_KNOWLEDGE_PATH=ssn/knowledge/knowledge.jsonl
```

**Exit criteria:** Two configs boot with different law files and separate `.ssn_state_*` dirs; policy outcomes differ predictably.

**Hardware:** Normal PC.

---

### Phase 4 — Senses & voice skeleton

**Goal:** Prove human-like loop (sense → world → cognition → speech) on CPU.

**Duration estimate:** ~2–3 weeks  
**Depends on:** Phase 2 (HTTP optional for demo)

| Task | Deliverable |
|------|-------------|
| 4.1 | `scripts/sense_tick_demo.py` — synthetic vision/audio events → world model |
| 4.2 | Wire `speech.stt.listen` to offline STT (optional dep: faster-whisper or whisper.cpp CLI) (**A-10**) |
| 4.3 | Wire `speech.tts.speak` to offline TTS (optional dep: piper) |
| 4.4 | CLI subcommand: `ssn-cli voice-once` — record → STT → Front Door → TTS (OWNER) |
| 4.5 | Document optional deps in `requirements-voice.txt` (not required for CI) |
| 4.6 | Tests: speech tools return structured responses; no mic in CI |

**Exit criteria:** OWNER push-to-talk works locally with optional deps installed; CI passes without voice deps.

**Hardware:** Normal PC + microphone (local dev only).

---

### Phase 5 — Embeddings & knowledge RAG

**Goal:** Smarter retrieval for memory and knowledge at platform scale.

**Duration estimate:** ~2 weeks  
**Depends on:** Phase 3

| Task | Deliverable |
|------|-------------|
| 5.1 | `ssn/core/embedding_providers.py` — protocol + `DeterministicHashEmbedding` |
| 5.2 | `HttpEmbeddingProvider` for future local embed server |
| 5.3 | Optional vector index (start: numpy + JSON sidecar, no heavy deps) (**A-11**, **A-12**) |
| 5.4 | Upgrade `KnowledgeStore.search` to use embeddings when `SSN_EMBEDDING_PROVIDER=http` |
| 5.5 | Offline tests use deterministic embedder only |

**New env vars:**
```bash
SSN_EMBEDDING_PROVIDER=deterministic   # deterministic | http
SSN_EMBEDDING_ENDPOINT=http://127.0.0.1:8002/embed
```

**Exit criteria:** Knowledge search rank changes with semantic similarity in live mode; offline tests unchanged and deterministic.

**Hardware:** Normal PC (CPU embedder); GPU optional.

---

### Phase 6 — Production shape

**Goal:** `systemctl start siona` on Ubuntu Jarvis box; audit-ready logging.

**Duration estimate:** ~1 week  
**Depends on:** Phases 2, 3, 5

| Task | Deliverable |
|------|-------------|
| 6.1 | `deploy/siona.service` — systemd unit |
| 6.2 | `deploy/README.md` — install, env, health, backup |
| 6.3 | `scripts/backup_state.sh` — backup `SSN_STATE_DIR` |
| 6.4 | Structured JSON logging to stdout (**A-14**) |
| 6.5 | Optional `pyproject.toml` with `[project.scripts]` (**A-15**) |
| 6.6 | Update `SIONA_AWS_ARCHITECTURE_SHOWCASE.md` with built vs planned status |

**Exit criteria:** Service starts on Ubuntu; `/v1/health` returns OK; backup/restore documented.

**Hardware:** Test on PC; full always-on on dedicated box later.

---

### Phase 7 — Real mind (hardware-funded)

**Goal:** Local GPU inference + owner fine-tuning where generic models fail.

**Duration estimate:** When budget allows  
**Depends on:** Phases 1–6 complete

| Task | Deliverable |
|------|-------------|
| 7.1 | Ollama / vLLM / llama.cpp on ROCm (395-class workstation) |
| 7.2 | Fast 7–8B always loaded; deep 32B+ for OWNER mode |
| 7.3 | Fine-tune / distill pipeline for law compliance, locale, tool behavior |
| 7.4 | Optional AWS GPU pool for burst / multi-tenant (see architecture showcase) |

**Hardware:** Ryzen AI Max+ 395 (128GB) or AWS g5/g6.

---

## 5. Phase dependency graph

```
Phase 0 (tests + CI + eval)
    │
    ▼
Phase 1 (mock LLM + HttpLLMProvider + fast/deep)
    │
    ▼
Phase 2 (HTTP Front Door API) ──────────────┐
    │                                        │
    ├──────────────────┐                     │
    ▼                  ▼                     ▼
Phase 3            Phase 4               (demo UI later)
(tenant law)       (senses + voice)
    │
    ▼
Phase 5 (embeddings)
    │
    ▼
Phase 6 (systemd deploy)
    │
    ▼
Phase 7 (GPU + fine-tune)  ← requires hardware budget
```

**Critical path:** 0 → 1 → 2 → 3  
Phases 4 and 5 can overlap after Phase 2.

---

## 6. Target folder layout (new work)

```
SSN/
├── docs/
│   ├── SIONA_BUILD_PLAN.md          ← this file
│   ├── SIONA_AWS_ARCHITECTURE_SHOWCASE.md
│   └── BOOT_PATH.md                 ← Phase 0
├── deploy/
│   ├── README.md                    ← Phase 6
│   ├── siona.service                ← Phase 6
│   ├── samson.home/                 ← Phase 3
│   │   └── .env.example
│   └── tenant.example/              ← Phase 3
│       ├── home_law_org.yaml
│       └── .env.example
├── scripts/
│   ├── mock_llm_server.py           ← Phase 1
│   ├── run_eval.py                  ← Phase 0
│   ├── smoke_http.py                ← Phase 2
│   ├── sense_tick_demo.py           ← Phase 4
│   └── backup_state.sh              ← Phase 6
├── ssn/
│   ├── runtime/
│   │   ├── http_server.py           ← Phase 2
│   │   └── session_store.py         ← Phase 2
│   └── core/
│       └── embedding_providers.py   ← Phase 5
├── requirements-voice.txt           ← Phase 4 (optional)
└── .github/workflows/ci.yml         ← Phase 0
```

---

## 7. Platform coding rules (all phases)

1. **Every external interface goes through Front Door + policy** — no bypass shortcuts.
2. **Secrets never in traces, memory, git, or logs.**
3. **`SSN_OFFLINE=1` tests must pass without network, GPU, or mic.**
4. **Prefer env/config over hard-coding Samson-specific logic** — prepare for tenant #2.
5. **One bootstrap path:** `create_siona()` for CLI, HTTP, voice, future robots.
6. **Minimal dependencies** — stdlib first; optional extras in separate requirements files.
7. **Idempotent tool registration** — bootstrap safe to call multiple times.
8. **Bounded outputs** — reuse Front Door clip limits for HTTP responses.

---

## 8. First coding sprint (when we start)

**Sprint 1 = Phase 0 + Phase 1.1–1.2** (documented here; code next session)

| Order | Task | Files |
|-------|------|-------|
| 1 | Triage test failures (**A-01**) | `ssn/tests/*` |
| 2 | Add CI workflow (**A-02**) | `.github/workflows/ci.yml` |
| 3 | Mock LLM server | `scripts/mock_llm_server.py` |
| 4 | Integration test | `ssn/tests/test_mock_llm_integration.py` |
| 5 | Fix PerceptionHub import (**A-07**) | `ssn/runtime/runtime_builder.py` |
| 6 | Expand eval scenarios | `ssn/eval/scenarios.py` |

**Do not start Phase 2 HTTP until Phase 1 mock LLM E2E is green.**

---

## 9. Success milestones

| Milestone | Phases | What it proves |
|-----------|--------|----------------|
| **M1: Trustworthy base** | 0 | CI green; eval expanded; boot path documented |
| **M2: Pluggable mind** | 1 | HTTP LLM works; fast/deep env ready |
| **M3: Platform API** | 2 | External apps can call SIONA |
| **M4: Multi-deployment** | 3 | Law + state isolation for tenant #2 |
| **M5: Embodied demo** | 4 | Senses + voice loop on CPU |
| **M6: Smart memory** | 5 | Embedding-backed knowledge |
| **M7: Jarvis-ready** | 6 | systemd deploy on Ubuntu |
| **M8: Real intelligence** | 7 | Local GPU + fine-tuned weights |

---

## 10. References

| Document | Purpose |
|----------|---------|
| `README.md` | Project overview |
| `ENVIRONMENT.md` | Runtime env vars |
| `LLM_STRATEGY_V10.md` | LLM provider contract |
| `docs/SIONA_AWS_ARCHITECTURE_SHOWCASE.md` | AWS / scale vision |
| `ssn/policy/home_law_samson.yaml` | Deployment #1 law |
| `ssn/bootstrap.py` | Canonical init |

---

## 11. Change log

| Date | Change |
|------|--------|
| 2026-06-17 | Sprint 3: configurable law paths, tenant deploy layouts, bounded OWNER mode |
| 2026-06-17 | Sprint 2: HTTP Front Door API, session store, 9 HTTP tests, CI smoke |
| 2026-06-17 | Sprint 1: mock LLM, CI, eval expansion, boot path doc, test triage (partial) |
| 2026-06-17 | Initial plan: Phases 0–7, attention items A-01–A-15, first sprint defined |

---

*Next step: Phase 4 — senses demo + CPU speech skeleton.*
