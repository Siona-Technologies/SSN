# Phase 3B — Model and Runtime Research

**Status:** official-source research completed — **no final selection approved**  
**Source-access date:** 2026-08-05  
**Hardware baseline:** HP EliteBook 840 G8; Intel i7-1165G7 (4C/8T); Intel Iris Xe; ~15.73 GiB RAM; no CUDA  
**Rule:** facts are labelled as officially stated, calculated estimate, engineering inference, unknown, or requires local benchmark

This document records evidence-based comparisons for optional local runtimes and
small open-weight models. Completing a row is **not** approval to install or
download.

## Research status

| Item | Status |
|------|--------|
| Official-source runtime research | **Completed** (2026-08-05) |
| Official-source model research | **Completed** (2026-08-05) |
| Provisional recommendation | **Recorded — requires owner approval** |
| Runtime installation | **Not authorized** |
| Model download | **Not authorized** |
| Weights | **Not downloaded** |
| Real-model benchmark | **Not started** |

## Sources consulted (primary)

| Source | Role | Accessed |
|--------|------|----------|
| https://github.com/ggml-org/llama.cpp (docs/build.md, docs/backend/SYCL.md, LICENSE, releases b9968) | Runtime | 2026-08-05 |
| https://docs.ollama.com/windows ; https://github.com/ollama/ollama (MIT) | Runtime | 2026-08-05 |
| https://lmstudio.ai/docs/developer/core/server ; https://lmstudio.ai/docs/developer/rest/quickstart | Runtime | 2026-08-05 |
| https://docs.openvino.ai/2026/get-started/install-openvino/install-openvino-genai.html ; GenAI inference docs | Runtime | 2026-08-05 |
| https://onnxruntime.ai / ONNX Runtime GenAI docs (DirectML / WinML path) | Runtime | 2026-08-05 |
| https://huggingface.co/Qwen/Qwen3-1.7B ; Qwen/Qwen3-1.7B-GGUF | Model A | 2026-08-05 |
| https://huggingface.co/ggml-org/Qwen3-1.7B-GGUF | Model A quant alt | 2026-08-05 |
| https://huggingface.co/Qwen/Qwen3-4B ; Qwen/Qwen3-4B-GGUF | Model B | 2026-08-05 |
| https://huggingface.co/ibm-granite/granite-4.0-micro ; ibm-granite/granite-4.0-micro-GGUF ; https://github.com/IBM/gguf | Model C | 2026-08-05 |
| https://huggingface.co/microsoft/Phi-4-mini-instruct | Model D | 2026-08-05 |
| https://huggingface.co/Qwen/Qwen3.5-2B ; HF transformers Qwen3.5 docs | Model E | 2026-08-05 |

---

## Runtime candidates

Release examined for llama.cpp Windows artefacts: **b9968**
(https://github.com/ggml-org/llama.cpp/releases/tag/b9968).

### 1. llama.cpp native Windows CPU

| Field | Finding | Evidence class |
|-------|---------|----------------|
| Project / publisher | ggml-org / llama.cpp | Officially stated |
| Revision examined | Release tag **b9968** (2026-08-05 access) | Officially stated |
| Licence | MIT (LICENSE copyright 2023–2026 The ggml authors) | Officially stated |
| Windows x64 support | Yes — official `llama-b9968-bin-win-cpu-x64.zip` | Officially stated |
| Windows-version requirements | Build docs assume modern VS2022 toolchain; exact minimum OS **REQUIRES VERIFICATION** beyond “Windows x64” | Partial |
| CPU support | Yes (default CPU build) | Officially stated |
| AVX2 requirements | Tiger Lake i7-1165G7 is expected to support AVX2; runtime CPUID not measured here | Engineering inference |
| Intel Iris Xe support | Not used in CPU-only build | Officially stated |
| i7-1165G7 documented | Not required for CPU path | n/a |
| Required drivers | None beyond OS for CPU path | Engineering inference |
| Installation mechanism | Download release zip or build from source (CMake) | Officially stated |
| Portable extraction | Yes — zip binaries | Officially stated |
| Installation footprint | CPU zip ~17.4 MB (release asset size) | Officially stated |
| Background-service behaviour | No installer service; operator starts `llama-server` manually | Engineering inference |
| Auto-start behaviour | None by default | Engineering inference |
| Model-storage / exact file control | Operator chooses GGUF path (`-m`) | Officially stated |
| GGUF support | Yes | Officially stated |
| ONNX support | Not the primary path | Officially stated |
| Quantization support | GGUF quants | Officially stated |
| Local API | `llama-server` HTTP API | Officially stated |
| Default host/port | Commonly `127.0.0.1:8080` in docs/examples; confirm with `--help` at install time | REQUIRES VERIFICATION at install |
| Loopback-only configuration | Bind host to loopback | Engineering inference / install-time |
| OpenAI-compatible endpoint | Available via server OpenAI-compatible routes | Officially stated (server docs family) |
| Structured JSON / grammar | Grammar / constrained decoding supported in llama.cpp ecosystem | Officially stated (project capability) |
| Streaming | Supported | Officially stated |
| Cancellation / timeouts / max response | Server flags exist; exact flag set **REQUIRES VERIFICATION** against chosen binary `--help` | Partial |
| Logging | Stderr/console; file logging **REQUIRES VERIFICATION** | Partial |
| Authentication | Not a first-class auth gateway; treat as unauthenticated local process | Engineering inference |
| Remote-exposure controls | Operator-controlled bind address | Engineering inference |
| Uninstall / rollback | Delete extract directory and model files | Engineering inference |
| LocalOpenWeightProvider fit | Strong — HTTP loopback + exact model ID/path | Engineering inference |
| Required SIONA adapter changes | Likely request/response mapping only; no gateway redesign | Engineering inference |
| CPU suitability (4C/8T) | Suitable for small models; latency unknown until benchmark | Requires local benchmark |
| Expected Iris Xe path | None (CPU) | Officially stated |
| Risks | Endpoint schema drift vs SIONA transport; no speed claim | Open |

### 2. llama.cpp Windows SYCL

| Field | Finding | Evidence class |
|-------|---------|----------------|
| Project / publisher | ggml-org llama.cpp SYCL backend | Officially stated |
| Revision examined | b9968 win-sycl zip; SYCL.md | Officially stated |
| Licence | MIT | Officially stated |
| Windows x64 support | Yes — `llama-b9968-bin-win-sycl-x64.zip` (~110 MB) | Officially stated |
| Windows-version | SYCL.md lists Windows 11 as verified OS | Officially stated |
| CPU support | Host still participates; device offload via SYCL | Officially stated |
| Intel Iris Xe / iGPU | Officially supports Intel iGPU (11th Gen+); SYCL.md lists **i7-1165G7** among iGPU examples | Officially stated |
| Required drivers / toolchain | Intel GPU driver; oneAPI for build; release zip includes depended oneAPI DLLs | Officially stated |
| Portable extraction | Yes (release zip) | Officially stated |
| Background service / auto-start | None by default | Engineering inference |
| Model-file control | Same GGUF path control as CPU | Officially stated |
| GGUF support | Yes | Officially stated |
| Local API / loopback | Same server family as CPU | Engineering inference |
| Compatibility with LocalOpenWeightProvider | Same HTTP boundary if server used | Engineering inference |
| CPU/iGPU suitability | Docs warn iGPUs with **&lt;80 EUs** may be too slow; Iris Xe path is **experimental until local benchmark** | Officially stated + requires local benchmark |
| Speed vs CPU | **Do not claim faster** until measured | Requires local benchmark |
| Risks | Driver/oneAPI complexity; shared-memory pressure; thermal laptop limits | Open |

### 3. llama.cpp Windows Vulkan

| Field | Finding | Evidence class |
|-------|---------|----------------|
| Project / publisher | ggml-org llama.cpp | Officially stated |
| Revision examined | b9968 `llama-b9968-bin-win-vulkan-x64.zip` (~31.4 MB) | Officially stated |
| Licence | MIT | Officially stated |
| Windows x64 / Vulkan | Build docs: `-DGGML_VULKAN=ON`; Windows Vulkan release published | Officially stated |
| Intel Iris Xe | Possible via Vulkan ICD; **not** claimed faster; suitability **requires local benchmark** | Engineering inference |
| Required drivers | Working Vulkan driver for Iris Xe | Engineering inference |
| Model-file control / GGUF / API | Same family as CPU server | Engineering inference |
| Selection | Deferred until after CPU baseline | Planning |

### 4. Ollama for Windows

| Field | Finding | Evidence class |
|-------|---------|----------------|
| Project / publisher | Ollama | Officially stated |
| Docs examined | https://docs.ollama.com/windows | Officially stated |
| Licence | MIT (GitHub ollama/ollama) | Officially stated |
| Windows x64 | Native Windows app; Win10 22H2+ or newer | Officially stated |
| GPU notes | Official docs emphasize NVIDIA and AMD; Intel Iris Xe path **not** a first-class documented target here | Officially stated / gap |
| Installation | `OllamaSetup.exe` (per-user) or standalone zip | Officially stated |
| Background service | **Runs in the background** after install; API on `http://localhost:11434` | Officially stated |
| Auto-start | Tray/app lifecycle; convenience over controlled one-shot process | Engineering inference |
| Model-storage control | Default `%HOMEPATH%\.ollama`; override `OLLAMA_MODELS` | Officially stated |
| Exact GGUF file control | Weaker than llama.cpp `-m` path; library/managed pull model | Engineering inference |
| Local API / OpenAI-compatible | REST API; OpenAI-compatible `/v1` commonly used | Officially stated / ecosystem |
| Uninstall | Windows Apps & features uninstaller; models may remain if custom `OLLAMA_MODELS` | Officially stated |
| LocalOpenWeightProvider fit | Possible via HTTP, but managed model naming differs | Engineering inference |
| Risks for first SIONA baseline | Background service, less exact artefact control, update coupling | Planning |

### 5. LM Studio

| Field | Finding | Evidence class |
|-------|---------|----------------|
| Project / publisher | LM Studio (Element Labs) | Officially stated |
| Docs examined | Developer server docs / REST quickstart | Officially stated |
| App licence | Proprietary desktop app (free for personal/internal use per product terms); **not** MIT for the app binary | Officially stated / product terms |
| CLI `lms` | Separate CLI ecosystem; do not conflate with app licence | Engineering inference |
| Local API | Default `http://localhost:1234`; OpenAI-compatible endpoints | Officially stated |
| Network exposure | Docs include “Serve on Local Network” option — must remain disabled for SIONA defaults | Officially stated |
| Model-file control | GUI/catalog mediated; less provenance-strict than explicit GGUF path | Engineering inference |
| Fit for first controlled baseline | Convenience only; weaker for SIONA provenance/rollback story | Planning |

### 6. OpenVINO GenAI

| Field | Finding | Evidence class |
|-------|---------|----------------|
| Project / publisher | Intel OpenVINO GenAI | Officially stated |
| Docs examined | OpenVINO 2026 GenAI install + inference docs | Officially stated |
| Windows package example | `openvino_genai_windows_2026.2.1.0_x86_64.zip` archive published | Officially stated |
| Devices | CPU and GPU selectable in pipelines | Officially stated |
| GGUF | Not the primary format; model conversion/IR workflow | Officially stated / ecosystem |
| HTTP OpenAI server | Not the same drop-in as llama-server; adapter work likely | Engineering inference |
| LocalOpenWeightProvider fit | Requires more SIONA adapter work than llama.cpp HTTP | Engineering inference |
| Role | Alternative Intel-optimized research path — deferred | Planning |

### 7. ONNX Runtime GenAI / WinML / DirectML

| Field | Finding | Evidence class |
|-------|---------|----------------|
| Project / publisher | Microsoft ONNX Runtime GenAI | Officially stated |
| Windows / DirectML | DirectML EP available for Windows GPU acceleration | Officially stated |
| Phi-4 ONNX | Microsoft publishes `Phi-4-mini-instruct-onnx` (official ONNX path) | Officially stated |
| GGUF | Not primary | Officially stated |
| LocalOpenWeightProvider fit | Different serving shape; more adapter work | Engineering inference |
| Role | Research/alternative for Microsoft ONNX artefacts — not first GGUF baseline | Planning |

---

## Provisional runtime recommendation

**Status: PROVISIONAL — REQUIRES OWNER APPROVAL BEFORE INSTALLATION**

### Primary first baseline

**llama.cpp native Windows x64 CPU build** (release family exemplified by **b9968** CPU zip).

### Possible later acceleration experiment

**llama.cpp Windows SYCL** on Intel Iris Xe (docs explicitly mention i7-1165G7-class iGPU support).  
**No speed advantage is claimed** until local benchmark.

### Convenience comparison (not first controlled baseline)

**Ollama for Windows** — strong DX, but background service + weaker exact-file provenance.

### Alternative Intel-optimized research path

**OpenVINO GenAI** — deferred until after HTTP/GGUF baseline exists.

### Why this ordering

1. **CPU before Iris Xe:** establishes a reproducible baseline without driver/oneAPI variables; SYCL remains experimental.
2. **Exact runtime and model-file control:** SIONA provenance requires known binary version + known GGUF digest + operator-controlled paths.
3. **No background service for first baseline:** reduces surprise auto-start and update coupling.
4. **Provider replaceability:** llama-server HTTP maps cleanly behind `LocalOpenWeightProvider` / `ModelGateway`.
5. **Convenience ≠ independence:** Ollama/LM Studio may be faster to demo, but do not improve SIONA architectural independence.

**No runtime is installed or finally approved by this document.**

---

## Model candidates

### Candidate A — Qwen3-1.7B

| Field | Value | Evidence class |
|-------|-------|----------------|
| Exact model repository | `Qwen/Qwen3-1.7B` | Officially stated |
| Exact quantized repository (publisher) | `Qwen/Qwen3-1.7B-GGUF` | Officially stated |
| Quantizer (publisher repo) | Qwen / Alibaba Cloud | Officially stated |
| Alternate Q4_K_M repository | `ggml-org/Qwen3-1.7B-GGUF` | Officially stated |
| Quantizer (alternate) | ggml-org | Officially stated |
| Original publisher / author | Qwen Team, Alibaba Cloud | Officially stated |
| Model family / architecture | Qwen3 dense causal LM | Officially stated |
| Parameter count | 1.7B (non-embedding 1.4B) | Officially stated |
| Training stage | Pretraining & post-training | Officially stated |
| Licence | Apache-2.0 | Officially stated |
| Commercial-use conditions | Apache-2.0 terms (attribution/NOTICE obligations) | Officially stated |
| File format | GGUF | Officially stated |
| **Preferred Q4_K_M on publisher repo** | **Not present** as of 2026-08-05 (publisher tree lists **Q8_0 only**) | Officially stated |
| Publisher artefact examined | `Qwen3-1.7B-Q8_0.gguf` — **1,834,426,016 bytes**; LFS SHA256 `061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a` | Officially stated |
| ggml-org Q4_K_M artefact | `Qwen3-1.7B-Q4_K_M.gguf` — **1,282,439,264 bytes**; LFS SHA256 `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5` | Officially stated |
| Context window | 32,768 native | Officially stated |
| Languages | 100+ claimed | Officially stated |
| Tool-use / structured-output claims | Agent/tool capabilities claimed; SIONA must still treat tool calls as advisory | Officially stated + SIONA policy |
| Thinking mode | Yes; disable via `enable_thinking=False` / `/no_think` | Officially stated |
| Sampling warnings | Avoid greedy in thinking mode; consider `presence_penalty` ~1.5 on quants to reduce repetition | Officially stated |
| Estimated RAM (weights + overhead) | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT (Q4_K_M ~2–4 GiB class; Q8_0 higher) | Estimate |
| KV-cache @ 2k/4k/8k | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT | Estimate |
| Disk footprint | ~1.19 GiB (ggml Q4_K_M) or ~1.71 GiB (publisher Q8_0) + runtime | Calculated from published sizes |
| CPU suitability | Good for first integration on 4C/8T | Engineering inference |
| Expected latency | **unknown until benchmark** (likely moderate on CPU) | Requires local benchmark |
| Provenance risk | **Low** for publisher Q8_0; **moderate** for ggml-org Q4_K_M (quantizer ≠ publisher) | Planning |
| Licence risk | Low (Apache-2.0) | Officially stated |
| Runtime-maturity risk | Low on llama.cpp for Qwen3 | Engineering inference |
| Local evaluation status | Not evaluated | |
| Selection status | **Not selected / not downloaded** | |

### Candidate B — Qwen3-4B

| Field | Value | Evidence class |
|-------|-------|----------------|
| Exact model repository | `Qwen/Qwen3-4B` | Officially stated |
| Exact quantized repository | `Qwen/Qwen3-4B-GGUF` | Officially stated |
| Quantizer | Qwen / Alibaba Cloud | Officially stated |
| Parameters | 4.0B (non-embedding 3.6B) | Officially stated |
| Licence | Apache-2.0 | Officially stated |
| Exact quant | **Q4_K_M present officially** | Officially stated |
| Exact file name | `Qwen3-4B-Q4_K_M.gguf` | Officially stated |
| Published size | **2,497,280,256 bytes** (~2.33 GiB) | Officially stated |
| Published SHA256 (LFS oid) | `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5` | Officially stated |
| Context | 32,768 native; YaRN to 131,072 | Officially stated |
| Thinking / `/no_think` | Same family behaviour as 1.7B | Officially stated |
| CPU suitability | Feasible but heavier than 1.7B on 16 GiB laptop | Engineering inference |
| Expected latency | **unknown until benchmark** (likely higher than 1.7B) | Requires local benchmark |
| Provenance risk | Low (publisher GGUF) | Officially stated |
| Selection status | **Deferred until after smaller baseline** | Planning |

### Candidate C — IBM Granite 4.0 Micro (instruct) GGUF

| Field | Value | Evidence class |
|-------|-------|----------------|
| Exact model repository | `ibm-granite/granite-4.0-micro` | Officially stated |
| Exact quantized repository | `ibm-granite/granite-4.0-micro-GGUF` | Officially stated |
| Quantizer | IBM Granite / IBM GGUF conversion pipeline (`IBM/gguf`) | Officially stated |
| Architecture | Dense Transformer (card); GGUF lists architecture `granite`; ~**3B** params | Officially stated |
| Licence | Apache-2.0 | Officially stated |
| Exact quant | `granite-4.0-micro-Q4_K_M.gguf` | Officially stated |
| Published size | **2,099,502,528 bytes** (~1.96 GiB) | Officially stated |
| Published SHA256 (LFS oid) | `97c417dcc0534b0737c74016fb2af083cb17c3b51eaac621192d23961b7024eb` | Officially stated |
| Capabilities claimed | IF, tool-calling, RAG, multilingual, FIM | Officially stated |
| CPU suitability | Similar class to 3–4B; feasible with care | Engineering inference |
| Expected latency | **unknown until benchmark** | Requires local benchmark |
| Provenance risk | Low (official IBM GGUF) | Officially stated |
| Selection status | **Comparison candidate — not first baseline** | Planning |

### Candidate D — Microsoft Phi-4-mini-instruct

| Field | Value | Evidence class |
|-------|-------|----------------|
| Exact model repository | `microsoft/Phi-4-mini-instruct` | Officially stated |
| Licence | **MIT** | Officially stated |
| Parameter class | Lightweight Phi-4 mini; context up to 128K claimed | Officially stated |
| Official GGUF from Microsoft | **Not published** as a first-party GGUF repo on access date | Officially stated / gap |
| Official ONNX | `microsoft/Phi-4-mini-instruct-onnx` exists | Officially stated |
| llama.cpp support | Architecture support landed in llama.cpp history | Officially stated (commits) |
| Community GGUF | e.g. bartowski quantizations — **quantizer ≠ Microsoft** | Officially stated (third party) |
| Provenance risk if using community GGUF | **Higher** — must record quantizer + checksum; not preferred for first gate | Planning |
| 3.8B-class laptop fit | Feasible in principle; still needs RAM/latency measurement | Engineering inference |
| Selection status | **Deferred** unless using official ONNX/ORT path under a separate plan | Planning |

### Candidate E — Qwen/Qwen3.5-2B (research-only)

| Field | Value | Evidence class |
|-------|-------|----------------|
| Exact model repository | `Qwen/Qwen3.5-2B` | Officially stated |
| Modality | **Multimodal** (`pipeline_tag: image-text-to-text`); native vision-language | Officially stated |
| Licence | Apache-2.0 | Officially stated |
| Official publisher GGUF | Not established as first-party GGUF on access date; community GGUFs exist | Gap / third party |
| llama.cpp maturity | Newer `qwen35` architecture; maturity risk higher than Qwen3 text | Engineering inference |
| Appropriateness for first Phase 3B baseline | **No** — multimodal + newer stack adds integration risk without benefit for text provider gate | Planning |
| Selection status | **Research-only — not a first baseline** | |

---

## Provisional first-model recommendation

**Status: PROVISIONAL — NO MODEL DOWNLOAD AUTHORIZED**

### Primary first integration candidate

**Qwen3-1.7B** for transport and integration validation.

Because `Qwen/Qwen3-1.7B-GGUF` does **not** publish Q4_K_M as of 2026-08-05, the evidence-based artefact choices are:

1. **Provenance-preferred:** `Qwen3-1.7B-Q8_0.gguf` from `Qwen/Qwen3-1.7B-GGUF`  
2. **Size/quant-preferred (requested Q4_K_M):** `Qwen3-1.7B-Q4_K_M.gguf` from `ggml-org/Qwen3-1.7B-GGUF` with quantizer explicitly recorded as **ggml-org**

Owner approval must choose which artefact path to authorize later.

### Second capability candidate

**Qwen3-4B Q4_K_M** from official `Qwen/Qwen3-4B-GGUF` — only after the 1.7B path validates end-to-end.

### Additional comparison

**IBM Granite 4.0 Micro Q4_K_M** (`ibm-granite/granite-4.0-micro-GGUF`).

### Why this ordering

- **1.7B** is small enough to validate loopback transport, sanitization, registry provenance and fallback without saturating a 16 GiB laptop.
- It is **not** claimed as SIONA’s permanent reasoning model.
- **4B** adds capability headroom only after the smaller path is measured.
- **SIONA evaluations** (not publisher blogs) decide quality acceptance.
- Published benchmark claims are **insufficient** for SIONA acceptance.
- External weights remain **replaceable** behind `ModelGateway` and are **not** SIONA’s identity.

---

## Alternatives rejected or deferred

| Option | Disposition | Reason |
|--------|-------------|--------|
| Ollama as first baseline | Deferred | Background service; weaker exact-file control |
| LM Studio as first baseline | Deferred | Proprietary app; network-serve option; weaker provenance story |
| OpenVINO / ORT GenAI first | Deferred | Format/adapter mismatch vs current LocalOpenWeightProvider HTTP/GGUF path |
| llama.cpp SYCL first | Deferred | Experimental until CPU baseline + local benchmark |
| Phi-4 community GGUF first | Deferred | Quantizer provenance risk; prefer official ONNX path only under separate plan |
| Qwen3.5-2B first | Rejected for first gate | Multimodal + newer architecture complexity |

## Open questions

1. Exact `llama-server` flags for bind address, timeouts, grammar and cancellation on the chosen bXXXX binary.
2. Measured free-RAM before load vs preferred 6–8 GiB target.
3. Measured tokens/s and thermal behaviour on i7-1165G7 CPU and optional SYCL.
4. Whether owner prefers publisher Q8_0 or ggml-org Q4_K_M for the first 1.7B artefact.
5. Confirm `winver` OS edition before install (WMI fields may be stale).

## Related documents

- [PHASE_3B_HARDWARE_INVENTORY.md](PHASE_3B_HARDWARE_INVENTORY.md)
- [PHASE_3B_MODEL_INDEPENDENCE.md](PHASE_3B_MODEL_INDEPENDENCE.md)
- [PHASE_3B_INSTALLATION_RUNBOOK.md](PHASE_3B_INSTALLATION_RUNBOOK.md)
- [adr/0003-first-local-model-strategy.md](adr/0003-first-local-model-strategy.md)
