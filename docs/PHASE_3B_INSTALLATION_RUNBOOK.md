# Phase 3B — Installation Runbook

**Status:** planning only — **no install authorized by this document**  
**Rule:** each destructive or state-changing step requires **explicit approval** before execution

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

## Unapproved selection placeholders

Fill only after owner approval. Current values are placeholders.

| Placeholder | Value | Approval status |
|-------------|-------|-----------------|
| Exact selected runtime version | `UNAPPROVED — e.g. llama.cpp bXXXX` | Not approved |
| Runtime download artefact | `UNAPPROVED — e.g. llama-bXXXX-bin-win-cpu-x64.zip` | Not approved |
| Official runtime SHA256 | `UNAPPROVED` | Not approved |
| Runtime controlled installation directory | `UNAPPROVED — e.g. C:\Users\njaji\Tools\llama.cpp-bXXXX` | Not approved |
| Exact selected model repository | `UNAPPROVED — e.g. Qwen/Qwen3-1.7B-GGUF or ggml-org/Qwen3-1.7B-GGUF` | Not approved |
| Exact GGUF filename | `UNAPPROVED` | Not approved |
| Model SHA256 | `UNAPPROVED` | Not approved |
| Model storage directory | `UNAPPROVED — on C: capacity-approved path` | Not approved |
| Initial server host and port | `UNAPPROVED — provisional intent 127.0.0.1:8080` | Not approved |
| Initial context size | `UNAPPROVED — provisional intent 2048 or 4096` | Not approved |
| Initial maximum output tokens | `UNAPPROVED — provisional intent bounded (e.g. 256–512)` | Not approved |
| CPU thread count | `UNAPPROVED — provisional intent ≤8` | Not approved |
| GPU-layer count | `UNAPPROVED — provisional intent 0 for CPU baseline` | Not approved |
| Rollback commands | `UNAPPROVED — stop process; delete runtime dir; delete GGUF; restore registry mock` | Not approved |

**No commands in this table may be executed until owner approval is recorded.**

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
