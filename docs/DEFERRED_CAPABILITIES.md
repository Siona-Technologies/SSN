# Deferred Capabilities

Durable IDs for work that remains unexecuted or only partially verified. Current
phase authority comes from `PHASE_STATUS.md`, accepted ADRs and phase acceptance
records.

---

### ID: HW-SNN-001
- **Capability:** First learned SNN software backend
- **Status:** **Completed and accepted in Phase 4 for the bounded CPU software-SNN scope**
- **Current implementation:** `siona-neuro-learned-lif-v1` + governed artifact `phase4b-lif-final-membrane-v1`; deterministic provider retained as default/fallback
- **Accepted evidence:** EXP-4-003/004/005 + `PHASE_4_ACCEPTANCE.md` + ADR 0004 Accepted
- **Not included in acceptance:** CUDA/GPU, Loihi/FPGA, neuromorphic silicon, real event-camera execution, general-purpose SNN cognition
- **Completed phase:** Phase 4

### ID: HW-LLM-001
- **Capability:** Optional local open-weight language-model inference
- **Status:** **Phase 3B accepted for the pinned conservative baseline**
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
- **Target phase:** Later; not automatically Phase 5
- **Acceptance evidence:** Documented SIONA-controlled tokenizer/data/training/checkpoint/evaluation provenance

### ID: MODEL-ADAPT-001
- **Capability:** SIONA-specific language-model adapters / LoRA / QLoRA / PEFT
- **Status:** Deferred; no adapter training has occurred
- **Reason:** Requires a separate dataset-rights, training, evaluation and ownership decision
- **Current implementation:** None
- **Target phase:** Later; not automatically Phase 5
- **Acceptance evidence:** Approved dataset/provenance + reproducible training + adapter checksum + held-out evaluation

### ID: SNN-STREAM-001
- **Capability:** Stateful event-by-event / asynchronous learned SNN execution
- **Status:** Deferred
- **Reason:** Accepted Phase 4 provider consumes complete 20×8 temporal windows; streaming state semantics, reset/isolation, backpressure and long-lived-state safety require a separate design/evidence gate
- **Target phase:** Later; candidate for Phase 5 planning, not automatically selected
- **Acceptance evidence:** Explicit streaming-state contract + deterministic parity/evaluation + failure/reset/isolation evidence

### ID: HW-BENCH-001
- **Capability:** GPU benchmarking for learned neuromorphic workloads
- **Status:** Hardware-gated / deferred
- **Reason:** No CUDA GPU on current development computer
- **Target phase:** Later; not part of accepted Phase 4 CPU scope
- **Acceptance evidence:** Reproducible benchmark on identified GPU/runtime; never inferred from CPU measurements

### ID: HW-SIM-001
- **Capability:** Isaac Sim robotics simulation
- **Status:** Deferred
- **Reason:** Heavy GPU/simulation stack; embodiment contracts only
- **Target phase:** Later

### ID: HW-SENS-001
- **Capability:** Event-camera hardware
- **Status:** Deferred
- **Reason:** No event-camera is part of the accepted SIONA Core learned-SNN baseline
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
- **Target phase:** Later

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
- **Status:** Provider abstraction and learned software SNN exist; silicon execution remains deferred
- **Target phase:** Later after separate hardware/evidence gate
