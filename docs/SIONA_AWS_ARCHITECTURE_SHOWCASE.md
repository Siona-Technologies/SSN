# SIONA — Architecture Showcase for AWS Developers

**Samson Sibona Njaji · SSN / SIONA Hybrid Brain Platform**  
**Document purpose:** Technical overview for architecture review, AWS deployment discussion, and roadmap alignment.

---

## 1. Executive summary

**SIONA** is a **law-bound, owner-controlled hybrid brain platform**—not a chatbot wrapper. It combines perception, long-term memory, a world model, tool execution, and a pluggable language core so organizations can run AI that remains **auditable**, **offline-capable**, and **under explicit policy and owner approval**.

**Positioning:** Infrastructure for a **sovereign, deployable cognitive runtime**—designed to run on a dedicated workstation, on-premises servers, or **AWS GPU compute**—with African ownership of laws, data boundaries, and model strategy over time.

---

## 2. Problem statement

| Challenge | How SIONA addresses it |
|-----------|-------------------------|
| Foreign AI as a black box | Runs on **your** hardware or **your** cloud account; actions are tool-gated and traced |
| No long-term context | **Memory** (semantic, episodic, trace) + **curated knowledge** + **world model** |
| Unsafe automation | **Proposal → approval → commit** for memory/knowledge; write tools require OWNER + policy |
| Dependency on single vendor APIs | **Pluggable LLM providers** (local HTTP, future custom weights); brain code stays stable |
| Regional AI sovereignty | **Owner law** (Samson home law) + local-first design; tunable to local language, law, and systems |

**One-liner:** *SIONA is a safe, owner-controlled Jarvis-class brain that turns your data, tools, and sensors into a single intelligent assistant you actually control.*

---

## 3. What is built today (honest status)

### 3.1 Production-oriented foundations (implemented)

- **Layered architecture:** Policy & safety → Interface gateway / Front Door → Orchestrator & BrainRouter → Fusion (LLM + SNN) → Memory & knowledge → World model → Tools
- **Tool platform:** `ToolRegistry` with contracts, role gating (OWNER / GUEST), rate limiting, structured traces, public vs full tool discovery
- **Research pipeline (read-only, bounded):** `net.search` → `net.fetch` → `net.sanitize` → `net.cite` → `research.answer` → optional `research.propose` → **OWNER-only** `memory.commit`
- **Knowledge vs memory separation:** Curated `knowledge.jsonl` (promote/search) vs personal/episodic memory with explicit commits
- **Policy engine:** World law, system law, **Samson home law** (OWNER has ultimate override authority in code)
- **Canonical bootstrap:** Single init path (`create_siona`), idempotent tool registration
- **Pluggable LLM layer:** `LanguageEngine` + `LLMProvider` abstraction; env-driven selection (`SSN_LLM_PROVIDER`, `SSN_LLM_ENDPOINT`); HTTP provider with safe fallback
- **Senses pipeline:** Encoders (vision, audio, IMU, LiDAR, event camera; plus touch, olfaction, gustation, interoception); `PerceptionHub` → world deltas
- **CLI Front Door:** Interactive console (`ssn.runtime.cli console`) with OWNER/GUEST, offline/strict/tools/research toggles
- **HTTP Front Door (Phase 2):** `GET /v1/health`, `POST /v1/chat`, `POST /v1/tool/run`; multi-tenant session isolation
- **Voice skeleton (Phase 4):** STT/TTS tool backends, `voice-once` CLI, optional voice deps
- **Knowledge RAG (Phase 5):** Embedding providers (deterministic + HTTP), vector sidecar on `KnowledgeStore`
- **Production shape (Phase 6):** `deploy/siona.service` systemd unit, `scripts/backup_state.sh`, structured JSON logging, `pyproject.toml` entry points (`siona-cli`, `siona-http`)
- **Documentation:** `README.md`, `ENVIRONMENT.md`, `LLM_STRATEGY_V10.md`, `deploy/README.md`, `.env.example`
- **Source control:** Project maintained on GitHub (`main` branch)

### 3.2 Not yet built (explicit roadmap items)

| Capability | Status |
|------------|--------|
| Production GPU LLM (real model server) | Architecture ready; wire `SSN_LLM_PROVIDER=http` to Ollama/vLLM |
| Always-on systemd service | ✅ `deploy/siona.service` + install guide |
| Voice Jarvis (STT/TTS + hotword) | Phase 4 skeleton; optional deps for mic/speaker |
| Face recognition / vision intelligence | Perception pipeline ready; models not wired |
| Multi-tenant cloud scale | Law paths + tenant state dirs; AWS deployment guide in this doc |
| Web/dashboard UI | HTTP Front Door live; dashboard UI future |

---

## 4. Architecture (logical view)

```
┌─────────────────────────────────────────────────────────────┐
│  INTERFACES                                                  │
│  CLI · HTTP Front Door (/v1/*) · Voice CLI (Phase 4)         │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  FRONT DOOR + POLICY                                         │
│  OWNER verification · approvals · redaction · rate limits    │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  COGNITION                                                   │
│  Orchestrator · BrainRouter · FusionEngine                     │
│  LLM (pluggable provider) + SNN + mode weights (deep/fast/…)   │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌──────────────────────┬──────────────────────────────────────┐
│  MEMORY              │  KNOWLEDGE                            │
│  semantic · episodic │  curated JSONL (promote/search)       │
│  trace · proposals   │  separate from personal memory        │
└──────────────────────┴──────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  WORLD MODEL                                                 │
│  Bounded entities/events · perception ticks · summaries        │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  SENSES                                                      │
│  SensoryBus → Encoders → PerceptionHub → WorldStateDelta     │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  TOOLS & ACTUATION                                           │
│  net.* · research.* · memory.* · knowledge.* · world.* · …   │
└─────────────────────────────────────────────────────────────┘
```

**Design principles (non-negotiable):**

- **Owner-bound:** Only OWNER authorizes state-changing actions.
- **Law-bound:** Every tool/action passes policy + safety.
- **Auditable:** Tool calls and policy outcomes are traced (bounded, redacted).
- **No silent learning:** Knowledge promotion and memory commits require explicit OWNER action.
- **Graceful degradation:** Missing sensors or offline mode must not break cognition.

---

## 5. LLM strategy (GPU-ready, vendor-neutral)

SIONA does **not** hard-code a single LLM vendor.

| Component | Role |
|-----------|------|
| `LanguageEngine` | Stable API for BrainRouter / FusionEngine |
| `LLMProvider` | Pluggable backend (`LocalDummy`, `Http`, future custom) |
| `HttpLLMProvider` | POST JSON to inference server; safe fallback on errors |

**Environment configuration:**

- `SSN_LLM_PROVIDER=dummy` — development / CI (no external model)
- `SSN_LLM_PROVIDER=http` + `SSN_LLM_ENDPOINT=...` — production inference worker

**Request/response contract (HTTP provider):**

Request:

```json
{
  "prompt": "<string>",
  "role": "OWNER|GUEST",
  "context": { }
}
```

Response:

```json
{
  "text": "<model reply>",
  "meta": { "engine": "...", "used_context": true }
}
```

See `LLM_STRATEGY_V10.md` in the repository for full details.

---

## 6. Why this maps to AWS

SIONA is designed as a **deployable cognitive runtime**, not a desktop-only script.

| SIONA layer | AWS mapping (typical) |
|-------------|------------------------|
| Stateless Front Door / API | ALB + ECS/Fargate or EKS pods |
| LLM inference workers | EC2 GPU instances (`g5`, `g6`, `p4`) or SageMaker endpoints |
| Orchestrator / tool workers | CPU ECS/EKS tasks, auto-scaling |
| State & audit | S3, EFS; optional DynamoDB for sessions |
| Secrets | Secrets Manager / Parameter Store (never in traces) |
| Encryption | KMS for vault/backups |
| Network | VPC, private subnets, security groups |
| Observability | CloudWatch logs/metrics; **structured JSON** HTTP audit/access logs (`SSN_STRUCTURED_LOG=1`) |

**Local-first by design; cloud-ready by architecture.** The same codebase can run on a Jarvis workstation or scale on AWS when elastic GPU and multi-tenant isolation are required.

---

## 7. Roadmap (next steps)

### Phase A — Demo-ready (weeks)

1. Deploy **one real LLM** behind `HttpLLMProvider` (open-weight model on GPU VM or EC2).
2. ~~Expose **HTTP Front Door** (stateless) with session backing store.~~ ✅ Done (Phase 2).
3. CI: deterministic offline test suite (`SSN_OFFLINE=1`). ✅ Done.

### Phase B — Jarvis workstation

4. ~~**Ubuntu LTS** dedicated machine; systemd always-on service.~~ ✅ Unit + docs (Phase 6).
5. **Sleep/wake** modes (service runs; interaction gated by owner command).
6. ~~**STT/TTS** tools + minimal UI (push-to-talk).~~ Skeleton done (Phase 4); hotword UI pending.

### Phase C — AWS production shape

7. Split **gateway / inference pool / tool workers**; tenant isolation per V10 blueprint.
8. Cost controls: scale-to-zero or scheduled GPU; caching where safe.
9. Optional: fine-tune or distill owner models (weights remain under our control).

---

## 8. Discussion topics for AWS developers

We are seeking guidance on:

1. **Recommended GPU inference pattern** for always-on vs bursty workloads (EC2 vs SageMaker vs EKS + GPU node groups).
2. **Cost model** for a small always-on Jarvis instance vs scale-to-zero API.
3. **Security checklist** for OWNER keys, audit logs, tool side-effects, and VPC isolation.
4. **Multi-tenant readiness** without rewriting the brain (namespaces, per-tenant state, shared knowledge promotion gates).

---

## 9. FAQ (anticipated questions)

**Q: Is SIONA production-ready today?**  
A: Core runtime, policy, tools, HTTP Front Door, structured logging, and backup paths are production-oriented. Real GPU LLM weights and always-on voice UI are the next integration layers.

**Q: Why not use only Amazon Bedrock?**  
A: Provider abstraction allows Bedrock as one backend later; priority is owner-controlled weights and local/offline operation where required.

**Q: What is unique vs a RAG chatbot?**  
A: Law-bound OWNER control, explicit memory/knowledge writes, world model, full tool trace, and hybrid cognition (LLM + SNN + fusion modes)—not single-shot Q&A.

**Q: Hardware requirement?**  
A: Runs on a developer laptop today (dummy LLM). Jarvis-class experience requires GPU (local desktop or AWS).

---

## 10. Closing statement

> We have built the **brain’s skeleton and nervous system**. The next step is plugging in a **real GPU mind** and **voice/UI** so SIONA can run always-on as Jarvis—on a dedicated Ubuntu workstation or on AWS—with full owner control, auditability, and a path to African AI sovereignty.

---

## References (repository)

| Document | Description |
|----------|-------------|
| `README.md` | Project overview, senses, CLI, LLM providers |
| `ENVIRONMENT.md` | Offline/live flags, state dir, secrets policy |
| `LLM_STRATEGY_V10.md` | LLM provider abstraction and upgrade path |
| `deploy/README.md` | Production install, systemd, backup/restore |
| `.env.example` | Safe environment template |
| `ssn/policy/home_law_samson.yaml` | Owner law and overrides |
| `ssn/bootstrap.py` | Canonical runtime initialization |

**Repository:** SSN / SIONA (GitHub, `main` branch)

---

*Document version: 1.1 · Phases 0–6 built · Phase 7 GPU mind pending*
