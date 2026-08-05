# Phase 3B — Hardware Inventory

**Status:** recorded (read-only inventory)  
**Machine:** SIBONA  
**Purpose:** evidence base for optional local-model runtime and weight selection  
**Constraint:** CPU-first baseline; no runtime or weights installed by this document

## Measured environment

| Field | Value |
|-------|--------|
| Computer name | SIBONA |
| Form factor | Laptop — HP EliteBook 840 G8 Notebook PC |
| OS (WMI reporting) | Windows Pro, 64-bit, build **26200** |
| OS note | WMI `WindowsProductName` / `WindowsVersion` fields may be stale; confirm later with `winver` before any install gate |
| Hostname | SIBONA |
| PowerShell | 5.1.26100.8875 (Desktop) |

### CPU

| Field | Value |
|-------|--------|
| Model | Intel Core i7-1165G7 @ 2.80 GHz (11th Gen / Tiger Lake) |
| Physical cores | 4 |
| Logical processors | 8 |
| Max clock (WMI) | 2804 MHz |
| AVX / AVX2 | Expected for Tiger Lake; **not** directly CPUID-verified in this inventory |
| Virtualization (WMI) | `VirtualizationFirmwareEnabled` reported False; WSL2 nonetheless present |

### GPU

| Field | Value |
|-------|--------|
| Adapter | Intel Iris Xe Graphics |
| Memory nature | Shared system memory (not discrete VRAM) |
| AdapterRAM (WMI) | ~2.00 GiB reported (shared figure) |
| Driver | 32.0.101.7085 (date 2026-03-03) |
| NVIDIA CUDA GPU | **None** — `nvidia-smi` not present |

### Memory

| Field | Value |
|-------|--------|
| Total usable RAM | 15.73 GiB |
| Free RAM (post restart/check) | 4.73 GiB |
| Preferred pre-inference free-RAM target | **6–8 GiB** |
| Installed module | 1× 16 GiB Samsung `M471A2K43EB1-CWE` @ 3200 MHz |
| Page file | `C:\pagefile.sys`, approximately **14.1 GB** allocated |

### Storage

| Field | Value |
|-------|--------|
| Drive | C: (NTFS) — only fixed drive |
| Total capacity | 475.88 GiB |
| Free after controlled cleanup | **41.86 GiB** |
| Previous low-space state | approximately 7.74 GiB |
| Cleanup action | 31.51 GiB duplicate game archive removed; extracted game preserved |
| Repository location | `C:\Users\njaji\Documents\SSN*` (on C:) |

### Python

| Field | Value |
|-------|--------|
| Interpreter | Python 3.14.3 |
| Phase environment | `C:\Users\njaji\Documents\SSN\.venv\Scripts\python.exe` |
| Inference packages | None installed (no torch, llama-cpp-python, openvino, onnxruntime, etc.) |

### Platform tooling

| Tool | Status |
|------|--------|
| WSL | WSL **2.6.1**; Ubuntu WSL2 available but **Stopped** |
| Docker | **Not installed** |
| Existing model runtimes | **None** (no Ollama, llama.cpp CLI, LM Studio, etc.) |
| Git | 2.51.2.windows.1 |
| Active power profile | Balanced |
| AC / battery during inventory | On AC (laptop) |

## Execution constraint

- **CPU-first baseline** for any first optional local model.
- Iris Xe acceleration is **experimental until benchmarked** and must not be assumed.
- Prolonged CPU inference on a laptop under the Balanced plan is likely thermally constrained.
- No automatic runtime start, no remote exposure, and no CI model download are permitted by planning defaults.

## Readiness gates

| Gate | Status |
|------|--------|
| Storage gate | **Passed** (41.86 GiB free after controlled cleanup) |
| Documentation gate | **In progress** |
| Runtime installation gate | **Not yet approved** |
| Model download gate | **Not yet approved** |
| Real-model benchmark gate | **Not started** |

## Explicit non-claims

- This inventory does **not** select a runtime or model.
- This inventory does **not** authorize installation or weight download.
- Free-RAM figures fluctuate; the preferred 6–8 GiB free target is a planning threshold, not a guarantee.
- AVX/AVX2 support is datasheet-expected for this CPU, not a runtime CPUID proof from this pass.
