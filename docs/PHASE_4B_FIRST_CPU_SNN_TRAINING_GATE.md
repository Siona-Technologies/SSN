# Phase 4B — First CPU SNN Training Gate

**Status:** Proposed; becomes authorization for one controlled CPU training run only after this gate is merged  
**Planned experiment:** EXP-4-003  
**Task:** `phase4a-temporal-salience-v1`  
**Training backend candidate:** snnTorch 1.0.0 + PyTorch 2.13.0 CPU  
**ADR 0004:** Proposed

## Purpose

Authorize exactly one controlled local CPU training/evaluation run for SIONA's
first learned neuromorphic checkpoint, using the deterministic synthetic task
and thresholds frozen by EXP-4-001.

This gate does not accept ADR 0004 and does not integrate the learned checkpoint
into the runtime. A successful training run only establishes a candidate learned
artifact for later provider-integration verification.

## Environment boundary

The training environment must be isolated outside Git and must not alter
`requirements.txt` or the normal hosted-CI environment.

Required execution environment:

- existing CPython **3.11.x 64-bit**;
- isolated virtual environment outside Git;
- PyTorch **2.13.0+cpu** from the official PyTorch CPU wheel index;
- expected Windows x86-64 direct wheel:
  `torch-2.13.0+cpu-cp311-cp311-win_amd64.whl`;
- snnTorch **1.0.0** from the official PyPI index;
- expected direct wheel:
  `snntorch-1.0.0-py2.py3-none-any.whl`;
- CPU execution only;
- four PyTorch CPU threads;
- CUDA disabled/not claimed.

Before installation, download the two direct package wheels to an operator-local
staging directory and record their SHA-256 digests. If the resolved filenames or
versions differ from the plan, stop instead of silently substituting packages.

After installation, record `python --version`, `pip --version`,
`torch.__version__`, `snntorch.__version__`, `torch.version.cuda`,
`torch.cuda.is_available()` and `pip freeze`.

If Python 3.11 is not already available, **stop**. This gate does not authorize
installing another Python distribution.

## Resource preflight

Before dependency installation/training:

- available RAM >= 4 GiB;
- free disk for venv/staging/artifacts >= 2 GiB;
- Qwen stopped;
- llama.cpp stopped;
- port 8080 closed;
- no unrelated model/training process consuming substantial CPU/RAM;
- laptop on AC power.

Do not terminate unrelated processes automatically. Report unexpected conflicts.

## Dataset and split

Use only the committed deterministic generator:

`ssn/cognition/neuromorphic/phase4a_dataset.py`

Task config:

`config/phase4a_temporal_salience_task.json`

Frozen fingerprints:

- train: `e124d6b5858399956f7b52f1fc6e342e9d2833704b44710315d57844c43805bd`
- validation: `cfd32c4b9b2684dc10f21e9b28d169807c42ae54e7968d5080a676d602929285`
- test: `34d93878277a0b6afae880c02a3b2d878fbc142a1cfee77b51985eebbf7f4116`

If any fingerprint differs, do not train.

No private/user/company/website data and no Qwen-generated labels are authorized.

## Frozen model topology

Architecture ID: `phase4b-lif-final-membrane-v1`

```text
input event vector: 8
        ↓
Linear(8 → 16)
        ↓
snnTorch Leaky LIF
  beta = 0.9
  threshold = 1.0
  reset = subtract
  fast-sigmoid surrogate slope = 25
        ↓
final hidden membrane after 20 timesteps
        ↓
Linear(16 → 2)
        ↓
class logits
```

`beta` and threshold are fixed, not learned.

The final readout uses the hidden LIF membrane after the twentieth timestep.
This intentionally preserves temporal recency information for the late-burst
task.

## Frozen training recipe

- seed: 42007;
- CPU only;
- deterministic PyTorch algorithms enabled;
- torch CPU threads: 4;
- batch size: 32;
- optimizer: Adam;
- learning rate: 0.01;
- weight decay: 0.0001;
- loss: cross entropy over final two-class logits;
- max epochs: 80;
- minimum epochs before early stopping: 10;
- early-stopping metric: validation loss;
- patience: 12 epochs;
- minimum validation-loss improvement: 0.00001;
- gradient clipping: max norm 1.0;
- wall-clock hard limit: 600 seconds;
- test set evaluated exactly once after model selection;
- test set may not be used for hyperparameter or threshold tuning.

Best model selection must be deterministic. Select lowest validation loss;
when tied within the declared minimum delta, retain the earlier checkpoint.

## Frozen acceptance gate

A training run is accepted only if all are true:

1. test balanced accuracy >= 0.90;
2. class-0 recall >= 0.85;
3. class-1 recall >= 0.85;
4. balanced-accuracy margin over 0.50 baseline >= 0.20;
5. no test-set tuning occurred;
6. positive-class temporal sensitivity passes: mean positive score on original
   positive test sequences minus mean positive score on their time-reversed
   versions >= 0.10;
7. checkpoint/export SHA-256 is recorded;
8. dataset fingerprints match the frozen EXP-4-001 values;
9. execution remained CPU-only;
10. no tool or physical-actuator authority was added;
11. Qwen/model-registry capabilities were not changed;
12. the project `requirements.txt` was not changed.

There is no operator override that may convert a failed metric into an accepted
training result.

## Candidate artifact policy

During training, save a raw PyTorch `state_dict` only in operator-local storage
outside Git.

If and only if the run passes the full acceptance gate, export a small canonical
JSON candidate artifact containing:

- schema/artifact version;
- task ID;
- architecture ID;
- fixed LIF parameters;
- `fc1` weights and bias;
- `fc2` weights and bias;
- training backend/version metadata;
- dataset split fingerprints;
- training seed;
- accepted metrics.

The artifact must not contain absolute operator paths. Its SHA-256 must be
recorded separately in the EXP-4-003 evidence.

Do not commit a failed checkpoint or failed candidate weights.

The JSON export is a candidate for later pure-Python/provider parity work; a
successful training run does not itself prove provider integration.

## Required training evidence

EXP-4-003 must record at minimum:

- base/source SHA;
- isolated worktree/branch;
- preflight RAM/disk/CPU/runtime state;
- Python/pip versions;
- direct torch/snnTorch wheel filenames and SHA-256;
- installed dependency manifest;
- torch/snnTorch versions and CUDA availability;
- dataset fingerprints;
- exact frozen topology/training configuration;
- epoch count and stop reason;
- train/validation history summary;
- selected epoch;
- test confusion matrix;
- balanced accuracy;
- per-class recall;
- baseline margin;
- time-reversal sensitivity result;
- wall time;
- candidate artifact path class and SHA-256;
- tool/actuator authority counts/flags;
- Qwen/runtime state before and after;
- cleanup/venv status;
- computed decision: `FIRST_CPU_SNN_TRAINING_VERIFIED` or
  `FIRST_CPU_SNN_TRAINING_NOT_VERIFIED`.

Complete raw training logs may remain operator-local; committed evidence should
contain bounded summaries and hashes.

## Failure policy

Stop without improvising if:

- Python 3.11 is unavailable;
- direct dependency version/filename differs;
- a required wheel cannot be downloaded from the approved source;
- dataset fingerprints differ;
- resource preflight fails;
- deterministic-algorithm configuration fails;
- the wall-clock cap is reached;
- training becomes non-finite;
- evidence cannot distinguish validation from test evaluation.

A dependency/environment failure may be repaired under a separately documented
failure-recovery step. A metric failure must be recorded as a failed experiment
before changing topology/hyperparameters; do not silently rerun with tuned values.

## Explicit non-authorization

This gate does not authorize:

- CUDA/GPU training;
- Qwen fine-tuning, LoRA, QLoRA or PEFT;
- a SIONA-native language-model claim;
- learned-provider runtime integration;
- ADR 0004 acceptance;
- Phase 4 completion;
- physical actuation, robotics, IoT or tool execution;
- private/user/company data training;
- project-wide PyTorch/snnTorch dependency changes.

## Authorization effect

Once this gate is merged and hosted CI is green, **one controlled EXP-4-003 CPU
training/evaluation run is authorized** under the exact frozen conditions above.
