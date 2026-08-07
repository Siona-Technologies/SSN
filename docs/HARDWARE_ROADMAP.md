# Hardware Roadmap

## Confirmed current machine

| Item | Value |
|------|--------|
| CPU | Intel Core i7-1165G7 |
| Cores/threads | 4 cores / 8 logical processors |
| GPU | Intel Iris Xe integrated graphics |
| CUDA-capable NVIDIA GPU | **No** |
| RAM | Not fully normalized in this hardware record |
| Storage | Not fully normalized in this hardware record |

Do not invent missing normalized hardware values from transient free-memory or
free-disk observations.

## What can run now

- Full offline CI (`SSN_OFFLINE=1`)
- Dummy / deterministic language providers
- Optional local Qwen CPU baseline when explicitly started under its Phase 3 boundaries
- Deterministic CPU neuromorphic provider
- Accepted learned software SNN provider `siona-neuro-learned-lif-v1` using pure-Python CPU inference
- Event bus, workspace, bridges, CLI, HTTP Front Door
- Mock embodiment (simulation only)

The accepted Phase 4 SNN training run was CPU-only. The normal learned-provider
runtime does not require PyTorch/snnTorch.

## CPU-only baseline

Accepted Phase 1–4 local cognitive paths are CPU-capable by default. CUDA is not
required for the accepted software architecture.

## Hardware-gated tests

Future CUDA SNN training/benchmarking, larger accelerated LLM experiments,
Loihi/FPGA execution and Isaac Sim tests remain hardware-gated and must not be
inferred from CPU results.

No GPU/neuromorphic-silicon or measured-energy claim exists for the accepted
Phase 4 SNN provider.

## Future workstation purchase triggers

Purchase consideration only when all of the following are true:

1. The selected future hardware experiment has a governed objective and metrics.
2. Software/provider contracts required by that experiment are stable.
3. CPU evidence is insufficient for the specific question being tested.
4. Owner-approved budget and safety review exist for physical/IoT work where applicable.

Do **not** recommend a specific machine merely because Phase 4 completed.

## Future categories (unsequenced)

- CUDA workstation for explicitly authorized SNN/LLM acceleration experiments
- Neuromorphic/FPGA hardware for separately governed spike-execution experiments
- Robotics/simulation workstation when embodiment work is authorized
- Optional cluster/cloud compute for separately governed distributed experiments

## Portability rule

Code must remain hardware-portable: providers behind interfaces, offline
defaults, no hard CUDA/PyTorch import in normal learned-provider module import
paths.
