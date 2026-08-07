#!/usr/bin/env python3
"""Controlled EXP-4-003 CPU SNN training/evaluation runner.

The training stack is imported lazily so hosted CI can validate the frozen plan
without installing PyTorch or snnTorch. Real execution is authorized only by the
merged Phase 4B training gate and must use an isolated local Python 3.11 venv.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import sys
import time
from typing import Any, Dict, Iterable, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "config" / "phase4b_cpu_snn_training_plan.json"
TASK_PATH = ROOT / "config" / "phase4a_temporal_salience_task.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ssn.cognition.neuromorphic.phase4a_dataset import (  # noqa: E402
    generate_split,
    split_fingerprint,
)


class TrainingGateError(RuntimeError):
    pass


def _read_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TrainingGateError(f"expected JSON object: {path.name}")
    return data


def validate_plan() -> Dict[str, Any]:
    plan = _read_json(PLAN_PATH)
    task = _read_json(TASK_PATH)
    if plan.get("execution_experiment_id") != "EXP-4-003":
        raise TrainingGateError("unexpected execution experiment ID")
    if plan.get("task_id") != task.get("task_id"):
        raise TrainingGateError("task ID mismatch")
    if plan["environment"]["required_python"] != "3.11.x 64-bit":
        raise TrainingGateError("Python gate drift")
    bootstrap = plan["environment"].get("python_bootstrap")
    if not isinstance(bootstrap, dict):
        raise TrainingGateError("python_bootstrap gate missing")
    if bootstrap.get("allowed_if_missing") is not True:
        raise TrainingGateError("python bootstrap must be allowed only when missing")
    if bootstrap.get("one_controlled_installation") is not True:
        raise TrainingGateError("python bootstrap must remain one controlled installation")
    if bootstrap.get("required_family") != "CPython":
        raise TrainingGateError("python bootstrap family drift")
    if bootstrap.get("required_version") != "3.11.x":
        raise TrainingGateError("python bootstrap version drift")
    if bootstrap.get("required_architecture") != "x64":
        raise TrainingGateError("python bootstrap architecture drift")
    if bootstrap.get("preferred_package_manager") != "winget":
        raise TrainingGateError("python bootstrap package manager drift")
    if bootstrap.get("package_id") != "Python.Python.3.11":
        raise TrainingGateError("python bootstrap package ID drift")
    if bootstrap.get("scope") != "user":
        raise TrainingGateError("python bootstrap scope drift")
    if bootstrap.get("side_by_side_only") is not True:
        raise TrainingGateError("python bootstrap must remain side-by-side only")
    if bootstrap.get("may_uninstall_existing_python") is not False:
        raise TrainingGateError("python bootstrap must not uninstall existing Python")
    if bootstrap.get("may_modify_qgis_python") is not False:
        raise TrainingGateError("python bootstrap must not modify QGIS Python")
    if bootstrap.get("may_manually_edit_path") is not False:
        raise TrainingGateError("python bootstrap must not manually edit PATH")
    if bootstrap.get("may_change_global_default_python") is not False:
        raise TrainingGateError("python bootstrap must not change global default Python")
    if bootstrap.get("verify_python_launcher_registration") is not True:
        raise TrainingGateError("python launcher verification required")
    if bootstrap.get("verify_existing_python314_still_available") is not True:
        raise TrainingGateError("Python 3.14 preservation verification required")
    if bootstrap.get("training_may_resume_only_after_verification") is not True:
        raise TrainingGateError("training resume must wait for python verification")
    if bootstrap.get("bootstrap_does_not_consume_training_run") is not True:
        raise TrainingGateError("bootstrap must not consume the training run")
    if plan["environment"]["torch"]["version"] != "2.13.0+cpu":
        raise TrainingGateError("PyTorch version drift")
    if plan["environment"]["snntorch"]["version"] != "1.0.0":
        raise TrainingGateError("snnTorch version drift")
    if plan["execution"]["cuda_allowed"] is not False:
        raise TrainingGateError("CUDA must remain disabled")
    if plan["execution"]["one_controlled_training_run_authorized_after_merge"] is not True:
        raise TrainingGateError("one-run authorization drift")
    if plan["environment"]["project_requirements_file_must_remain_unchanged"] is not True:
        raise TrainingGateError("project requirements boundary missing")
    expected_fingerprints = {
        "train": "e124d6b5858399956f7b52f1fc6e342e9d2833704b44710315d57844c43805bd",
        "validation": "cfd32c4b9b2684dc10f21e9b28d169807c42ae54e7968d5080a676d602929285",
        "test": "34d93878277a0b6afae880c02a3b2d878fbc142a1cfee77b51985eebbf7f4116",
    }
    actual = {split: split_fingerprint(split) for split in expected_fingerprints}
    if actual != expected_fingerprints:
        raise TrainingGateError("dataset fingerprint drift")
    return {
        "plan_id": plan["gate_id"],
        "experiment_id": plan["execution_experiment_id"],
        "task_id": plan["task_id"],
        "dataset_fingerprints": actual,
        "training_stack_required": True,
        "training_executed": False,
        "plan_valid": True,
    }


def _load_training_stack():
    try:
        import torch
        import torch.nn as nn
        import snntorch as snn
        from snntorch import surrogate
    except Exception as exc:  # pragma: no cover - only real training environment
        raise TrainingGateError(f"training stack unavailable: {type(exc).__name__}: {exc}") from exc
    return torch, nn, snn, surrogate


def _balanced_accuracy(labels: Sequence[int], preds: Sequence[int]) -> Tuple[float, Dict[str, float]]:
    recalls: Dict[str, float] = {}
    for cls in (0, 1):
        idx = [i for i, label in enumerate(labels) if label == cls]
        if not idx:
            raise TrainingGateError(f"missing class {cls}")
        recalls[str(cls)] = sum(preds[i] == cls for i in idx) / len(idx)
    return (recalls["0"] + recalls["1"]) / 2.0, recalls


def _tensor_dataset(torch, split: str):
    samples = generate_split(split)
    x = torch.tensor([sample.sequence for sample in samples], dtype=torch.float32)
    y = torch.tensor([sample.label for sample in samples], dtype=torch.long)
    return x, y


def _build_model(torch, nn, snn, surrogate, plan: Dict[str, Any]):
    model_cfg = plan["model"]

    class TemporalSalienceSNN(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = nn.Linear(model_cfg["input_features"], model_cfg["hidden_units"])
            self.lif1 = snn.Leaky(
                beta=float(model_cfg["beta"]),
                threshold=float(model_cfg["threshold"]),
                spike_grad=surrogate.fast_sigmoid(slope=float(model_cfg["surrogate_slope"])),
                reset_mechanism=model_cfg["reset_mechanism"],
                learn_beta=bool(model_cfg["learn_beta"]),
                learn_threshold=bool(model_cfg["learn_threshold"]),
            )
            self.fc2 = nn.Linear(model_cfg["hidden_units"], model_cfg["output_classes"])

        def forward(self, x):
            if x.ndim != 3 or x.shape[1] != model_cfg["timesteps"] or x.shape[2] != model_cfg["input_features"]:
                raise TrainingGateError(f"unexpected input shape: {tuple(x.shape)}")
            mem = self.lif1.init_leaky()
            for step in range(model_cfg["timesteps"]):
                current = self.fc1(x[:, step, :])
                _spike, mem = self.lif1(current, mem)
            return self.fc2(mem)

    return TemporalSalienceSNN()


def _evaluate(torch, model, x, y, loss_fn) -> Dict[str, Any]:
    model.eval()
    with torch.no_grad():
        logits = model(x)
        loss = float(loss_fn(logits, y).item())
        probs = torch.softmax(logits, dim=1)
        preds = probs.argmax(dim=1)
    labels_list = [int(v) for v in y.tolist()]
    preds_list = [int(v) for v in preds.tolist()]
    bal_acc, recalls = _balanced_accuracy(labels_list, preds_list)
    confusion = [[0, 0], [0, 0]]
    for truth, pred in zip(labels_list, preds_list):
        confusion[truth][pred] += 1
    return {
        "loss": loss,
        "balanced_accuracy": bal_acc,
        "recall": recalls,
        "confusion_matrix": confusion,
        "positive_probabilities": [float(v) for v in probs[:, 1].tolist()],
    }


def _canonical_artifact(model, plan: Dict[str, Any], fingerprints: Dict[str, str], metrics: Dict[str, Any], stack: Dict[str, str]) -> Dict[str, Any]:
    state = model.state_dict()
    return {
        "schema_version": 1,
        "artifact_type": "SIONA_LEARNED_NEUROMORPHIC_CANDIDATE",
        "provider_target": "siona-neuro-learned-lif-v1",
        "task_id": plan["task_id"],
        "architecture_id": plan["model"]["architecture_id"],
        "training_experiment": plan["execution_experiment_id"],
        "backend": stack,
        "dataset_fingerprints": fingerprints,
        "training_seed": plan["training"]["seed"],
        "lif": {
            "beta": plan["model"]["beta"],
            "threshold": plan["model"]["threshold"],
            "reset_mechanism": plan["model"]["reset_mechanism"],
            "surrogate": plan["model"]["surrogate"],
            "surrogate_slope": plan["model"]["surrogate_slope"],
            "learn_beta": plan["model"]["learn_beta"],
            "learn_threshold": plan["model"]["learn_threshold"],
        },
        "weights": {
            "fc1.weight": state["fc1.weight"].detach().cpu().tolist(),
            "fc1.bias": state["fc1.bias"].detach().cpu().tolist(),
            "fc2.weight": state["fc2.weight"].detach().cpu().tolist(),
            "fc2.bias": state["fc2.bias"].detach().cpu().tolist(),
        },
        "accepted_metrics": metrics,
        "tool_authority": False,
        "physical_actuation_authority": False,
    }


def run_training(args: argparse.Namespace) -> int:  # pragma: no cover - controlled local execution
    plan = _read_json(PLAN_PATH)
    validate_plan()

    if sys.version_info[:2] != (3, 11) or platform.architecture()[0] != "64bit":
        raise TrainingGateError(f"requires CPython 3.11 x64; got {platform.python_version()} {platform.architecture()[0]}")

    torch, nn, snn, surrogate = _load_training_stack()
    if str(torch.__version__) != "2.13.0+cpu":
        raise TrainingGateError(f"unexpected torch version: {torch.__version__}")
    if str(getattr(snn, "__version__", "")) != "1.0.0":
        raise TrainingGateError(f"unexpected snntorch version: {getattr(snn, '__version__', None)}")
    if torch.cuda.is_available() or torch.version.cuda is not None:
        raise TrainingGateError("CUDA-capable build/runtime is outside this CPU gate")

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if str(ROOT).lower() in str(output_dir).lower():
        raise TrainingGateError("raw training output must be outside the Git worktree")

    seed = int(plan["training"]["seed"])
    random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(int(plan["resource_preflight"]["torch_threads"]))
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass

    fingerprints = {split: split_fingerprint(split) for split in ("train", "validation", "test")}
    x_train, y_train = _tensor_dataset(torch, "train")
    x_val, y_val = _tensor_dataset(torch, "validation")
    x_test, y_test = _tensor_dataset(torch, "test")

    model = _build_model(torch, nn, snn, surrogate, plan)
    loss_fn = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=float(plan["training"]["learning_rate"]),
        weight_decay=float(plan["training"]["weight_decay"]),
    )

    dataset = torch.utils.data.TensorDataset(x_train, y_train)
    generator = torch.Generator().manual_seed(seed)
    loader = torch.utils.data.DataLoader(
        dataset,
        batch_size=int(plan["training"]["batch_size"]),
        shuffle=True,
        generator=generator,
        num_workers=0,
        drop_last=False,
    )

    max_epochs = int(plan["training"]["max_epochs"])
    min_epochs = int(plan["training"]["minimum_epochs_before_early_stop"])
    patience = int(plan["training"]["early_stopping_patience"])
    min_delta = float(plan["training"]["early_stopping_min_delta"])
    clip = float(plan["training"]["gradient_clip_norm"])
    wall_limit = float(plan["training"]["max_wall_clock_seconds"])

    history: List[Dict[str, float]] = []
    best_state = None
    best_val_loss = math.inf
    best_epoch = 0
    stale_epochs = 0
    started = time.perf_counter()
    stop_reason = "max_epochs"

    for epoch in range(1, max_epochs + 1):
        if time.perf_counter() - started > wall_limit:
            raise TrainingGateError("wall-clock training limit exceeded")
        model.train()
        train_loss_sum = 0.0
        train_count = 0
        for xb, yb in loader:
            optimizer.zero_grad(set_to_none=True)
            logits = model(xb)
            loss = loss_fn(logits, yb)
            if not torch.isfinite(loss):
                raise TrainingGateError("non-finite training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=clip)
            optimizer.step()
            train_loss_sum += float(loss.item()) * len(yb)
            train_count += len(yb)

        val = _evaluate(torch, model, x_val, y_val, loss_fn)
        train_loss = train_loss_sum / max(train_count, 1)
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "validation_loss": val["loss"],
                "validation_balanced_accuracy": val["balanced_accuracy"],
            }
        )

        if val["loss"] < best_val_loss - min_delta:
            best_val_loss = val["loss"]
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
            stale_epochs = 0
        else:
            stale_epochs += 1

        if epoch >= min_epochs and stale_epochs >= patience:
            stop_reason = "early_stopping_validation_loss"
            break

    if best_state is None:
        raise TrainingGateError("no best checkpoint selected")
    model.load_state_dict(best_state)

    # The held-out test set is evaluated exactly once after model selection.
    test = _evaluate(torch, model, x_test, y_test, loss_fn)
    positive_idx = [i for i, value in enumerate(y_test.tolist()) if int(value) == 1]
    x_positive = x_test[positive_idx]
    model.eval()
    with torch.no_grad():
        original_score = torch.softmax(model(x_positive), dim=1)[:, 1].mean().item()
        reversed_score = torch.softmax(model(torch.flip(x_positive, dims=[1])), dim=1)[:, 1].mean().item()
    reversal_drop = float(original_score - reversed_score)

    thresholds = plan["acceptance"]
    margin = float(test["balanced_accuracy"] - thresholds["balanced_random_baseline"])
    checks = {
        "balanced_accuracy": test["balanced_accuracy"] >= thresholds["test_balanced_accuracy_min"],
        "class0_recall": test["recall"]["0"] >= thresholds["per_class_recall_min"],
        "class1_recall": test["recall"]["1"] >= thresholds["per_class_recall_min"],
        "baseline_margin": margin >= thresholds["margin_over_balanced_random_min"],
        "time_reversal": reversal_drop >= thresholds["time_reversal_positive_score_drop_min"],
    }
    accepted = all(checks.values())
    decision = "FIRST_CPU_SNN_TRAINING_VERIFIED" if accepted else "FIRST_CPU_SNN_TRAINING_NOT_VERIFIED"

    elapsed = time.perf_counter() - started
    stack = {
        "python": platform.python_version(),
        "torch": str(torch.__version__),
        "snntorch": str(getattr(snn, "__version__", "unknown")),
        "cuda_version": str(torch.version.cuda),
        "cuda_available": bool(torch.cuda.is_available()),
    }
    metrics = {
        "selected_epoch": best_epoch,
        "stop_reason": stop_reason,
        "epochs_executed": len(history),
        "test_loss": test["loss"],
        "test_balanced_accuracy": test["balanced_accuracy"],
        "per_class_recall": test["recall"],
        "confusion_matrix": test["confusion_matrix"],
        "margin_over_baseline": margin,
        "positive_score_original_mean": original_score,
        "positive_score_reversed_mean": reversed_score,
        "time_reversal_positive_score_drop": reversal_drop,
        "acceptance_checks": checks,
        "wall_seconds": elapsed,
    }

    raw_state_path = output_dir / "exp4-003-best-state.pt"
    torch.save(model.state_dict(), raw_state_path)
    raw_state_sha = hashlib.sha256(raw_state_path.read_bytes()).hexdigest()

    artifact = _canonical_artifact(model, plan, fingerprints, metrics, stack)
    artifact_blob = json.dumps(artifact, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    artifact_sha = hashlib.sha256(artifact_blob).hexdigest()
    artifact_path = output_dir / "exp4-003-candidate-artifact.json"
    artifact_path.write_bytes(artifact_blob)

    result = {
        "experiment_id": "EXP-4-003",
        "decision": decision,
        "accepted": accepted,
        "plan_id": plan["gate_id"],
        "task_id": plan["task_id"],
        "stack": stack,
        "dataset_fingerprints": fingerprints,
        "metrics": metrics,
        "raw_state_sha256": raw_state_sha,
        "candidate_artifact_sha256": artifact_sha,
        "candidate_artifact_commit_allowed": accepted,
        "torch_wheel_filename": args.torch_wheel_filename,
        "torch_wheel_sha256": args.torch_wheel_sha256,
        "snntorch_wheel_filename": args.snntorch_wheel_filename,
        "snntorch_wheel_sha256": args.snntorch_wheel_sha256,
        "tool_authority": False,
        "physical_actuation_authority": False,
        "qwen_used": False,
        "cuda_used": False,
        "absolute_operator_paths_committed": False,
    }
    result_path = output_dir / "exp4-003-local-result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    history_path = output_dir / "exp4-003-training-history.json"
    history_path.write_text(json.dumps(history, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if accepted else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-plan", action="store_true")
    parser.add_argument("--output-dir")
    parser.add_argument("--torch-wheel-filename")
    parser.add_argument("--torch-wheel-sha256")
    parser.add_argument("--snntorch-wheel-filename")
    parser.add_argument("--snntorch-wheel-sha256")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.validate_plan:
        print(json.dumps(validate_plan(), indent=2, sort_keys=True))
        return 0
    required = (
        "output_dir",
        "torch_wheel_filename",
        "torch_wheel_sha256",
        "snntorch_wheel_filename",
        "snntorch_wheel_sha256",
    )
    missing = [name for name in required if not getattr(args, name)]
    if missing:
        raise TrainingGateError(f"missing required execution arguments: {', '.join(missing)}")
    return run_training(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TrainingGateError as exc:
        print(f"TRAINING_GATE_ERROR: {exc}", file=sys.stderr)
        raise SystemExit(3)
