# Phase 3B — Installation Runbook

**Status:** owner-approved first baseline recorded for **pre-installation
verification only** — **no install authorized by this document**  
**Rule:** each destructive or state-changing step requires **explicit approval**
before execution

This runbook defines the ordered procedure for a future optional local runtime and
single-model install. Completing documentation is not approval to install.

## Approval gates

Do not proceed past a stage without recorded approval.

| Gate | Prerequisite | Approval required |
|------|--------------|-------------------|
| A — Environment | Hardware inventory current | Yes |
| B — Runtime install | Runtime research complete + Gate A | Yes |
| C — Model download | Model research + licence/provenance recorded + Gate B | Yes |
| D — Integration tests | Loopback health + provider tests + Gate C | Yes |
| E — Real-model eval | Gate D | Yes |
| F — Rollback drill | Any prior install | Yes |

## Provisional safety defaults

These defaults are **provisional**, not final production certification:

- Loopback only
- No remote exposure
- No automatic startup
- No automatic model download
- Tool execution disabled
- Capability status unverified
- Context initially bounded
- Output tokens initially bounded
- CPU-first baseline
- No model used in CI

## Owner-approved first baseline (pre-installation verification only)

**Terminology:** this is the **OWNER-APPROVED FIRST BASELINE FOR PRE-INSTALLATION
VERIFICATION**. It is **not** SIONA's permanent reasoning model, a final
production model, a SIONA-native model, a capability-approved model, an
installed model, or a downloaded model.

| Field | Recorded value | Current status |
|-------|----------------|----------------|
| Runtime family | llama.cpp | Owner-approved baseline |
| Runtime version | b9968 | Owner-approved baseline |
| Runtime commit | `1d1d9a9ed7a4f09c4225ea4cc8fd3bd1cf2c940f` | Source pinned |
| Runtime archive | `llama-b9968-bin-win-cpu-x64.zip` | Approved for verification only |
| Runtime SHA256 | REQUIRES PRE-INSTALL SOURCE VERIFICATION | Not yet verified |
| Runtime mode | Windows x64 CPU-only | Owner-approved baseline |
| Model family | Qwen3-1.7B | Owner-approved baseline |
| Original model publisher | Qwen Team / Alibaba Cloud | Source pinned |
| Model repository | `ggml-org/Qwen3-1.7B-GGUF` | Owner-approved baseline |
| Repository revision | `daeb8e2d528a760970442092f6bf1e55c3b659eb` | Source pinned |
| GGUF filename | `Qwen3-1.7B-Q4_K_M.gguf` | Owner-approved baseline |
| Published size | 1282439264 bytes | Expected only |
| Expected SHA256 | `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5` | Expected only |
| Model licence | Apache License 2.0 | Requires licence preservation |
| Quantizer | ggml-org | Explicit provenance |
| Purpose | Transport, integration, safety, provenance, rollback and baseline-performance validation only | Scope limited |
| Installation directory | PENDING READ-ONLY PRE-INSTALL CHECKLIST | Not approved |
| Model storage directory | PENDING READ-ONLY PRE-INSTALL CHECKLIST | Not approved |
| Host and port | Provisional intent `127.0.0.1:8080` | Not execution-approved |
| Context size | Provisional intent 4096 | Not execution-approved |
| Maximum output tokens | Provisional intent 512 | Not execution-approved |
| CPU threads | PENDING LOCAL VERIFICATION | Not approved |
| GPU layers | 0 for CPU baseline | Provisional |
| Capability status | Unverified | Must remain unverified |
| Download status | Not authorized | Blocked |
| Installation status | Not authorized | Blocked |
| Execution status | Not authorized | Blocked |
| Rollback commands | `UNAPPROVED — stop process; delete runtime dir; delete GGUF; restore registry mock` | Not approved |

### Download / install gate (blocked)

No download or state-changing command may be executed until:

1. This documentation PR is reviewed and merged.
2. Read-only pre-install checks pass.
3. Runtime archive source and checksum handling are verified.
4. Storage and free-RAM readings are refreshed.
5. Exact installation and rollback paths are approved.
6. The owner explicitly authorizes installation and model download.

**No install authorized. No model download authorized. No runtime execution
authorized.**

## Stages


### 1. Verify disk and RAM

- Confirm free disk on the model-storage drive meets the planned model size plus
  unpack/headroom budget.
- Confirm free RAM meets the preferred pre-inference target (currently 6–8 GiB).
- Record figures in the experiment log.
- **Approval required before stage 2.**

### 2. Verify operating system

- Confirm 64-bit Windows build with `winver` (WMI fields may be stale).
- Confirm no conflicting unmanaged runtime already bound to the intended port.
- **Approval required before stage 3.**

### 3. Select runtime based on approved research

- Complete [PHASE_3B_MODEL_RUNTIME_RESEARCH.md](PHASE_3B_MODEL_RUNTIME_RESEARCH.md)
  from official sources only.
- Record the selection rationale.
- **Approval required before stage 4.**

### 4. Record runtime version and source

- Exact version string
- Official download URL
- Publisher / project
- Licence summary
- **Approval required before stage 5.**

### 5. Download runtime from official source

- Download only the approved artefact.
- Do not use unofficial mirrors unless separately approved.
- **Approval required before stage 6.**

### 6. Verify checksum/signature when available

- Record expected digest/signature from the official source.
- Verify before extract/install.
- Stop on mismatch.
- **Approval required before stage 7.**

### 7. Install or extract to a controlled directory

- Prefer a controlled, non-system directory when the runtime allows it.
- Record the install path.
- Do not enable auto-start.
- **Approval required before stage 8.**

### 8. Select one model only

- One candidate model for the first real-model gate.
- Record licence, commercial-use conditions and provenance.
- **Approval required before stage 9.**

### 9. Record licence and provenance

- Publisher, author, quantizer (if any), licence text/URI, checksum source.
- Confirm ownership/adaptation implications for SIONA.
- **Approval required before stage 10.**

### 10. Download one model

- Download only the approved artefact.
- Store under the approved model path on the capacity-approved drive.
- **Approval required before stage 11.**

### 11. Verify model checksum

- Verify against the official digest.
- Stop on mismatch; do not register a failed artefact.
- **Approval required before stage 12.**

### 12. Register model in SIONA registry

- Use the existing provenance schema.
- Keep artefact and capability verification statuses honest.
- Do not mark capabilities verified without evidence.
- **Approval required before stage 13.**

### 13. Start runtime on loopback only

- Bind to loopback.
- No remote exposure.
- No automatic startup persistence.
- **Approval required before stage 14.**

### 14. Run health checks

- Runtime health endpoint / process health as applicable.
- Confirm the configured model ID is present.
- **Approval required before stage 15.**

### 15. Run provider tests

- Exercise `LocalOpenWeightProvider` against the loopback endpoint.
- Confirm sanitization, redirect rejection and fallback still hold.
- **Approval required before stage 16.**

### 16. Run real-model evaluations

- Use the provider evaluation harness with honest labels.
- Do not claim production certification from a first pass.
- **Approval required before stage 17.**

### 17. Record latency, memory and token throughput

- Record hardware state (AC/battery, free RAM, thermal notes).
- Do not fabricate metrics.
- **Approval required before stage 18.**

### 18. Shut down runtime

- Stop the process cleanly.
- Confirm ports are released.
- **Approval required before stage 19.**

### 19. Verify deterministic fallback

- With the runtime stopped, confirm offline/deterministic providers still pass.
- CI path must remain free of real-model dependencies.
- **Approval required before stage 20.**

### 20. Document rollback and uninstall

- Record exact uninstall/delete steps for runtime and model artefacts.
- Confirm SIONA Core continues without the optional provider.
- Record residual files, if any.

## Rollback outline (to be completed after a real install)

1. Stop runtime processes.
2. Remove auto-start entries if any were created (should be none under defaults).
3. Delete or quarantine model weights.
4. Uninstall or remove the controlled runtime directory.
5. Revert registry entries to mock/unverified state as appropriate.
6. Re-run `SSN_OFFLINE=1 python scripts/run_tests.py` and production eval.
7. Record the rollback in `EXPERIMENT_LOG.md`.

## Explicit non-authorization

This runbook does **not**:

- Install a runtime
- Download weights
- Approve a final model
- Change owner-control semantics
- Enable remote serving
- Add real models to CI
