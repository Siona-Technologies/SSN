# Phase 3B — Model and Runtime Research

**Status:** Official-source research matrix completed; first baseline is
**INSTALLED AND ARTIFACT-VERIFIED LOCALLY; LIMITED LOOPBACK EXECUTION COMPLETED**;
`openai_chat` transport implemented; controlled real SIONA provider text path
validated (EXP-3B-005); runtime currently **stopped**.

**Source-access date:** 2026-08-05  
**Hardware baseline:** HP EliteBook 840 G8; Intel i7-1165G7 (4C/8T); Intel Iris Xe; ~15.73 GiB RAM; no CUDA  

**Non-authorization:** This document does **not** authorize ADR acceptance,
Phase 3B completion, Phase 4, or automatic/permanent model startup. Gate E
breadth is recorded (EXP-3B-011). Model-registry activation review passed with
conservative capability binding (EXP-3B-012: registry record available; exact
binding software supported). A controlled real-runtime verification through that
registry-bound path (state C) was verified under EXP-3B-013 and the runtime was
shut down afterward; STATE C DOES NOT MEAN AUTOMATIC OR PERMANENT MODEL STARTUP.

## Research status

| Item | Status |
|------|--------|
| Official-source runtime research | **Completed with full field coverage** (2026-08-05) |
| Official-source model research | **Completed with full field coverage** (2026-08-05) |
| Source revisions pinned | **Yes** (see Source traceability appendix) |
| Owner-approved first baseline | **Recorded** |
| Runtime installation | **Completed locally (operator evidence)** |
| Model download | **Completed locally (operator evidence)** |
| Local SHA256 verification | **MATCH for runtime archive and model** |
| Limited loopback execution | **Completed; runtime currently stopped** |
| openai_chat provider transport | **Implemented (merged)** |
| Controlled real SIONA provider text path (EXP-3B-005) | **Validated; limited text-transport gate only** |
| Exact `/v1/models` model-ID verification | **Succeeded** |
| Direct provider text (no fallback) | **Succeeded** |
| LanguageEngine → real local provider | **Succeeded** |
| Deterministic fallback after shutdown | **Verified** |
| Structured JSON probe | **Observed failure; capability remains unverified** |
| Model registry | **Record available; binding software supported (EXP-3B-012); State C real-runtime verification PASSED (EXP-3B-013); runtime currently stopped** |
| Gate E governed evaluation | **Recorded (EXP-3B-011)** — safety 8/8; runtime R01–R07 passed; timeout/cancellation evaluated; streaming evaluated as UNSUPPORTED_ON_PINNED_BASELINE; native JSON NOT_VERIFIED |
| Bounded text/chat capability | **Conservatively verified** at locally tested 4096 context (chat=true in registry) |
| Native JSON / structured_json | **Evaluated; NOT_VERIFIED; disabled in registry (false)** |
| Streaming | **Evaluated; UNSUPPORTED_ON_PINNED_BASELINE; disabled in registry (false)** |
| Tools / multimodal | **Disabled in registry (false); multimodal unverified** |
| Real-model production evaluation | **Not started** |
| Registry-bound real-runtime verification (state C) | **PASSED** (EXP-3B-013) — temporary loopback verification; runtime shut down |
| ADR 0003 | **Proposed** |
| Phase 3B | **In progress** |
| Phase 4 | **Not started** |

## Owner-approved first baseline

**Prior status wording (selection gate):** OWNER-APPROVED FOR PRE-INSTALLATION
VERIFICATION ONLY

**Current local-evidence wording:** INSTALLED AND ARTIFACT-VERIFIED LOCALLY;
LIMITED LOOPBACK EXECUTION COMPLETED; CONTROLLED REAL-PROVIDER TEXT PATH
VALIDATED (EXP-3B-005); RUNTIME CURRENTLY STOPPED

| Item | Exact recorded value |
|------|----------------------|
| Runtime family | llama.cpp |
| Runtime release | b9968 |
| Runtime source revision | `1d1d9a9ed7a4f09c4225ea4cc8fd3bd1cf2c940f` |
| Runtime platform | Windows x64 CPU-only |
| Expected runtime archive | `llama-b9968-bin-win-cpu-x64.zip` |
| Model family | Qwen3-1.7B |
| Model artifact | `Qwen3-1.7B-Q4_K_M.gguf` |
| Model repository | `ggml-org/Qwen3-1.7B-GGUF` |
| Model repository revision | `daeb8e2d528a760970442092f6bf1e55c3b659eb` |
| Expected model size | 1282439264 bytes |
| Expected model SHA256 | `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5` |
| Original model publisher | Qwen Team / Alibaba Cloud |
| Quantizer | ggml-org |
| Model licence | Apache License 2.0 |
| Purpose | Transport, integration, safety, provenance, rollback and baseline-performance validation only |

### Local operator evidence (2026-08-05)

This subsection is **local operator evidence**, not a claim that GitHub
independently verified installation.

- Runtime archive `llama-b9968-bin-win-cpu-x64.zip`: 18211732 bytes; locally
  calculated SHA256
  `f98e6690faad6a8718451d420a63cbfde6c87028beae4e7f35a36a762730cefd` — **MATCH**
- Portable extract to `C:\Users\njaji\SIONA\runtimes\llama.cpp\b9968` with
  `llama-server.exe` / `llama-cli.exe` present; MIT licence copy preserved
- Model `Qwen3-1.7B-Q4_K_M.gguf`: 1282439264 bytes; locally calculated SHA256
  `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5` — **MATCH**
- Model directory `C:\Users\njaji\SIONA\models\Qwen3-1.7B-Q4_K_M`; Apache-2.0
  licence copy preserved; quantizer remains **ggml-org**
- CPU-only loopback run on `127.0.0.1:8080` loaded the model and generated text
  for short probes; runtime is **currently stopped**; port 8080 not listening
- Controlled real SIONA provider text path validated in **EXP-3B-005**
  (`LanguageEngine` → `ModelGateway` → `LocalOpenWeightProvider` → llama.cpp →
  Qwen): exact `/v1/models` model-ID verification succeeded; direct provider
  text succeeded without fallback; LanguageEngine reached the real local
  provider; tool proposals remained absent
- Deterministic fallback verified after shutdown
- Structured JSON probe **observed failure**; structured JSON capability remains
  **unverified**
- Short probes alone are **insufficient** for production capability claims;
  Gate E (EXP-3B-011) later recorded broader evidence with conservative limits
- Registry record availability and exact binding software support are complete
  under EXP-3B-012. A controlled real-runtime verification through that
  registry-bound path (state C) PASSED under EXP-3B-013 then shut down. Model registry runtime remains inactive at steady state
  until that separate authorized experiment. Further provider integration
  campaigns beyond the recorded conservative registry binding remain
  unauthorized until explicitly approved.
- The model remains external, optional and replaceable; **not** SIONA-native
- No tool capability is approved; no production recommendation is issued

Selection notes:

- Q4_K_M was selected for the first integration because of the laptop's RAM,
  storage and CPU constraints.
- The Q4_K_M quantization is from **ggml-org**, not the Qwen publisher.
- The original model remains Qwen3-1.7B by Qwen Team.
- The selection prioritizes controlled integration and lower memory use.
- Publisher Q8_0 remains a possible later comparison.
- Qwen3-4B and Granite remain later comparison candidates.
- The first baseline is replaceable behind `ModelGateway`.
- Verified registry behaviour is limited to bounded text/chat at 4096 context;
  tools, structured_json, streaming and multimodal remain false.
- ADR acceptance still requires separate explicit authorization.

This is **not** SIONA's permanent reasoning model, a final production model, a
SIONA-native model, or a capability-approved model. The selected baseline is
locally installed and artifact-verified; the controlled text path was validated;
the runtime is currently stopped.

## Preserved later candidates (not authorized)

- **Later experiment:** llama.cpp SYCL
- **Publisher Q8_0 comparison:** `Qwen/Qwen3-1.7B-GGUF` Q8_0
- **Second candidate:** Qwen3-4B Q4_K_M
- **Comparison candidate:** IBM Granite 4.0 Micro Q4_K_M

## Evidence classes

Use only: **Officially stated**; calculated estimate; engineering inference;
NOT APPLICABLE; NOT OFFICIALLY DOCUMENTED; UNKNOWN; REQUIRES INSTALL-TIME
VERIFICATION; REQUIRES LOCAL BENCHMARK; ENGINEERING ESTIMATE — REQUIRES LOCAL
MEASUREMENT.

Do not convert unknowns into engineering facts. Do not fabricate tokens/s.

---

## Runtime comparisons

### 1. llama.cpp native Windows CPU

| Field | Value |
|-------|-------|
| Project | llama.cpp |
| Publisher | ggml-org |
| Exact release, version, tag or revision examined | Tag **b9968**; corresponding commit `1d1d9a9ed7a4f09c4225ea4cc8fd3bd1cf2c940f` (Officially stated via GitHub release API) |
| Source-access date | 2026-08-05 |
| Exact official source references | https://github.com/ggml-org/llama.cpp/releases/tag/b9968; docs/build.md; LICENSE (MIT) |
| Licence | MIT — Copyright (c) 2023–2026 The ggml authors (Officially stated) |
| Windows x64 support | Yes — asset `llama-b9968-bin-win-cpu-x64.zip` (Officially stated) |
| Minimum Windows requirement | NOT OFFICIALLY DOCUMENTED as a single minimum Windows SKU in examined release notes; build docs assume Visual Studio 2022 |
| CPU support | Yes — default CPU build (Officially stated) |
| AVX2 requirement | Tiger Lake expected AVX2; whether the exact release binary requires AVX2 at runtime: REQUIRES LOCAL BENCHMARK |
| Intel Iris Xe support | NOT APPLICABLE for CPU-only path |
| Whether i7-1165G7 is explicitly documented | NOT APPLICABLE for CPU-only path |
| Required drivers | None beyond the operating system for CPU-only path |
| Required toolchains | None for prebuilt zip; Visual Studio 2022 + CMake if building from source (Officially stated in build docs) |
| Installation mechanism | Download official release zip or build from source (Officially stated) |
| Portable extraction availability | Yes — portable zip extraction (Officially stated) |
| Published installation/download footprint | ~17.4 MB published GitHub asset size for `llama-b9968-bin-win-cpu-x64.zip` (Officially stated) |
| Background-process or service behaviour | No installer service; operator starts `llama-server` / CLI manually |
| Auto-start behaviour | None by default |
| Update behaviour | Manual re-download / replace with a newer release tag |
| Model-storage control | Operator-chosen filesystem directory for GGUF files |
| Exact model-file control | Yes — explicit GGUF path (`-m`) (Officially stated) |
| GGUF support | Yes (Officially stated) |
| ONNX support | Not the primary path |
| Quantization support | GGUF quantization formats (Officially stated) |
| Local HTTP API | Yes — `llama-server` HTTP API (Officially stated) |
| Default bind host | Default intent `127.0.0.1` — confirm with `--help` on exact binary: REQUIRES INSTALL-TIME VERIFICATION |
| Default port | Default intent `8080` — confirm with `--help` on exact binary: REQUIRES INSTALL-TIME VERIFICATION |
| Explicit loopback binding | Bind host to loopback for SIONA baseline; do not use `0.0.0.0` |
| OpenAI-compatible endpoint | Yes — OpenAI-compatible routes in the llama-server family (Officially stated) |
| Structured JSON or grammar support | Grammar / constrained decoding supported in llama.cpp ecosystem (Officially stated) |
| Streaming support | Yes (Officially stated) |
| Cancellation behaviour | REQUIRES INSTALL-TIME VERIFICATION against b9968 `--help` |
| Request timeout controls | REQUIRES INSTALL-TIME VERIFICATION against b9968 `--help` |
| Maximum-output controls | REQUIRES INSTALL-TIME VERIFICATION against b9968 `--help` |
| Logging | Console/stderr; file logging details REQUIRES INSTALL-TIME VERIFICATION |
| Authentication | No first-class authentication gateway; treat as unauthenticated local process |
| Remote-exposure controls | Controlled by bind host/port; keep loopback-only |
| Uninstall method | Delete the extract directory |
| Rollback method | Restore a prior extract / remove binaries; SIONA Core remains unchanged |
| LocalOpenWeightProvider compatibility | Strong fit for HTTP loopback + exact model path/ID |
| Required SIONA adapter changes | Likely request/response mapping only; no gateway redesign |
| CPU suitability on i7-1165G7 | Suitable for small models on 4C/8T; latency REQUIRES LOCAL BENCHMARK |
| Iris Xe path | NOT APPLICABLE (CPU baseline) |
| Risks | Endpoint schema drift vs SIONA transport; no tokens/s claim |
| Unresolved questions | Initial binary flags were inspected during the owner-authorized baseline run; future governed execution must revalidate required flags before startup |
| Selection status | **Historical provisional primary baseline at research gate; now locally installed/verified (runtime stopped)** |

### 2. llama.cpp Windows SYCL

| Field | Value |
|-------|-------|
| Project | llama.cpp (SYCL backend) |
| Publisher | ggml-org |
| Exact release, version, tag or revision examined | Tag **b9968**; commit `1d1d9a9ed7a4f09c4225ea4cc8fd3bd1cf2c940f`; asset `llama-b9968-bin-win-sycl-x64.zip` |
| Source-access date | 2026-08-05 |
| Exact official source references | https://github.com/ggml-org/llama.cpp docs/backend/SYCL.md; release tag b9968 |
| Licence | MIT (Officially stated) |
| Windows x64 support | Yes — `llama-b9968-bin-win-sycl-x64.zip` (Officially stated) |
| Minimum Windows requirement | Windows 11 listed as a verified OS in SYCL.md (Officially stated) |
| CPU support | Host CPU participates; device offload via SYCL (Officially stated) |
| AVX2 requirement | REQUIRES LOCAL BENCHMARK |
| Intel Iris Xe support | Yes — Intel iGPU / Level Zero path documented (Officially stated) |
| Whether i7-1165G7 is explicitly documented | Yes — SYCL.md lists **i7-1165G7** among iGPU examples (Officially stated) |
| Required drivers | Intel GPU driver; release notes note oneAPI DLL dependencies with the zip (Officially stated) |
| Required toolchains | oneAPI/icx for source builds; prebuilt zip reduces toolchain need |
| Installation mechanism | Download SYCL release zip or build with `-DGGML_SYCL=ON` (Officially stated) |
| Portable extraction availability | Yes — zip extract |
| Published installation/download footprint | ~110.1 MB published asset size for `llama-b9968-bin-win-sycl-x64.zip` (Officially stated) |
| Background-process or service behaviour | No installer service by default |
| Auto-start behaviour | None by default |
| Update behaviour | Manual release replacement |
| Model-storage control | Operator-chosen GGUF directory |
| Exact model-file control | Yes — explicit GGUF path |
| GGUF support | Yes (Officially stated) |
| ONNX support | Not the primary path |
| Quantization support | GGUF |
| Local HTTP API | Same llama-server family as CPU |
| Default bind host | Default intent `127.0.0.1` — REQUIRES INSTALL-TIME VERIFICATION |
| Default port | Default intent `8080` — REQUIRES INSTALL-TIME VERIFICATION |
| Explicit loopback binding | Bind loopback for SIONA |
| OpenAI-compatible endpoint | Same server family capability |
| Structured JSON or grammar support | Same grammar capability family |
| Streaming support | Yes |
| Cancellation behaviour | REQUIRES INSTALL-TIME VERIFICATION |
| Request timeout controls | REQUIRES INSTALL-TIME VERIFICATION |
| Maximum-output controls | REQUIRES INSTALL-TIME VERIFICATION |
| Logging | Console; details REQUIRES INSTALL-TIME VERIFICATION |
| Authentication | Unauthenticated local process by default |
| Remote-exposure controls | Bind-host controlled |
| Uninstall method | Delete extract directory |
| Rollback method | Remove SYCL binaries; fall back to CPU zip |
| LocalOpenWeightProvider compatibility | Compatible if HTTP server used |
| Required SIONA adapter changes | Same as CPU path if API surface identical |
| CPU suitability on i7-1165G7 | Still usable; device offload experimental |
| Iris Xe path | Experimental — docs warn iGPUs with <80 EUs may be too slow; **no speed claim** until local benchmark (Officially stated warning + REQUIRES LOCAL BENCHMARK) |
| Risks | Driver/oneAPI complexity; shared memory; laptop thermals |
| Unresolved questions | Local SYCL versus CPU benchmark outstanding |
| Selection status | **Later experiment only — not approved** |
### 3. llama.cpp Windows Vulkan

| Field | Value |
|-------|-------|
| Project | llama.cpp (Vulkan backend) |
| Publisher | ggml-org |
| Exact release, version, tag or revision examined | Tag **b9968**; commit `1d1d9a9ed7a4f09c4225ea4cc8fd3bd1cf2c940f`; asset `llama-b9968-bin-win-vulkan-x64.zip` |
| Source-access date | 2026-08-05 |
| Exact official source references | docs/build.md Vulkan section; release b9968 assets |
| Licence | MIT (Officially stated) |
| Windows x64 support | Yes — `llama-b9968-bin-win-vulkan-x64.zip` (Officially stated) |
| Minimum Windows requirement | NOT OFFICIALLY DOCUMENTED as a single minimum Windows SKU in examined notes |
| CPU support | Host CPU present; GPU via Vulkan |
| AVX2 requirement | REQUIRES LOCAL BENCHMARK |
| Intel Iris Xe support | Possible via Intel Vulkan ICD — suitability REQUIRES LOCAL BENCHMARK |
| Whether i7-1165G7 is explicitly documented | NOT OFFICIALLY DOCUMENTED specifically for the Vulkan path in examined docs |
| Required drivers | Working Vulkan driver for Iris Xe |
| Required toolchains | Vulkan SDK if building from source; prebuilt zip available |
| Installation mechanism | Download Vulkan zip or build `-DGGML_VULKAN=ON` (Officially stated) |
| Portable extraction availability | Yes |
| Published installation/download footprint | ~31.4 MB published asset size for `llama-b9968-bin-win-vulkan-x64.zip` (Officially stated) |
| Background-process or service behaviour | No installer service by default |
| Auto-start behaviour | None by default |
| Update behaviour | Manual release replacement |
| Model-storage control | Operator-chosen path |
| Exact model-file control | Yes — GGUF path |
| GGUF support | Yes |
| ONNX support | Not the primary path |
| Quantization support | GGUF |
| Local HTTP API | llama-server family |
| Default bind host | Default intent `127.0.0.1` — REQUIRES INSTALL-TIME VERIFICATION |
| Default port | Default intent `8080` — REQUIRES INSTALL-TIME VERIFICATION |
| Explicit loopback binding | Bind loopback |
| OpenAI-compatible endpoint | Server family capability |
| Structured JSON or grammar support | Grammar family capability |
| Streaming support | Yes |
| Cancellation behaviour | REQUIRES INSTALL-TIME VERIFICATION |
| Request timeout controls | REQUIRES INSTALL-TIME VERIFICATION |
| Maximum-output controls | REQUIRES INSTALL-TIME VERIFICATION |
| Logging | REQUIRES INSTALL-TIME VERIFICATION |
| Authentication | Unauthenticated local process by default |
| Remote-exposure controls | Bind-host controlled |
| Uninstall method | Delete extract directory |
| Rollback method | Remove Vulkan binaries; keep CPU baseline |
| LocalOpenWeightProvider compatibility | Compatible if HTTP used |
| Required SIONA adapter changes | Same HTTP mapping if API matches |
| CPU suitability on i7-1165G7 | CPU fallback always available |
| Iris Xe path | Experimental Vulkan iGPU path — **no speed claim** (REQUIRES LOCAL BENCHMARK) |
| Risks | Driver variance; unknown Iris Xe gain |
| Unresolved questions | Local Vulkan benchmark outstanding |
| Selection status | **Deferred after CPU baseline — not approved** |

### 4. Ollama for Windows

| Field | Value |
|-------|-------|
| Project | Ollama |
| Publisher | Ollama |
| Exact release, version, tag or revision examined | Release tag **v0.32.5** (published 2026-07-27); commit `eec8e0b9458b8a01be0c216a9cc53eefde24ef50` |
| Source-access date | 2026-08-05 |
| Exact official source references | https://docs.ollama.com/windows (UNVERSIONED OFFICIAL DOCUMENTATION — ACCESSED 2026-08-05); https://github.com/ollama/ollama |
| Licence | MIT for the ollama/ollama project repository (Officially stated) |
| Windows x64 support | Yes — native Windows application (Officially stated) |
| Minimum Windows requirement | Windows 10 22H2 or newer (Home or Pro) per official Windows docs (Officially stated) |
| CPU support | Yes (Officially stated) |
| AVX2 requirement | NOT OFFICIALLY DOCUMENTED as an explicit hard requirement in examined Windows docs |
| Intel Iris Xe support | NOT OFFICIALLY DOCUMENTED as a first-class target; docs emphasize NVIDIA/AMD |
| Whether i7-1165G7 is explicitly documented | NOT OFFICIALLY DOCUMENTED |
| Required drivers | NVIDIA/AMD when using those GPUs; Intel path NOT OFFICIALLY DOCUMENTED |
| Required toolchains | None for the installer path |
| Installation mechanism | `OllamaSetup.exe` or standalone `ollama-windows-amd64.zip` (Officially stated) |
| Portable extraction availability | Partial — standalone zip exists; installer is the primary path |
| Published installation/download footprint | Installer guidance cites ≥4GB free for binary install; model storage additional (Officially stated) |
| Background-process or service behaviour | **Runs in the background** after install; API served continuously (Officially stated) |
| Auto-start behaviour | Tray/app lifecycle — convenience auto-running behaviour |
| Update behaviour | Installer helps keep the application up to date (Officially stated) |
| Model-storage control | Default `%HOMEPATH%\.ollama`; override with `OLLAMA_MODELS` (Officially stated) |
| Exact model-file control | Weaker than explicit GGUF `-m` path; library/managed model names |
| GGUF support | Uses GGUF internally / import paths; managed library abstraction |
| ONNX support | Not the primary path |
| Quantization support | Managed quant variants via library |
| Local HTTP API | Yes — REST API (Officially stated) |
| Default bind host | localhost / loopback in documentation examples (Officially stated) |
| Default port | 11434 (Officially stated) |
| Explicit loopback binding | Default documented API is localhost; remote exposure is not preferred for SIONA |
| OpenAI-compatible endpoint | OpenAI-compatible `/v1` commonly used (Officially stated / ecosystem) |
| Structured JSON or grammar support | Model-dependent; structured behaviour REQUIRES LOCAL BENCHMARK |
| Streaming support | Yes |
| Cancellation behaviour | REQUIRES INSTALL-TIME VERIFICATION |
| Request timeout controls | REQUIRES INSTALL-TIME VERIFICATION |
| Maximum-output controls | REQUIRES INSTALL-TIME VERIFICATION |
| Logging | `%LOCALAPPDATA%\Ollama` logs (`app.log`, `server.log`) (Officially stated) |
| Authentication | Local API typically unauthenticated |
| Remote-exposure controls | Can be configured; keep local-only for SIONA |
| Uninstall method | Windows Apps & features uninstaller; custom `OLLAMA_MODELS` may remain |
| Rollback method | Uninstall + delete model directory; SIONA Core unchanged |
| LocalOpenWeightProvider compatibility | Possible via HTTP, but model naming differs from exact GGUF path |
| Required SIONA adapter changes | Mapping + model-id translation likely |
| CPU suitability on i7-1165G7 | Feasible; exact latency REQUIRES LOCAL BENCHMARK |
| Iris Xe path | NOT OFFICIALLY DOCUMENTED / uncertain for Iris Xe |
| Risks | Background service; weaker exact artefact control; update coupling |
| Unresolved questions | Whether Intel Iris Xe acceleration is usable on this laptop |
| Selection status | **Convenience comparison — deferred as first controlled baseline** |

### 5. LM Studio

| Field | Value |
|-------|-------|
| Project | LM Studio Desktop App |
| Publisher | Element Labs, Inc. |
| Exact release, version, tag or revision examined | App Terms of Service **Version: July 1, 2025** (https://lmstudio.ai/terms); developer server docs: UNVERSIONED OFFICIAL DOCUMENTATION — ACCESSED 2026-08-05 |
| Source-access date | 2026-08-05 |
| Exact official source references | https://lmstudio.ai/terms; https://lmstudio.ai/docs/developer/core/server; https://lmstudio.ai/docs/developer/rest/quickstart |
| Licence | Proprietary desktop App Terms (not MIT). Licence grant examined: non-exclusive, non-transferable use for **personal and/or internal business purposes** only. Restrictions examined include no redistribution of the Software; no service-bureau / ASP / SaaS transfer of Software functionality; no reverse engineering except as legally required. Embedding/redistribution edge cases: **REQUIRES LEGAL REVIEW**. Do not conflate App Terms with any separately licensed CLI. |
| Windows x64 support | Yes (desktop app) |
| Minimum Windows requirement | See Certified System Requirements (may change); exact minimum REQUIRES INSTALL-TIME VERIFICATION against https://lmstudio.ai/docs/system-requirements |
| CPU support | Yes |
| AVX2 requirement | NOT OFFICIALLY DOCUMENTED in examined terms/server pages |
| Intel Iris Xe support | NOT OFFICIALLY DOCUMENTED in examined pages |
| Whether i7-1165G7 is explicitly documented | NOT OFFICIALLY DOCUMENTED |
| Required drivers | GPU-dependent; specifics NOT OFFICIALLY DOCUMENTED here |
| Required toolchains | None for app install |
| Installation mechanism | Official desktop installer from lmstudio.ai |
| Portable extraction availability | NOT OFFICIALLY DOCUMENTED as a first-class portable extract for the app |
| Published installation/download footprint | NOT OFFICIALLY DOCUMENTED as a single published byte size in examined pages |
| Background-process or service behaviour | Local API server started via Developer tab / `lms server start` (Officially stated) |
| Auto-start behaviour | Operator-controlled server toggle; app persistence REQUIRES INSTALL-TIME VERIFICATION |
| Update behaviour | App update channel — REQUIRES INSTALL-TIME VERIFICATION |
| Model-storage control | App/catalog mediated storage |
| Exact model-file control | Weaker than explicit operator-owned GGUF path |
| GGUF support | Yes (loads GGUF models) (Officially stated) |
| ONNX support | NOT OFFICIALLY DOCUMENTED as primary in examined pages |
| Quantization support | Catalog/quant variants |
| Local HTTP API | Yes (Officially stated) |
| Default bind host | localhost by default; docs also document Serve on Local Network (Officially stated) |
| Default port | 1234 (Officially stated) |
| Explicit loopback binding | Default localhost; network serve must remain disabled for SIONA |
| OpenAI-compatible endpoint | Yes — OpenAI-compatible endpoints (Officially stated) |
| Structured JSON or grammar support | Model/API dependent — REQUIRES LOCAL BENCHMARK |
| Streaming support | Yes |
| Cancellation behaviour | REQUIRES INSTALL-TIME VERIFICATION |
| Request timeout controls | REQUIRES INSTALL-TIME VERIFICATION |
| Maximum-output controls | REQUIRES INSTALL-TIME VERIFICATION |
| Logging | App/developer logging — REQUIRES INSTALL-TIME VERIFICATION |
| Authentication | Optional API token in server settings (default may be none) — REQUIRES INSTALL-TIME VERIFICATION |
| Remote-exposure controls | Explicit local-network serve option exists — keep disabled |
| Uninstall method | OS uninstall of desktop app + remove model cache |
| Rollback method | Uninstall app; delete models; SIONA Core unchanged |
| LocalOpenWeightProvider compatibility | Possible via OpenAI-compatible HTTP; weaker provenance story |
| Required SIONA adapter changes | Base URL/path mapping; model-id mapping |
| CPU suitability on i7-1165G7 | Feasible; latency REQUIRES LOCAL BENCHMARK |
| Iris Xe path | UNKNOWN / NOT OFFICIALLY DOCUMENTED |
| Risks | Proprietary terms; network-serve option; weaker artefact control |
| Unresolved questions | Legal review if redistribution/embedding ever considered |
| Selection status | **Deferred — not first controlled baseline** |
### 6. OpenVINO GenAI

| Field | Value |
|-------|-------|
| Project | OpenVINO GenAI |
| Publisher | Intel / OpenVINO Toolkit |
| Exact release, version, tag or revision examined | openvino.genai release tag **2026.3.0.0** (published 2026-08-05); install guides also reference 2026.2.1 Windows package naming |
| Source-access date | 2026-08-05 |
| Exact official source references | https://docs.openvino.ai/2026/get-started/install-openvino/install-openvino-genai.html; GenAI inference docs; GitHub openvinotoolkit/openvino.genai |
| Licence | Intel OpenVINO licensing — confirm exact licence/NOTICE text in the chosen archive at install time (REQUIRES INSTALL-TIME VERIFICATION) |
| Windows x64 support | Yes — Windows x86_64 archives published (Officially stated) |
| Minimum Windows requirement | NOT OFFICIALLY DOCUMENTED as a single SKU in examined GenAI install excerpt |
| CPU support | Yes (`device='CPU'`) (Officially stated) |
| AVX2 requirement | Intel CPU path typically benefits from modern ISA; exact hard AVX2 requirement NOT OFFICIALLY DOCUMENTED here |
| Intel Iris Xe support | GPU device selectable; Iris Xe suitability REQUIRES LOCAL BENCHMARK |
| Whether i7-1165G7 is explicitly documented | NOT OFFICIALLY DOCUMENTED by CPU SKU in examined GenAI pages |
| Required drivers | Intel GPU driver if using GPU device |
| Required toolchains | Archive or PyPI `openvino-genai` (not installed in this task) |
| Installation mechanism | Official archive zip or PyPI (not executed here) |
| Portable extraction availability | Archive zip available (Officially stated) |
| Published installation/download footprint | Depends on package; exact chosen bytes REQUIRES INSTALL-TIME VERIFICATION |
| Background-process or service behaviour | Library/pipeline oriented; no required always-on service |
| Auto-start behaviour | None by default |
| Update behaviour | Manual package replacement |
| Model-storage control | Converted/IR model directories under operator control |
| Exact model-file control | Yes for IR/model dirs; not GGUF-primary |
| GGUF support | Not the primary format |
| ONNX support | OpenVINO conversion ecosystem may involve ONNX intermediates — workflow-dependent |
| Quantization support | OpenVINO quantization tools — details REQUIRES INSTALL-TIME VERIFICATION |
| Local HTTP API | Not the same drop-in llama-server HTTP; custom serving needed |
| Default bind host | NOT APPLICABLE unless a separate server is built |
| Default port | NOT APPLICABLE unless a separate server is built |
| Explicit loopback binding | NOT APPLICABLE unless a separate server is built |
| OpenAI-compatible endpoint | Not native drop-in — would require adapter/server |
| Structured JSON or grammar support | Pipeline-dependent — REQUIRES LOCAL BENCHMARK |
| Streaming support | Supported in GenAI pipelines (Officially stated) |
| Cancellation behaviour | REQUIRES INSTALL-TIME VERIFICATION |
| Request timeout controls | REQUIRES INSTALL-TIME VERIFICATION |
| Maximum-output controls | Generation config max tokens (Officially stated family) |
| Logging | Application-dependent |
| Authentication | NOT APPLICABLE for library-only use |
| Remote-exposure controls | NOT APPLICABLE for library-only use |
| Uninstall method | Delete archive/env packages |
| Rollback method | Remove package; keep SIONA Core |
| LocalOpenWeightProvider compatibility | Weak immediate fit — needs adapter/server work |
| Required SIONA adapter changes | Non-trivial vs current LocalOpenWeightProvider HTTP/GGUF assumptions |
| CPU suitability on i7-1165G7 | Promising Intel CPU path — REQUIRES LOCAL BENCHMARK |
| Iris Xe path | Possible GPU device — REQUIRES LOCAL BENCHMARK; no speed claim |
| Risks | Format/adapter mismatch for first gate |
| Unresolved questions | Whether to invest in OpenVINO after GGUF HTTP baseline |
| Selection status | **Alternative Intel-optimized research path — deferred** |

### 7. ONNX Runtime GenAI / WinML / DirectML

| Field | Value |
|-------|-------|
| Project | ONNX Runtime GenAI |
| Publisher | Microsoft |
| Exact release, version, tag or revision examined | Latest examined GitHub release **v0.15.0** (published 2026-07-30); historical v0.13.0 Windows DirectML/WinML assets also noted |
| Source-access date | 2026-08-05 |
| Exact official source references | https://github.com/microsoft/onnxruntime-genai/releases; ONNX Runtime GenAI documentation; Phi-4 ONNX model card |
| Licence | ONNX Runtime GenAI project licence — confirm LICENSE/NOTICE in chosen package at install time (REQUIRES INSTALL-TIME VERIFICATION) |
| Windows x64 support | Yes — win-x64 and DML/WinML assets published (Officially stated) |
| Minimum Windows requirement | NOT OFFICIALLY DOCUMENTED as a single SKU in examined release JSON |
| CPU support | Yes (CPU packages) (Officially stated) |
| AVX2 requirement | NOT OFFICIALLY DOCUMENTED in examined release notes excerpt |
| Intel Iris Xe support | DirectML EP can target Windows GPUs including iGPUs — suitability REQUIRES LOCAL BENCHMARK |
| Whether i7-1165G7 is explicitly documented | NOT OFFICIALLY DOCUMENTED by SKU |
| Required drivers | DirectML/GPU stack for DML builds |
| Required toolchains | Prebuilt packages / pip wheels (not installed here) |
| Installation mechanism | Official release archives or packages (not executed) |
| Portable extraction availability | Zip archives available (Officially stated) |
| Published installation/download footprint | Confirm chosen v0.15.0 asset sizes at install time (historical 0.13.0 win-x64-dml ~16.1 MB class) |
| Background-process or service behaviour | Library-oriented unless wrapped in a server |
| Auto-start behaviour | None by default |
| Update behaviour | Manual package replacement |
| Model-storage control | ONNX model directories under operator control |
| Exact model-file control | Yes for ONNX artefacts |
| GGUF support | Not the primary path |
| ONNX support | Yes — primary (Officially stated) |
| Quantization support | ONNX quantized variants (e.g. int4 packages for Phi) |
| Local HTTP API | Not native llama-server; custom serving needed |
| Default bind host | NOT APPLICABLE unless custom server |
| Default port | NOT APPLICABLE unless custom server |
| Explicit loopback binding | NOT APPLICABLE unless custom server |
| OpenAI-compatible endpoint | Not native drop-in |
| Structured JSON or grammar support | Model/pipeline dependent — REQUIRES LOCAL BENCHMARK |
| Streaming support | Supported in GenAI APIs — confirm for chosen version |
| Cancellation behaviour | REQUIRES INSTALL-TIME VERIFICATION |
| Request timeout controls | REQUIRES INSTALL-TIME VERIFICATION |
| Maximum-output controls | REQUIRES INSTALL-TIME VERIFICATION |
| Logging | Application-dependent |
| Authentication | NOT APPLICABLE for library-only |
| Remote-exposure controls | NOT APPLICABLE for library-only |
| Uninstall method | Delete packages/dirs |
| Rollback method | Remove ORT GenAI install; keep SIONA Core |
| LocalOpenWeightProvider compatibility | Weak immediate fit vs current HTTP/GGUF provider |
| Required SIONA adapter changes | Significant adapter work unless HTTP facade added |
| CPU suitability on i7-1165G7 | Feasible for small ONNX models — REQUIRES LOCAL BENCHMARK |
| Iris Xe path | DirectML possible — REQUIRES LOCAL BENCHMARK; no speed claim |
| Risks | Different artefact ecosystem from GGUF baseline |
| Unresolved questions | Whether Phi-4 ONNX path should be a separate later track |
| Selection status | **Deferred — not first GGUF baseline** |

## Runtime recommendation history and current status

**Historical selection status:** PROVISIONAL — REQUIRED OWNER APPROVAL BEFORE INSTALLATION

**Current status:** OWNER-AUTHORIZED DOWNLOAD AND PORTABLE INSTALLATION COMPLETED; ARTIFACT-VERIFIED LOCALLY; LIMITED LOOPBACK EXECUTION COMPLETED; OPENAI_CHAT TRANSPORT IMPLEMENTED; CONTROLLED REAL-PROVIDER TEXT PATH VALIDATED (EXP-3B-005); GATE E BREADTH RECORDED (EXP-3B-011); MODEL-REGISTRY ACTIVATION REVIEW PASSED (EXP-3B-012); REGISTRY RECORD AVAILABLE; BINDING SOFTWARE SUPPORTED; STATE C CONTROLLED REGISTRY-BOUND REAL-RUNTIME VERIFICATION PASSED (EXP-3B-013); RUNTIME CURRENTLY STOPPED; ADR ACCEPTANCE STILL PENDING

Primary first baseline remains **llama.cpp native Windows x64 CPU**
(tag **b9968** / commit `1d1d9a9ed7a4f09c4225ea4cc8fd3bd1cf2c940f`).

The historical recommendation remains useful as decision provenance. It is
**not** the current installation state. Installation occurred later under
separate explicit owner authorization. Local operator evidence records
artifact verification, a limited loopback probe, EXP-3B-005 controlled
real-provider text-path validation, Gate E breadth (EXP-3B-011), and
model-registry activation review (EXP-3B-012). The runtime is currently
stopped. State C (controlled registry-bound real-runtime verification) PASSED
under EXP-3B-013. ADR acceptance still requires separate authorization.

**Historical owner-selection gate wording:** OWNER-APPROVED FOR PRE-INSTALLATION VERIFICATION ONLY

Later experiment: **llama.cpp SYCL**. Convenience comparison: **Ollama**.
Alternative research path: **OpenVINO GenAI**.

No final production runtime approval is issued by ADR 0003 (still Proposed).

---

## Model comparisons
### Candidate A — Qwen3-1.7B

| Field | Value |
|-------|-------|
| Exact original repository | `Qwen/Qwen3-1.7B` |
| Original repository revision | `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` |
| Exact quantized repository | Publisher: `Qwen/Qwen3-1.7B-GGUF`. Alternate Q4_K_M: `ggml-org/Qwen3-1.7B-GGUF` |
| Quantized repository revision | Publisher GGUF revision `90862c4b9d2787eaed51d12237eafdfe7c5f6077` (tree lists **Q8_0 only**). ggml-org revision `daeb8e2d528a760970442092f6bf1e55c3b659eb` |
| Original publisher | Alibaba Cloud / Qwen |
| Original author/team | Qwen Team |
| Quantizer | Publisher path: Qwen. Q4_K_M path: **ggml-org** |
| Model family | Qwen3 |
| Architecture | Dense causal LM (Qwen3) |
| Parameter count | 1.7B (Officially stated) |
| Active parameter count | Non-embedding 1.4B (Officially stated on model card) |
| Training stage | Pretraining & post-training (Officially stated) |
| Licence | Apache License 2.0 (Officially stated) |
| Commercial-use conditions | Commercial use permitted subject to Apache License 2.0 conditions (licence text, copyright/patent/trademark/attribution notice preservation). Officially stated by Apache-2.0; not a waiver of all obligations. |
| Licence preservation requirements | Must retain all copyright, patent, trademark, and attribution notices; include a copy of the Apache-2.0 licence with any distribution of the Work or Derivative Works; modified files must carry prominent notices stating changes were made (Apache-2.0 §4). Apache-2.0 grants no trademark rights to the names/logos of the licensor. |
| NOTICE requirements | If a NOTICE file is supplied with the Work, readable copies of the attribution notices contained within that NOTICE file must be included in distributions, excluding notices that do not pertain to any part of the Derivative Works (Apache-2.0 §4(d)). Confirm NOTICE presence at download time — REQUIRES INSTALL-TIME VERIFICATION. |
| Acceptable-use restrictions | No separate acceptable-use policy beyond Apache-2.0 found in examined card; follow model-card guidance and applicable law. Model-card guidance is separate from the licence text. |
| Base-model dependency | `Qwen/Qwen3-1.7B-Base` (Officially stated on card) |
| File format | GGUF (quantized path) |
| Exact quantization | Publisher examined revision: **Q8_0 only**. Requested Q4_K_M: ggml-org only as of pinned revision |
| Exact filename | Publisher: `Qwen3-1.7B-Q8_0.gguf`. ggml-org: `Qwen3-1.7B-Q4_K_M.gguf` |
| Published size in bytes | Q8_0: 1834426016 bytes. Q4_K_M: 1282439264 bytes (Officially stated via HF LFS metadata) |
| Published SHA256/LFS/Xet digest | Q8_0 LFS SHA256 `061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a` (xet `0765e15700b0f9aebe441b64af38978f083447471b9854e10a18c644740e1a6d`). Q4_K_M LFS SHA256 `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5` (xet `0a8e661bad7f1ea5accdd078b6a2aca20ff0201100bbf128aa1cc22c643d7221`) |
| Native context | 32768 native (Officially stated) |
| Extended context | NOT OFFICIALLY DOCUMENTED as YaRN-extended for 1.7B in examined 1.7B card |
| Languages | 100+ claimed (Officially stated) |
| Tool-use claims | Agent/tool capabilities claimed; SIONA treats tool calls as advisory |
| Structured-output claims | Prompted JSON / agent frameworks claimed; not a SIONA acceptance guarantee |
| Thinking/reasoning mode | Yes (default thinking mode) (Officially stated) |
| Method for disabling thinking | `enable_thinking=False` / `/no_think` (Officially stated) |
| Sampling/repetition warnings | Avoid greedy decoding in thinking mode; consider presence_penalty ~1.5 on quants (Officially stated guidance) |
| Official runtime instructions | Official llama.cpp / Ollama guidance on Qwen docs and GGUF READMEs |
| Estimated weight RAM | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT: ≈ file size for mmap-friendly load; Q4_K_M file ≈1.19 GiB; Q8_0 file ≈1.71 GiB |
| Estimated total RAM | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT: weights + KV + runtime overhead; planning band ~2–5 GiB depending on context/quant — measure locally |
| KV-cache estimate at 2,048 | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT: ~224 MiB. Assumptions (Qwen3-1.7B-class): hidden=2048, n_q=16, n_kv=8, head_dim=128, n_layers=28, KV stored fp16; bytes/token ≈ 2 * n_layers * n_kv * head_dim * 2 = 114688 (~112 KiB/token). |
| KV-cache estimate at 4,096 | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT: ~448 MiB (same assumptions as 2,048) |
| KV-cache estimate at 8,192 | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT: ~896 MiB (same assumptions as 2,048) |
| Total disk estimate | ≈1.19 GiB (Q4_K_M) or ≈1.71 GiB (Q8_0) + runtime binaries |
| CPU suitability | Good first-integration candidate on 4C/8T |
| Expected latency classification | unknown until benchmark (likely moderate on CPU) — do not fabricate tokens/s |
| Provenance risk | Low for publisher Q8_0; moderate for ggml-org Q4_K_M |
| Licence risk | Low (Apache-2.0) if licence/NOTICE obligations preserved |
| Runtime-maturity risk | Low on llama.cpp for Qwen3 text |
| Local evaluation status | Limited local loopback smoke completed; controlled real-provider text path validated (EXP-3B-005); Gate E breadth recorded (EXP-3B-011); model-registry activation review passed (EXP-3B-012) |
| Selection status | **OWNER-AUTHORIZED locally installed baseline; controlled real-provider text path validated (EXP-3B-005); runtime currently stopped; registry record available; ADR acceptance pending** |

### Candidate B — Qwen3-4B

| Field | Value |
|-------|-------|
| Exact original repository | `Qwen/Qwen3-4B` |
| Original repository revision | `1cfa9a7208912126459214e8b04321603b3df60c` |
| Exact quantized repository | `Qwen/Qwen3-4B-GGUF` |
| Quantized repository revision | `bc640142c66e1fdd12af0bd68f40445458f3869b` |
| Original publisher | Alibaba Cloud / Qwen |
| Original author/team | Qwen Team |
| Quantizer | Qwen (publisher GGUF) |
| Model family | Qwen3 |
| Architecture | Dense causal LM (Qwen3) |
| Parameter count | 4.0B (Officially stated) |
| Active parameter count | Non-embedding 3.6B (Officially stated) |
| Training stage | Pretraining & post-training |
| Licence | Apache License 2.0 (Officially stated) |
| Commercial-use conditions | Commercial use permitted subject to Apache License 2.0 conditions (licence text, copyright/patent/trademark/attribution notice preservation). Officially stated by Apache-2.0; not a waiver of all obligations. |
| Licence preservation requirements | Must retain all copyright, patent, trademark, and attribution notices; include a copy of the Apache-2.0 licence with any distribution of the Work or Derivative Works; modified files must carry prominent notices stating changes were made (Apache-2.0 §4). Apache-2.0 grants no trademark rights to the names/logos of the licensor. |
| NOTICE requirements | If a NOTICE file is supplied with the Work, readable copies of the attribution notices contained within that NOTICE file must be included in distributions, excluding notices that do not pertain to any part of the Derivative Works (Apache-2.0 §4(d)). Confirm NOTICE presence at download time — REQUIRES INSTALL-TIME VERIFICATION. |
| Acceptable-use restrictions | Follow model card + applicable law; card guidance separate from licence |
| Base-model dependency | `Qwen/Qwen3-4B` base lineage per card |
| File format | GGUF |
| Exact quantization | Q4_K_M (also Q5_0, Q5_K_M, Q6_K, Q8_0 present at examined revision) |
| Exact filename | `Qwen3-4B-Q4_K_M.gguf` |
| Published size in bytes | 2497280256 bytes (Officially stated via HF LFS metadata) |
| Published SHA256/LFS/Xet digest | LFS SHA256 `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5` (xet `9375c1fd02b321abc3f51b69ff7fcdd187af17f0d694c5b05000b54664292e17`) |
| Native context | 32768 native (Officially stated) |
| Extended context | 131072 with YaRN (Officially stated on card) |
| Languages | 100+ claimed |
| Tool-use claims | Agent/tool claims; advisory under SIONA |
| Structured-output claims | Prompted structured formats claimed |
| Thinking/reasoning mode | Yes |
| Method for disabling thinking | `/no_think` / `enable_thinking=False` |
| Sampling/repetition warnings | Same family warnings as 1.7B; presence_penalty guidance for quants |
| Official runtime instructions | Official llama.cpp quickstart on GGUF README |
| Estimated weight RAM | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT: ≈2.33 GiB file class |
| Estimated total RAM | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT: higher than 1.7B; measure locally before approval |
| KV-cache estimate at 2,048 | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT: do not copy 1.7B KV numbers — measure for 4B architecture |
| KV-cache estimate at 4,096 | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT |
| KV-cache estimate at 8,192 | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT |
| Total disk estimate | ≈2.33 GiB + runtime |
| CPU suitability | Feasible but heavier — after 1.7B gate |
| Expected latency classification | unknown until benchmark (likely higher than 1.7B) — no tokens/s fabricated |
| Provenance risk | Low (publisher GGUF) |
| Licence risk | Low if Apache notices preserved |
| Runtime-maturity risk | Low on llama.cpp |
| Local evaluation status | Not evaluated |
| Selection status | **Second capability candidate — deferred; no download authorized** |
### Candidate C — IBM Granite 4.0 Micro

| Field | Value |
|-------|-------|
| Exact original repository | `ibm-granite/granite-4.0-micro` |
| Original repository revision | `56111ae135df9c53a78c99028e7bc24035a9e979` |
| Exact quantized repository | `ibm-granite/granite-4.0-micro-GGUF` |
| Quantized repository revision | `ec48475f0c811d812fbfb61975717a9c36eeb652` |
| Original publisher | IBM Granite Team |
| Original author/team | Granite Team, IBM |
| Quantizer | IBM GGUF conversion pipeline (`IBM/gguf` / ibm-granite GGUF repos) |
| Model family | Granite 4.0 |
| Architecture | Dense Transformer instruct (card); GGUF architecture label `granite` |
| Parameter count | ~3B (card / GGUF model size) |
| Active parameter count | NOT OFFICIALLY DOCUMENTED as a separate active-parameter figure in examined card excerpt |
| Training stage | SFT + RL alignment + merging (Officially stated on card) |
| Licence | Apache License 2.0 (Officially stated) |
| Commercial-use conditions | Commercial use permitted subject to Apache License 2.0 conditions (licence text, copyright/patent/trademark/attribution notice preservation). Officially stated by Apache-2.0; not a waiver of all obligations. |
| Licence preservation requirements | Must retain all copyright, patent, trademark, and attribution notices; include a copy of the Apache-2.0 licence with any distribution of the Work or Derivative Works; modified files must carry prominent notices stating changes were made (Apache-2.0 §4). Apache-2.0 grants no trademark rights to the names/logos of the licensor. |
| NOTICE requirements | If a NOTICE file is supplied with the Work, readable copies of the attribution notices contained within that NOTICE file must be included in distributions, excluding notices that do not pertain to any part of the Derivative Works (Apache-2.0 §4(d)). Confirm NOTICE presence at download time — REQUIRES INSTALL-TIME VERIFICATION. |
| Acceptable-use restrictions | Intended-use text on card; follow applicable law / enterprise policy — separate from Apache-2.0 grant |
| Base-model dependency | Finetuned from `granite-4.0-micro-base` |
| File format | GGUF |
| Exact quantization | Q4_K_M |
| Exact filename | `granite-4.0-micro-Q4_K_M.gguf` |
| Published size in bytes | 2099502528 bytes (Officially stated via HF LFS metadata) |
| Published SHA256/LFS/Xet digest | LFS SHA256 `97c417dcc0534b0737c74016fb2af083cb17c3b51eaac621192d23961b7024eb` (xet `8ca04a7bd6ff2696b516cc2fcf8ace5facb1d8b07bbd28e8130e4410601aae9a`) |
| Native context | Long-context instruct — exact native numeric max REQUIRES INSTALL-TIME VERIFICATION from full card tables |
| Extended context | REQUIRES INSTALL-TIME VERIFICATION from full card tables |
| Languages | EN, DE, ES, FR, JA, PT, AR, CS, IT, KO, NL, ZH (Officially stated) |
| Tool-use claims | Tool-calling / function-calling claimed (Officially stated) |
| Structured-output claims | Structured JSON output claimed in Granite 4.0 family docs |
| Thinking/reasoning mode | NOT OFFICIALLY DOCUMENTED as Qwen-style think tags in examined excerpt |
| Method for disabling thinking | NOT APPLICABLE / NOT OFFICIALLY DOCUMENTED |
| Sampling/repetition warnings | Follow Granite card defaults — REQUIRES INSTALL-TIME VERIFICATION |
| Official runtime instructions | Transformers examples on card; GGUF via llama.cpp ecosystem |
| Estimated weight RAM | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT: ≈1.96 GiB file class |
| Estimated total RAM | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT: measure locally |
| KV-cache estimate at 2,048 | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT |
| KV-cache estimate at 4,096 | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT |
| KV-cache estimate at 8,192 | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT |
| Total disk estimate | ≈1.96 GiB + runtime |
| CPU suitability | Feasible comparison class |
| Expected latency classification | unknown until benchmark — no tokens/s fabricated |
| Provenance risk | Low (official IBM GGUF) |
| Licence risk | Low if Apache notices preserved |
| Runtime-maturity risk | Low–moderate depending on llama.cpp granite support maturity — REQUIRES LOCAL BENCHMARK |
| Local evaluation status | Not evaluated |
| Selection status | **Comparison candidate — no download authorized** |

### Candidate D — Microsoft Phi-4-mini-instruct

| Field | Value |
|-------|-------|
| Exact original repository | `microsoft/Phi-4-mini-instruct` |
| Original repository revision | `cfbefacb99257ffa30c83adab238a50856ac3083` |
| Exact quantized repository | Official GGUF: **not published by Microsoft** on access date. Official ONNX: `microsoft/Phi-4-mini-instruct-onnx` |
| Quantized repository revision | ONNX repo revision `fc04c8f93df696602fd9f300a30d1bf2e3081347` |
| Original publisher | Microsoft |
| Original author/team | Microsoft Phi team |
| Quantizer | Official ONNX packages by Microsoft; community GGUF quantizers are **third party** |
| Model family | Phi-4 |
| Architecture | Phi-4 mini instruct |
| Parameter count | Lightweight mini class — confirm exact parameter count from card tables at use time |
| Active parameter count | NOT OFFICIALLY DOCUMENTED in examined README excerpt as a separate figure |
| Training stage | SFT + DPO enhancement (Officially stated) |
| Licence | MIT (Officially stated) |
| Commercial-use conditions | MIT permits commercial use subject to MIT notice conditions |
| Licence preservation requirements | Retain copyright notice and permission notice in all copies or substantial portions of the Software (MIT) |
| NOTICE requirements | MIT does not define Apache-style NOTICE file requirements; preserve the LICENSE text |
| Acceptable-use restrictions | Primary use cases and limitations on model card — review before deployment; separate from MIT grant |
| Base-model dependency | Phi-4 mini lineage |
| File format | Safetensors original; official ONNX packages; community GGUF only |
| Exact quantization | Official ONNX int4 variants exist; community GGUF Q4_K_M exists but is not Microsoft-quantized |
| Exact filename | ONNX examples include `cpu_and_mobile/cpu-int4-rtn-block-32-acc-level-4/model.onnx` and `gpu/gpu-int4-rtn-block-32/model.onnx` |
| Published size in bytes | NOT OFFICIALLY DOCUMENTED as a single GGUF size (no official GGUF). ONNX sizes REQUIRES INSTALL-TIME VERIFICATION |
| Published SHA256/LFS/Xet digest | NOT APPLICABLE for official GGUF (none). ONNX digests REQUIRES INSTALL-TIME VERIFICATION per chosen file |
| Native context | Up to 128K claimed (Officially stated) |
| Extended context | 128K claimed context length (Officially stated) |
| Languages | Multilingual list on card |
| Tool-use claims | Broad assistant use; tool-calling specifics REQUIRES INSTALL-TIME VERIFICATION |
| Structured-output claims | Card focuses on instruction adherence; structured-output guarantees REQUIRES LOCAL BENCHMARK |
| Thinking/reasoning mode | Separate Phi reasoning variants exist; this instruct card is not the reasoning SKU |
| Method for disabling thinking | NOT APPLICABLE / model-dependent |
| Sampling/repetition warnings | Follow card recommendations — REQUIRES INSTALL-TIME VERIFICATION |
| Official runtime instructions | Transformers / ONNX Runtime paths; llama.cpp supports architecture historically but official GGUF absent |
| Estimated weight RAM | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT for chosen ONNX/community GGUF |
| Estimated total RAM | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT |
| KV-cache estimate at 2,048 | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT |
| KV-cache estimate at 4,096 | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT |
| KV-cache estimate at 8,192 | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT |
| Total disk estimate | REQUIRES INSTALL-TIME VERIFICATION for chosen artefact |
| CPU suitability | Feasible in principle |
| Expected latency classification | unknown until benchmark — no tokens/s fabricated |
| Provenance risk | **Higher** if using community GGUF; lower if using official ONNX under a separate ORT plan |
| Licence risk | Low for MIT if notices preserved |
| Runtime-maturity risk | Moderate for community GGUF provenance; ORT path separate |
| Local evaluation status | Not evaluated |
| Selection status | **Deferred — community GGUF not preferred for first gate** |

### Candidate E — Qwen3.5-2B

| Field | Value |
|-------|-------|
| Exact original repository | `Qwen/Qwen3.5-2B` |
| Original repository revision | `15852e8c16360a2fea060d615a32b45270f8a8fc` |
| Exact quantized repository | Official publisher GGUF not established as first-party on access date; community GGUFs exist (third party) |
| Quantized repository revision | NOT APPLICABLE for official GGUF (none pinned) |
| Original publisher | Alibaba Cloud / Qwen |
| Original author/team | Qwen Team |
| Quantizer | Community only if GGUF used — not recommended for first gate |
| Model family | Qwen3.5 |
| Architecture | Natively multimodal (text+image(+video tokens)); hybrid attention stack |
| Parameter count | ~2B class |
| Active parameter count | NOT OFFICIALLY DOCUMENTED in examined excerpt as separate active params |
| Training stage | Post-trained multimodal foundation (Officially stated) |
| Licence | Apache License 2.0 (Officially stated) |
| Commercial-use conditions | Commercial use permitted subject to Apache License 2.0 conditions (licence text, copyright/patent/trademark/attribution notice preservation). Officially stated by Apache-2.0; not a waiver of all obligations. |
| Licence preservation requirements | Must retain all copyright, patent, trademark, and attribution notices; include a copy of the Apache-2.0 licence with any distribution of the Work or Derivative Works; modified files must carry prominent notices stating changes were made (Apache-2.0 §4). Apache-2.0 grants no trademark rights to the names/logos of the licensor. |
| NOTICE requirements | If a NOTICE file is supplied with the Work, readable copies of the attribution notices contained within that NOTICE file must be included in distributions, excluding notices that do not pertain to any part of the Derivative Works (Apache-2.0 §4(d)). Confirm NOTICE presence at download time — REQUIRES INSTALL-TIME VERIFICATION. |
| Acceptable-use restrictions | Follow card + law; card restrictions separate from licence grant |
| Base-model dependency | `Qwen/Qwen3.5-2B-Base` |
| File format | Transformers / safetensors official; GGUF community-only |
| Exact quantization | NOT APPLICABLE for official GGUF |
| Exact filename | Official weights e.g. `model.safetensors-00001-of-00001.safetensors` (not a GGUF baseline artefact) |
| Published size in bytes | REQUIRES INSTALL-TIME VERIFICATION for safetensors; no official GGUF size |
| Published SHA256/LFS/Xet digest | REQUIRES INSTALL-TIME VERIFICATION for chosen safetensors; no official GGUF digest |
| Native context | Long context claimed in ecosystem docs (implementation-dependent) |
| Extended context | REQUIRES INSTALL-TIME VERIFICATION |
| Languages | Multilingual claimed |
| Tool-use claims | Tool-calling claimed in ecosystem summaries |
| Structured-output claims | REQUIRES LOCAL BENCHMARK |
| Thinking/reasoning mode | Thinking/reasoning modes discussed in family docs |
| Method for disabling thinking | REQUIRES INSTALL-TIME VERIFICATION for exact controls |
| Sampling/repetition warnings | REQUIRES INSTALL-TIME VERIFICATION |
| Official runtime instructions | Transformers / vLLM / SGLang oriented; llama.cpp maturity for qwen35 newer |
| Estimated weight RAM | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT |
| Estimated total RAM | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT: multimodal overhead may increase RAM — measure |
| KV-cache estimate at 2,048 | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT |
| KV-cache estimate at 4,096 | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT |
| KV-cache estimate at 8,192 | ENGINEERING ESTIMATE — REQUIRES LOCAL MEASUREMENT |
| Total disk estimate | REQUIRES INSTALL-TIME VERIFICATION |
| CPU suitability | Not appropriate as first Phase 3B text-provider baseline |
| Expected latency classification | unknown until benchmark — no tokens/s fabricated |
| Provenance risk | Higher if community GGUF used |
| Licence risk | Low for Apache-2.0 if notices preserved |
| Runtime-maturity risk | Higher — newer multimodal architecture |
| Local evaluation status | Not evaluated |
| Selection status | **Research-only — rejected for first integration gate** |
## First-model recommendation history and current status

**Historical selection status:** PROVISIONAL — NO MODEL DOWNLOAD AUTHORIZED AT THE RESEARCH GATE

**Subsequent authorized outcome:** `Qwen3-1.7B-Q4_K_M.gguf` was downloaded under
explicit owner authorization, verified locally at the pinned size
(1282439264 bytes) and SHA256
`d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`, loaded for
a limited loopback probe, and retained on disk with the runtime stopped.

Primary family remains **Qwen3-1.7B** from `ggml-org/Qwen3-1.7B-GGUF` revision
`daeb8e2d528a760970442092f6bf1e55c3b659eb`.

**Historical owner-selection gate wording:** OWNER-APPROVED FIRST BASELINE FOR
PRE-INSTALLATION VERIFICATION

Publisher Q8_0 remains a possible later comparison. Second: Qwen3-4B Q4_K_M.
Comparison: Granite 4.0 Micro Q4_K_M.

**Current restrictions:**

- Controlled real SIONA provider text path validated (EXP-3B-005); limited
  text-transport gate only
- Gate E breadth recorded (EXP-3B-011): governed safety 8/8; runtime R01–R07
  passed; timeout/cancellation evaluated; streaming evaluated and classified
  UNSUPPORTED_ON_PINNED_BASELINE; native JSON remains NOT_VERIFIED
- Registry record availability and exact binding software support are complete
  under EXP-3B-012. A controlled real-runtime verification through that
  registry-bound path (state C) PASSED under EXP-3B-013; runtime stopped.
- STATE C DOES NOT MEAN AUTOMATIC OR PERMANENT MODEL STARTUP. It was a controlled
  controlled verification that starts the pinned llama.cpp/Qwen baseline,
  enables the local provider, loads the canonical registry, proves exact entry
  binding and real pinned-model reachability, confirms safe registry
  observability, performs no tool execution, keeps loopback-only operation,
  then shuts the runtime down and verifies port/process closure.
- Verified registry behaviour: bounded text/chat only at context 4096;
  tools=false; structured_json=false; streaming=false; multimodal=false
- ADR 0003 acceptance remains pending
- ADR 0003 remains Proposed
- Phase 3B remains in progress
- Phase 4 remains not started
- Runtime currently stopped
- Further adversarial follow-on campaigns beyond the Gate E catalogue require
  separate explicit authorization

---

## Source traceability appendix

| Item | Official source | Exact version/revision | Accessed | Evidence used | Remaining uncertainty |
|------|-----------------|------------------------|----------|---------------|------------------------|
| llama.cpp CPU/SYCL/Vulkan binaries | https://github.com/ggml-org/llama.cpp/releases/tag/b9968 | tag b9968 / commit `1d1d9a9ed7a4f09c4225ea4cc8fd3bd1cf2c940f` | 2026-08-05 | Asset names `llama-b9968-bin-win-cpu-x64.zip`, `llama-b9968-bin-win-sycl-x64.zip`, `llama-b9968-bin-win-vulkan-x64.zip`; MIT licence; backend docs | Exact `--help` flags on extracted binary |
| llama.cpp SYCL i7-1165G7 note | docs/backend/SYCL.md | upstream docs at access date | 2026-08-05 | iGPU list includes i7-1165G7 | Local SYCL performance |
| Ollama Windows | https://docs.ollama.com/windows | UNVERSIONED OFFICIAL DOCUMENTATION — ACCESSED 2026-08-05; project release v0.32.5 / `eec8e0b9458b8a01be0c216a9cc53eefde24ef50` | 2026-08-05 | Win10 22H2+, port 11434, background app | Iris Xe support |
| LM Studio terms | https://lmstudio.ai/terms | Version July 1, 2025 | 2026-08-05 | Personal/internal business licence; redistribution/SaaS restrictions | Legal review for edge cases |
| LM Studio server | https://lmstudio.ai/docs/developer/core/server | UNVERSIONED OFFICIAL DOCUMENTATION — ACCESSED 2026-08-05 | 2026-08-05 | localhost:1234; network serve option | Auth defaults |
| OpenVINO GenAI | docs.openvino.ai + GitHub release | tag 2026.3.0.0 | 2026-08-05 | CPU/GPU devices; archive install | Exact Windows min SKU |
| ONNX Runtime GenAI | GitHub microsoft/onnxruntime-genai | v0.15.0 | 2026-08-05 | Windows/DirectML packaging exists | Iris Xe benchmark |
| Qwen3-1.7B | HF `Qwen/Qwen3-1.7B` | `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` | 2026-08-05 | Params, Apache-2.0, thinking controls | Local RAM |
| Qwen3-1.7B-GGUF publisher | HF `Qwen/Qwen3-1.7B-GGUF` | `90862c4b9d2787eaed51d12237eafdfe7c5f6077` | 2026-08-05 | **Only Q8_0 present**; size+SHA256 | Whether publisher later adds Q4_K_M |
| Qwen3-1.7B Q4_K_M | HF `ggml-org/Qwen3-1.7B-GGUF` | `daeb8e2d528a760970442092f6bf1e55c3b659eb` | 2026-08-05 | Q4_K_M size+SHA256 | Quantizer provenance acceptance |
| Qwen3-4B | HF `Qwen/Qwen3-4B` | `1cfa9a7208912126459214e8b04321603b3df60c` | 2026-08-05 | Params, Apache-2.0 | Local latency |
| Qwen3-4B-GGUF | HF `Qwen/Qwen3-4B-GGUF` | `bc640142c66e1fdd12af0bd68f40445458f3869b` | 2026-08-05 | Official Q4_K_M digest | Local latency |
| Granite 4.0 Micro | HF `ibm-granite/granite-4.0-micro` | `56111ae135df9c53a78c99028e7bc24035a9e979` | 2026-08-05 | Apache-2.0; instruct card | Exact context numerics |
| Granite 4.0 Micro GGUF | HF `ibm-granite/granite-4.0-micro-GGUF` | `ec48475f0c811d812fbfb61975717a9c36eeb652` | 2026-08-05 | Official Q4_K_M digest | Exact context numerics |
| Phi-4-mini-instruct | HF `microsoft/Phi-4-mini-instruct` | `cfbefacb99257ffa30c83adab238a50856ac3083` | 2026-08-05 | MIT; no official GGUF | Community GGUF risk |
| Phi-4-mini ONNX | HF `microsoft/Phi-4-mini-instruct-onnx` | `fc04c8f93df696602fd9f300a30d1bf2e3081347` | 2026-08-05 | Official ONNX paths | ORT adapter effort |
| Qwen3.5-2B | HF `Qwen/Qwen3.5-2B` | `15852e8c16360a2fea060d615a32b45270f8a8fc` | 2026-08-05 | Multimodal; Apache-2.0 | Not first baseline |

Every provisional recommendation above traces to one or more appendix rows.

## Related documents

- [PHASE_3B_HARDWARE_INVENTORY.md](PHASE_3B_HARDWARE_INVENTORY.md)
- [PHASE_3B_MODEL_INDEPENDENCE.md](PHASE_3B_MODEL_INDEPENDENCE.md)
- [PHASE_3B_INSTALLATION_RUNBOOK.md](PHASE_3B_INSTALLATION_RUNBOOK.md)
- [adr/0003-first-local-model-strategy.md](adr/0003-first-local-model-strategy.md)
