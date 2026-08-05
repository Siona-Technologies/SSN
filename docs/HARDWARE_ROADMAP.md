# Hardware Roadmap

## Confirmed current machine

| Item | Value |
|------|--------|
| CPU | Intel Core i7-1165G7 |
| Cores/threads | 4 cores / 8 logical processors |
| GPU | Intel Iris Xe integrated graphics |
| CUDA-capable NVIDIA GPU | **No** |
| RAM | Not yet confirmed |
| Storage | Not yet confirmed |

Do not invent missing RAM or storage values.

## What can run now

- Full offline CI (`SSN_OFFLINE=1`)
- Dummy / deterministic language providers
- Deterministic CPU neuromorphic provider
- Event bus, workspace, bridges, CLI, HTTP Front Door
- Mock embodiment (simulation only)

## CPU-only

All Phase 1–2 cognitive paths are CPU-only by default. No CUDA required.

## Hardware-gated tests

Any future CUDA SNN / large LLM / Isaac Sim tests must be marked hardware-gated and skipped on this machine.

## Future workstation purchase triggers

Purchase consideration only when all of the following are true:

1. Software contracts for neuromorphic + model providers are stable.
2. Evaluation datasets and metrics are defined.
3. Owner-approved budget and safety review for physical/IoT work (if applicable).

Do **not** recommend a specific machine in this phase.

## Future categories (progression)

1. CUDA workstation for SNN/LLM experiments
2. Robotics/sim workstation (Isaac-capable)
3. Optional small cluster for distributed experiments

## Portability rule

Code must remain hardware-portable: providers behind interfaces, offline defaults, no hard CUDA import at module import time.
