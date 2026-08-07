# Deferred Capabilities

Durable IDs for work that is architecturally prepared but not yet fully executed
or verified. Current phase authority comes from `PHASE_STATUS.md`, accepted ADRs,
and phase acceptance/specification records.

---

### ID: HW-SNN-001
- **Capability:** Learned SNN software provider, with later CUDA acceleration
- **Status:** **Phase 4 accepted for the bounded CPU-trained software SNN provider**
- **Accepted implementation:** `siona-neuro-learned-lif-v1` using the verified `phase4b-lif-final-membrane-v1` artifact; pure-Python runtime; deterministic provider retained as default/fallback
- **Accepted task:** `phase4a-temporal-salience-v1` (20 × 8 binary temporal sequence)
- **Accepted evidence:** EXP-4-003 training, EXP-4-004 parity, EXP-4-005 breadth/safety, ADR 0004 Accepted, `PHASE_4_ACCEPTANCE.md`
- **Still deferred:** CUDA/GPU training or benchmarking, event-by-event persistent streaming SNN inference, real event-camera input, Loihi/FPGA/neuromorphic-silicon execution, measured energy-efficiency claims
- **Hardware-gated work:** CUDA training/benchmark remains deferred until an approved CUDA-capable environment exists

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
- **Target phase:** Later; no current phase selected
- **Acceptance evidence:** Documented SIONA-controlled tokenizer/data/training/checkpoint/evaluation provenance

### ID: MODEL-ADAPT-001
- **Capability:** SIONA-specific language-model adapters / LoRA / QLoRA / PEFT
- **Status:** Deferred; no adapter training has occurred
- **Reason:** Requires a separate dataset-rights, training, evaluation and ownership decision
- **Current implementation:** None
- **Target phase:** Later; no current phase selected
- **Acceptance evidence:** Approved dataset/provenance + reproducible training + adapter checksum + held-out evaluation

### ID: HW-BENCH-001
- **Capability:** GPU benchmarking for learned neuromorphic workloads
- **Status:** Hardware-gated / deferred
- **Reason:** No CUDA GPU on current development computer
- **Target phase:** Later optional hardware-gated evidence; not required for accepted Phase 4 software scope
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
- **Reason:** User-facing embodiment is separate from the accepted learned neuromorphic core milestone
- **Target phase:** Later

### ID: CLOUD-001
- **Capability:** Cloud compute fabric
- **Status:** Deferred
- **Reason:** Current architecture remains local-first and provider-replaceable
- **Target phase:** Later

### ID: HW-NEURO-ASIC-001
- **Capability:** Neuromorphic hardware deployment (Loihi/FPGA)
- **Status:** Provider abstraction and learned software SNN evidence exist; silicon execution deferred
- **Target phase:** Later under a separate hardware/energy evidence gate
