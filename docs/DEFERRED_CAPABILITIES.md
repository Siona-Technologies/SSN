# Deferred Capabilities

Durable IDs for work that is architecturally prepared but not yet fully executed
or verified. Current phase authority comes from `PHASE_STATUS.md`, accepted ADRs,
and phase acceptance/specification records.

---

### ID: HW-SNN-001
- **Capability:** Learned SNN training, with later CUDA acceleration
- **Status:** Phase 4 planning candidate; deterministic neuromorphic provider exists; no trained SNN is currently claimed
- **Reason:** Hybrid architecture requires a real learned neuromorphic provider; current development computer has no NVIDIA CUDA GPU
- **Current implementation:** Deterministic CPU neuromorphic/reference provider only
- **Planned next work:** Phase 4A task/dataset/backend governance, then a bounded CPU learned-SNN proof before any separately verified CUDA benchmark
- **Hardware-gated work:** CUDA training/benchmark remains deferred until an approved CUDA-capable environment exists
- **Target phase:** Phase 4
- **Acceptance evidence:** Reproducible authorized training/evaluation report + checkpoint provenance/checksum + provider integration/fallback evidence; GPU evidence recorded separately if executed

### ID: HW-LLM-001
- **Capability:** Optional local open-weight language-model inference
- **Status:** **Phase 3B accepted for the pinned conservative baseline**
- **Reason:** Phase 3 established a real optional local model without making hosted CI or SIONA Core depend permanently on it
- **Current implementation:** `LocalOpenWeightProvider` + canonical registry + llama.cpp b9968 + `Qwen3-1.7B-Q4_K_M`; State C verified; steady-state runtime stopped
- **Accepted capabilities:** bounded text/chat at context 4096; tools=false; structured_json=false; streaming=false; multimodal=false; siona_native=false
- **Remaining work:** larger-model comparisons, acceleration and capability expansion only under later separate authorization
- **Completed phase:** Phase 3B
- **Acceptance evidence:** `PHASE_3B_ACCEPTANCE.md`, EXP-3B-011/012/013, ADR 0003 Accepted

### ID: HW-LLM-002
- **Capability:** SIONA-native foundation-model pretraining
- **Status:** Deferred
- **Reason:** Requires SIONA-controlled training provenance, dedicated data governance, compute budget and hardware
- **Current implementation:** N/A — not claimed
- **Target phase:** Later; not Phase 4
- **Acceptance evidence:** Documented SIONA-controlled tokenizer/data/training/checkpoint/evaluation provenance

### ID: MODEL-ADAPT-001
- **Capability:** SIONA-specific language-model adapters / LoRA / QLoRA / PEFT
- **Status:** Deferred; no adapter training has occurred
- **Reason:** Requires a separate dataset-rights, training, evaluation and ownership decision
- **Current implementation:** None
- **Target phase:** Later; explicitly excluded from Phase 4 learned-neuromorphic scope
- **Acceptance evidence:** Approved dataset/provenance + reproducible training + adapter checksum + held-out evaluation

### ID: HW-BENCH-001
- **Capability:** GPU benchmarking for learned neuromorphic workloads
- **Status:** Hardware-gated / deferred
- **Reason:** No CUDA GPU on current development computer
- **Target phase:** Phase 4 optional hardware-gated evidence
- **Acceptance evidence:** Reproducible benchmark on identified GPU/runtime; never inferred from CPU measurements

### ID: HW-SIM-001
- **Capability:** Isaac Sim robotics simulation
- **Status:** Deferred
- **Reason:** Heavy GPU/simulation stack; embodiment contracts only
- **Target phase:** Later

### ID: HW-SENS-001
- **Capability:** Event-camera hardware
- **Status:** Deferred
- **Reason:** No event-camera is part of the present SIONA Core baseline; encoder/contracts may be explored separately
- **Target phase:** Later

### ID: HW-IOT-001
- **Capability:** Real IoT devices
- **Status:** Deferred — mock/body-independent adapter boundary only
- **Reason:** Physical safety and hardware availability
- **Target phase:** After dedicated physical-safety/capability gates

### ID: HW-ROBOT-001
- **Capability:** Physical robot/humanoid
- **Status:** Deferred
- **Reason:** No motor-control authorization; mind/body split and simulation-first safety principle govern future work
- **Target phase:** After simulation and physical-safety kernel

### ID: DATA-PG-001
- **Capability:** Production database / Postgres-vector migration
- **Status:** Deferred
- **Reason:** Current stores remain sufficient for the accepted local-development baseline; migration is a separate data-integrity decision
- **Target phase:** Later

### ID: MEMORY-SEM-001
- **Capability:** Production semantic retrieval / vector-memory backend
- **Status:** Deferred
- **Reason:** Requires separate memory, privacy, provenance, retention and embedding-governance design
- **Target phase:** Later; explicitly excluded from Phase 4 learned-neuromorphic scope

### ID: VOICE-001
- **Capability:** Real STT/TTS / voice embodiment
- **Status:** Deferred
- **Reason:** User-facing embodiment is separate from the learned neuromorphic core milestone
- **Target phase:** Later

### ID: CLOUD-001
- **Capability:** Cloud compute fabric
- **Status:** Deferred
- **Reason:** Current architecture remains local-first and provider-replaceable
- **Target phase:** Later

### ID: HW-NEURO-ASIC-001
- **Capability:** Neuromorphic hardware deployment (Loihi/FPGA)
- **Status:** Provider abstraction prepared; silicon execution deferred
- **Target phase:** Later after learned-provider software evidence
