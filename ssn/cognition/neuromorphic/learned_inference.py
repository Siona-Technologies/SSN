"""Pure-Python inference for phase4b-lif-final-membrane-v1.

Reproduces snnTorch 1.0.0 Leaky semantics with:
- beta decay + input integration
- reset_mechanism='subtract'
- reset_delay=True (reset from previous membrane applied during state update)
- forward spike = Heaviside(mem > threshold) as used by fast_sigmoid forward

No torch/snnTorch/numpy dependency.
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

TIMESTEPS = 20
INPUT_FEATURES = 8
HIDDEN_UNITS = 16
OUTPUT_CLASSES = 2


class LearnedNeuromorphicInferenceError(ValueError):
    """Invalid learned temporal sequence for pure-Python inference."""


def _dot(row: Sequence[float], vec: Sequence[float]) -> float:
    return sum(float(a) * float(b) for a, b in zip(row, vec))


def _linear(weight: Sequence[Sequence[float]], bias: Sequence[float], x: Sequence[float]) -> List[float]:
    return [_dot(row, x) + float(b) for row, b in zip(weight, bias)]


def _softmax(logits: Sequence[float]) -> List[float]:
    peak = max(float(v) for v in logits)
    exps = [math.exp(float(v) - peak) for v in logits]
    total = sum(exps)
    if total == 0.0:
        raise LearnedNeuromorphicInferenceError("softmax_degenerate")
    return [v / total for v in exps]


def parse_temporal_sequence(sequence: object) -> Tuple[Tuple[float, ...], ...]:
    if not isinstance(sequence, (list, tuple)):
        raise LearnedNeuromorphicInferenceError("temporal_sequence_not_list")
    if len(sequence) != TIMESTEPS:
        raise LearnedNeuromorphicInferenceError("temporal_sequence_timesteps")
    rows: List[Tuple[float, ...]] = []
    for row in sequence:
        if not isinstance(row, (list, tuple)) or len(row) != INPUT_FEATURES:
            raise LearnedNeuromorphicInferenceError("temporal_sequence_shape")
        parsed: List[float] = []
        for value in row:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise LearnedNeuromorphicInferenceError("temporal_sequence_non_binary_numeric")
            number = float(value)
            if not math.isfinite(number) or number not in (0.0, 1.0):
                raise LearnedNeuromorphicInferenceError("temporal_sequence_non_binary_numeric")
            parsed.append(number)
        rows.append(tuple(parsed))
    return tuple(rows)


def forward_lif_final_membrane(
    sequence: Sequence[Sequence[float]],
    *,
    fc1_weight: Sequence[Sequence[float]],
    fc1_bias: Sequence[float],
    fc2_weight: Sequence[Sequence[float]],
    fc2_bias: Sequence[float],
    beta: float = 0.9,
    threshold: float = 1.0,
) -> Dict[str, object]:
    """Run exact EXP-4-003 architecture on one 20x8 binary sequence."""
    if len(sequence) != TIMESTEPS:
        raise LearnedNeuromorphicInferenceError("temporal_sequence_timesteps")
    mem = [0.0] * HIDDEN_UNITS
    spike_count = 0
    for step in range(TIMESTEPS):
        current = _linear(fc1_weight, fc1_bias, sequence[step])
        # reset_delay=True: reset signal from previous membrane
        reset = [1.0 if m > threshold else 0.0 for m in mem]
        mem = [beta * m + inj - r * threshold for m, inj, r in zip(mem, current, reset)]
        spikes = [1.0 if m > threshold else 0.0 for m in mem]
        spike_count += int(sum(spikes))

    logits = _linear(fc2_weight, fc2_bias, mem)
    probs = _softmax(logits)
    # Match torch.argmax: first index of maximum.
    predicted = 0 if logits[0] >= logits[1] else 1
    return {
        "logits": (float(logits[0]), float(logits[1])),
        "probabilities": (float(probs[0]), float(probs[1])),
        "predicted_class": int(predicted),
        "positive_score": float(probs[1]),
        "hidden_spike_count": int(spike_count),
        "final_membrane": tuple(float(v) for v in mem),
    }
