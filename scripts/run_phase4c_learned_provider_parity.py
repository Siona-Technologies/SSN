#!/usr/bin/env python3
"""EXP-4-004 local snnTorch parity runner (operator venv only; no training).

Predeclared tolerances (immutable for this experiment):
  max absolute logit difference <= 1e-5
  max absolute class-probability difference <= 1e-5
  predicted class agreement = 100%
  hidden spike-count agreement = 100%
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ssn.cognition.neuromorphic.learned_artifact import (  # noqa: E402
    APPROVED_ARTIFACT_SHA256,
    load_learned_artifact,
)
from ssn.cognition.neuromorphic.learned_inference import (  # noqa: E402
    forward_lif_final_membrane,
    parse_temporal_sequence,
)
from ssn.cognition.neuromorphic.phase4a_dataset import generate_split  # noqa: E402

MAX_ABS_LOGIT_DIFF = 1e-5
MAX_ABS_PROB_DIFF = 1e-5


def _seq_hash(sequence: Sequence[Sequence[float]]) -> str:
    blob = json.dumps([[int(v) for v in row] for row in sequence], separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _edge_controls() -> List[Dict[str, Any]]:
    zero = [[0 for _ in range(8)] for _ in range(20)]
    early = [row[:] for row in zero]
    early[0][0] = 1
    late = [row[:] for row in zero]
    late[19][7] = 1
    full_late = [row[:] for row in zero]
    full_late[19] = [1 for _ in range(8)]
    ones = [[1 for _ in range(8)] for _ in range(20)]
    return [
        {"sample_id": "edge:all_zero", "sequence": zero},
        {"sample_id": "edge:one_early", "sequence": early},
        {"sample_id": "edge:one_late", "sequence": late},
        {"sample_id": "edge:full_final_timestep", "sequence": full_late},
        {"sample_id": "edge:all_one", "sequence": ones},
    ]


def _build_torch_model(artifact: Dict[str, Any]):
    import torch
    import torch.nn as nn
    import snntorch as snn
    from snntorch import surrogate

    class TemporalSalienceSNN(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.fc1 = nn.Linear(8, 16)
            self.lif1 = snn.Leaky(
                beta=0.9,
                threshold=1.0,
                spike_grad=surrogate.fast_sigmoid(slope=25.0),
                reset_mechanism="subtract",
                learn_beta=False,
                learn_threshold=False,
            )
            self.fc2 = nn.Linear(16, 2)

        def forward(self, x: "torch.Tensor") -> Tuple["torch.Tensor", int]:
            mem = self.lif1.init_leaky()
            spike_count = 0
            for step in range(20):
                current = self.fc1(x[:, step, :])
                spk, mem = self.lif1(current, mem)
                spike_count += int(spk.sum().item())
            return self.fc2(mem), spike_count

    model = TemporalSalienceSNN()
    weights = artifact["weights"]
    with torch.no_grad():
        model.fc1.weight.copy_(torch.tensor(weights["fc1.weight"], dtype=torch.float32))
        model.fc1.bias.copy_(torch.tensor(weights["fc1.bias"], dtype=torch.float32))
        model.fc2.weight.copy_(torch.tensor(weights["fc2.weight"], dtype=torch.float32))
        model.fc2.bias.copy_(torch.tensor(weights["fc2.bias"], dtype=torch.float32))
    model.eval()
    return model, torch


def run_parity() -> Dict[str, Any]:
    import torch

    artifact = load_learned_artifact()
    model, torch_mod = _build_torch_model(artifact)
    weights = artifact["weights"]

    records: List[Dict[str, Any]] = []
    groups = {
        "held_out_test": [],
        "reversed_positive": [],
        "edge_controls": [],
    }

    for sample in generate_split("test"):
        groups["held_out_test"].append(
            {"sample_id": sample.sample_id, "sequence": [list(r) for r in sample.sequence], "label": sample.label}
        )
        if sample.label == 1:
            reversed_seq = [list(r) for r in reversed(sample.sequence)]
            groups["reversed_positive"].append(
                {
                    "sample_id": f"rev:{sample.sample_id}",
                    "sequence": reversed_seq,
                    "label": 1,
                }
            )
    groups["edge_controls"] = _edge_controls()

    max_logit = 0.0
    max_prob = 0.0
    class_agree = 0
    spike_agree = 0
    total = 0

    for group_name, items in groups.items():
        for item in items:
            seq = item["sequence"]
            pure = forward_lif_final_membrane(
                parse_temporal_sequence(seq),
                fc1_weight=weights["fc1.weight"],
                fc1_bias=weights["fc1.bias"],
                fc2_weight=weights["fc2.weight"],
                fc2_bias=weights["fc2.bias"],
            )
            x = torch_mod.tensor([seq], dtype=torch_mod.float32)
            with torch_mod.no_grad():
                logits, spike_count = model(x)
                probs = torch_mod.softmax(logits, dim=1)[0]
                pred = int(logits[0].argmax().item())
            ref_logits = (float(logits[0, 0]), float(logits[0, 1]))
            ref_probs = (float(probs[0]), float(probs[1]))
            d_logit = max(abs(pure["logits"][0] - ref_logits[0]), abs(pure["logits"][1] - ref_logits[1]))
            d_prob = max(
                abs(pure["probabilities"][0] - ref_probs[0]),
                abs(pure["probabilities"][1] - ref_probs[1]),
            )
            max_logit = max(max_logit, d_logit)
            max_prob = max(max_prob, d_prob)
            class_ok = int(pure["predicted_class"] == pred)
            spike_ok = int(pure["hidden_spike_count"] == spike_count)
            class_agree += class_ok
            spike_agree += spike_ok
            total += 1
            records.append(
                {
                    "group": group_name,
                    "sample_id": item["sample_id"],
                    "input_sha256": _seq_hash(seq),
                    "ref_logits": ref_logits,
                    "ref_probabilities": ref_probs,
                    "ref_predicted_class": pred,
                    "ref_hidden_spike_count": spike_count,
                    "pure_logits": pure["logits"],
                    "pure_probabilities": pure["probabilities"],
                    "pure_predicted_class": pure["predicted_class"],
                    "pure_hidden_spike_count": pure["hidden_spike_count"],
                    "abs_logit_diff": d_logit,
                    "abs_prob_diff": d_prob,
                }
            )

    expected_total = 128 + 64 + 5
    checks = {
        "artifact_sha_match": artifact["sha256"] == APPROVED_ARTIFACT_SHA256,
        "sample_count": total == expected_total,
        "max_logit_ok": max_logit <= MAX_ABS_LOGIT_DIFF,
        "max_prob_ok": max_prob <= MAX_ABS_PROB_DIFF,
        "class_agreement": class_agree == total,
        "spike_agreement": spike_agree == total,
        "cuda_false": (not torch.cuda.is_available()) and (torch.version.cuda is None),
    }
    verified = all(checks.values())
    decision = (
        "LEARNED_SNN_PROVIDER_PARITY_VERIFIED"
        if verified
        else "LEARNED_SNN_PROVIDER_PARITY_NOT_VERIFIED"
    )

    # Compact fixture subset for hosted CI
    fixture_ids = []
    # one class 0, one class 1 from held-out
    for item in groups["held_out_test"]:
        if item.get("label") == 0 and "class0" not in fixture_ids:
            fixture_ids.append(("held_out_test", item["sample_id"], "class0"))
        if item.get("label") == 1 and "class1" not in [x[2] for x in fixture_ids]:
            fixture_ids.append(("held_out_test", item["sample_id"], "class1"))
        if len(fixture_ids) >= 2:
            break
    fixture_ids.append(("reversed_positive", groups["reversed_positive"][0]["sample_id"], "reversed_positive"))
    fixture_ids.append(("edge_controls", "edge:all_zero", "all_zero"))
    fixture_ids.append(("edge_controls", "edge:full_final_timestep", "full_late"))

    fixture_samples = []
    by_id = {r["sample_id"]: r for r in records}
    for _group, sample_id, tag in fixture_ids:
        rec = by_id[sample_id]
        fixture_samples.append(
            {
                "tag": tag,
                "sample_id": sample_id,
                "group": rec["group"],
                "input_sha256": rec["input_sha256"],
                "reference_logits": list(rec["ref_logits"]),
                "reference_probabilities": list(rec["ref_probabilities"]),
                "predicted_class": rec["ref_predicted_class"],
                "hidden_spike_count": rec["ref_hidden_spike_count"],
            }
        )
        # include reproducible input for CI (small)
        for group_items in groups.values():
            for item in group_items:
                if item["sample_id"] == sample_id:
                    fixture_samples[-1]["sequence"] = item["sequence"]
                    break

    return {
        "decision": decision,
        "checks": checks,
        "counts": {
            "held_out_test": len(groups["held_out_test"]),
            "reversed_positive": len(groups["reversed_positive"]),
            "edge_controls": len(groups["edge_controls"]),
            "total": total,
            "expected_total": expected_total,
        },
        "max_abs_logit_difference": max_logit,
        "max_abs_probability_difference": max_prob,
        "predicted_class_agreement": {"count": class_agree, "rate": class_agree / total},
        "spike_count_agreement": {"count": spike_agree, "rate": spike_agree / total},
        "stack": {
            "python": platform.python_version(),
            "torch": str(torch.__version__),
            "snntorch": __import__("snntorch").__version__,
            "cuda_version": str(torch.version.cuda),
            "cuda_available": bool(torch.cuda.is_available()),
        },
        "artifact_sha256": artifact["sha256"],
        "tolerances": {
            "max_abs_logit_difference": MAX_ABS_LOGIT_DIFF,
            "max_abs_probability_difference": MAX_ABS_PROB_DIFF,
        },
        "fixture": {
            "schema_version": 1,
            "experiment_id": "EXP-4-004",
            "artifact_sha256": APPROVED_ARTIFACT_SHA256,
            "tolerances": {
                "max_abs_logit_difference": MAX_ABS_LOGIT_DIFF,
                "max_abs_probability_difference": MAX_ABS_PROB_DIFF,
            },
            "samples": fixture_samples,
        },
        "records_sha256": hashlib.sha256(
            json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--fixture-json", type=Path, required=True)
    args = parser.parse_args()
    result = run_parity()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    # Strip bulky fixture from evidence payload duplicate
    evidence = {k: v for k, v in result.items() if k != "fixture"}
    evidence["fixture_sample_count"] = len(result["fixture"]["samples"])
    args.output_json.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.fixture_json.write_text(json.dumps(result["fixture"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "checks": result["checks"], "counts": result["counts"]}, indent=2))
    return 0 if result["decision"] == "LEARNED_SNN_PROVIDER_PARITY_VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
