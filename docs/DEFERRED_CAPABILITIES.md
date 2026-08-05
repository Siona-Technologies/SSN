# Deferred Capabilities

Durable IDs for work that is architecturally prepared but not executed on the current development computer.

---

### ID: HW-SNN-001
- **Capability:** CUDA-accelerated SNN training
- **Status:** Software architecture prepared; hardware execution deferred
- **Reason:** Current development computer has no NVIDIA CUDA GPU
- **Current implementation:** Deterministic CPU neuromorphic provider
- **Remaining work:** snnTorch backend, dataset training and GPU benchmark
- **Target phase:** Phase 4
- **Acceptance evidence:** Reproducible GPU training and evaluation report

### ID: HW-LLM-001
- **Capability:** Large local language-model inference
- **Status:** Phase 3A foundation ready; real weights/runtime deferred to Phase 3B
- **Reason:** No mandatory large downloads; laptop CPU-first policy
- **Current implementation:** Dummy + deterministic providers; optional LocalOpenWeightProvider (disabled by default; loopback-only)
- **Remaining work:** Select/verify real open-weight model + runtime adapter (Ollama/llama.cpp/etc.)
- **Target phase:** Phase 3B–4
- **Acceptance evidence:** Offline fallback still works; local model optional; real-model eval report

### ID: HW-LLM-002
- **Capability:** SIONA-native model pretraining
- **Status:** Deferred
- **Reason:** Requires dedicated training budget and hardware
- **Current implementation:** N/A (not claimed)
- **Target phase:** Later
- **Acceptance evidence:** Documented training run + eval

### ID: HW-BENCH-001
- **Capability:** GPU benchmarking
- **Status:** Deferred
- **Reason:** No CUDA GPU on current machine
- **Target phase:** Phase 4

### ID: HW-SIM-001
- **Capability:** Isaac Sim robotics simulation
- **Status:** Deferred
- **Reason:** Heavy GPU/sim stack; embodiment contracts only
- **Target phase:** Later

### ID: HW-SENS-001
- **Capability:** Event-camera hardware
- **Status:** Deferred
- **Reason:** No event-camera attached; encoder contracts exist
- **Target phase:** Later

### ID: HW-IOT-001
- **Capability:** Real IoT devices
- **Status:** Deferred — mock adapter only
- **Reason:** Safety and hardware availability
- **Target phase:** After physical-safety kernel

### ID: HW-ROBOT-001
- **Capability:** Physical robot/humanoid
- **Status:** Deferred
- **Reason:** No motor control; mind/body split documented
- **Target phase:** After safety kernel

### ID: DATA-PG-001
- **Capability:** Production database migration
- **Status:** Deferred
- **Reason:** JSON/JSONL sufficient for development; avoid risky migration
- **Target phase:** Later

### ID: CLOUD-001
- **Capability:** Cloud compute fabric
- **Status:** Deferred
- **Reason:** Modular monolith / local-first Phase 1–2
- **Target phase:** Later

### ID: HW-NEURO-ASIC-001
- **Capability:** Neuromorphic hardware deployment (Loihi/FPGA)
- **Status:** Provider abstraction prepared; silicon deferred
- **Target phase:** Later
