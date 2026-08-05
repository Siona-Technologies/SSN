# Phase 3B — Installation Runbook

**Status:** first baseline **installed and artifact-verified locally** (2026-08-05);
limited loopback execution and **controlled real SIONA provider text-path
validation** completed; runtime **stopped** — registry activation, Gate E
evaluation, capability approval, and ADR acceptance **not** authorized by this
document  
**Rule:** each destructive or state-changing step beyond the recorded baseline
requires **explicit approval** before execution

This runbook defines the ordered procedure for the optional local runtime and
single-model install. Completing documentation is not approval for provider integration,
capability claims, or ADR acceptance.

## Approval gates

Do not proceed past a stage without recorded approval.

| Gate | Prerequisite | Approval required | Local status (2026-08-05) |
|------|--------------|-------------------|---------------------------|
| A — Environment | Hardware inventory current | Yes | Passed (read-only checklist) |
| B — Runtime install | Runtime research complete + Gate A | Yes | **Completed locally** |
| C — Model download | Model research + licence/provenance recorded + Gate B | Yes | **Completed locally** |
| D — Integration tests | Loopback health + provider tests + Gate C | Yes | **Controlled real-provider text path validated** (EXP-3B-005); runtime stopped; registry/Gate E/capability approval still pending |
| E — Real-model eval | Gate D | Yes | Pending — not complete |
| F — Rollback drill | Any prior install | Yes | Portable layout ready; post-shutdown deterministic fallback verified; full campaign pending |

## Provisional safety defaults

These defaults are **provisional**, not final production certification:

- Loopback only
- No remote exposure
- No automatic startup
- No automatic model download
- Tool execution disabled
- Capability status unverified beyond basic transport/inference probe
- Context initially bounded
- Output tokens initially bounded
- CPU-first baseline
- No model used in CI

## Owner-approved first baseline — local installation record (2026-08-05)

**Terminology:** this remains the first controlled baseline for transport,
integration preparation, safety, provenance, rollback and baseline-performance
validation. It is **not** SIONA's permanent reasoning model, a final production
model, a SIONA-native model, or a capability-approved model.

**Evidence class:** local operator evidence (artifact hashes calculated on the
operator machine). Do **not** state that GitHub independently verified local
installation.

| Field | Recorded value | Current status |
|-------|----------------|----------------|
| Runtime family | llama.cpp | Installed locally |
| Runtime version | b9968 | Artifact-verified |
| Runtime commit | `1d1d9a9ed7a4f09c4225ea4cc8fd3bd1cf2c940f` | Source pinned |
| Runtime archive | `llama-b9968-bin-win-cpu-x64.zip` | Downloaded |
| Runtime archive size | 18211732 bytes | Locally measured |
| Runtime SHA256 (locally calculated) | `f98e6690faad6a8718451d420a63cbfde6c87028beae4e7f35a36a762730cefd` | **MATCH** |
| Runtime mode | Windows x64 CPU-only | Verified at run |
| Portable extraction | completed | Outside Git |
| Runtime directory | `C:\Users\njaji\SIONA\runtimes\llama.cpp\b9968` | Present |
| Required executables | `llama-server.exe`, `llama-cli.exe` | Present |
| MIT licence copy | `LICENSE-MIT.txt` preserved beside runtime | Present |
| Model family | Qwen3-1.7B | Installed locally |
| Original model publisher | Qwen Team / Alibaba Cloud | Source pinned |
| Model repository | `ggml-org/Qwen3-1.7B-GGUF` | Downloaded |
| Repository revision | `daeb8e2d528a760970442092f6bf1e55c3b659eb` | Source pinned |
| GGUF filename | `Qwen3-1.7B-Q4_K_M.gguf` | Present |
| Published / local size | 1282439264 bytes | **MATCH** |
| Model SHA256 (locally calculated) | `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5` | **MATCH** |
| Model directory | `C:\Users\njaji\SIONA\models\Qwen3-1.7B-Q4_K_M` | Present |
| Apache-2.0 licence copy | `LICENSE-Apache-2.0.txt` preserved | Present |
| Quantizer | ggml-org | Explicit provenance |
| Host and port (executed) | `127.0.0.1:8080` | Stopped after test |
| Context size (executed) | 4096 | Recorded |
| Maximum output setting (executed) | 512 server default; probe used ≤64 | Recorded |
| CPU threads (executed) | 4 | Recorded |
| GPU layers (executed) | 0 | Recorded |
| Capability status | Unverified beyond specific observed text path; structured JSON unverified | Must remain limited |
| PATH modification | None | Confirmed |
| Firewall rule | None | Confirmed |
| Windows service | None | Confirmed |
| Scheduled auto-start | None | Confirmed |
| Registry modification | None | Confirmed |
| Download status (this baseline) | Completed under owner authorization | Local evidence |
| Installation status (this baseline) | Completed portable extract | Local evidence |
| Execution status | Limited loopback + controlled real-provider text path validated; **runtime currently stopped** | Local evidence |
| Portable rollback | Available (delete runtime/model/staging dirs; Core untouched) | Design verified |
| Rollback / fallback | Deterministic fallback verified after shutdown (EXP-3B-005); registry still inactive | Local evidence |

### Remaining authorization gate

No model-registry activation, Gate E evaluation suite, capability approval,
ADR acceptance, Phase 3B completion, or Phase 4 work may proceed without
further explicit owner authorization. Controlled text-path validation does
**not** certify production use or broad capabilities. Additional provider integration
campaigns remain unauthorized until explicitly approved.
`UNAPPROVED` for registry activation, Gate E, capability approval, and ADR acceptance.

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
