"""Deterministic synthetic temporal-salience dataset for Phase 4A readiness.

This module intentionally has no PyTorch/snnTorch/Norse dependency. It defines
training-data scaffolding only; importing or using it does not authorize or run
SNN training.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import random
from typing import Dict, List, Sequence, Tuple

TIMESTEPS = 20
CHANNELS = 8
EVENTS_PER_SAMPLE = 16
LATE_TIMESTEPS = (16, 17, 18, 19)
POSITIVE_LATE_EVENTS = 12
ROOT_SEED = 42007
SPLIT_SIZES: Dict[str, int] = {"train": 256, "validation": 64, "test": 128}


@dataclass(frozen=True)
class TemporalSalienceSample:
    sample_id: str
    split: str
    label: int
    sequence: Tuple[Tuple[int, ...], ...]

    @property
    def event_count(self) -> int:
        return sum(sum(row) for row in self.sequence)

    @property
    def late_event_count(self) -> int:
        return sum(sum(self.sequence[t]) for t in LATE_TIMESTEPS)

    @property
    def late_event_fraction(self) -> float:
        return self.late_event_count / float(self.event_count or 1)

    def to_dict(self) -> Dict[str, object]:
        return {
            "sample_id": self.sample_id,
            "split": self.split,
            "label": self.label,
            "sequence": [list(row) for row in self.sequence],
            "event_count": self.event_count,
            "late_event_count": self.late_event_count,
        }


def _seed_for(split: str, index: int) -> int:
    digest = hashlib.sha256(f"{ROOT_SEED}:{split}:{index}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _empty_sequence() -> List[List[int]]:
    return [[0 for _ in range(CHANNELS)] for _ in range(TIMESTEPS)]


def _choose_cells(rng: random.Random, cells: Sequence[Tuple[int, int]], count: int) -> List[Tuple[int, int]]:
    if count < 0 or count > len(cells):
        raise ValueError("invalid cell count")
    return rng.sample(list(cells), count)


def _background_cells(rng: random.Random) -> List[Tuple[int, int]]:
    # One event in each of 16 distinct timesteps. Because only four timesteps are
    # in the late window, late activity is bounded to <=4/16 while total activity
    # remains exactly equal to the positive class.
    timesteps = rng.sample(list(range(TIMESTEPS)), EVENTS_PER_SAMPLE)
    return [(t, rng.randrange(CHANNELS)) for t in timesteps]


def _positive_cells(rng: random.Random) -> List[Tuple[int, int]]:
    late_cells = [(t, c) for t in LATE_TIMESTEPS for c in range(CHANNELS)]
    early_cells = [(t, c) for t in range(TIMESTEPS) if t not in LATE_TIMESTEPS for c in range(CHANNELS)]
    selected = _choose_cells(rng, late_cells, POSITIVE_LATE_EVENTS)
    selected.extend(_choose_cells(rng, early_cells, EVENTS_PER_SAMPLE - POSITIVE_LATE_EVENTS))
    return selected


def generate_sample(split: str, index: int) -> TemporalSalienceSample:
    if split not in SPLIT_SIZES:
        raise ValueError(f"unknown split: {split}")
    if index < 0 or index >= SPLIT_SIZES[split]:
        raise IndexError(index)

    # Alternating labels makes each even-sized split exactly balanced. The sample
    # ID is metadata only and is not part of the model input.
    label = index % 2
    rng = random.Random(_seed_for(split, index))
    cells = _positive_cells(rng) if label == 1 else _background_cells(rng)

    sequence = _empty_sequence()
    for timestep, channel in cells:
        sequence[timestep][channel] = 1

    frozen = tuple(tuple(row) for row in sequence)
    canonical = json.dumps(
        {"split": split, "index": index, "label": label, "sequence": frozen},
        sort_keys=True,
        separators=(",", ":"),
    )
    sample_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    sample = TemporalSalienceSample(sample_id=sample_id, split=split, label=label, sequence=frozen)
    if sample.event_count != EVENTS_PER_SAMPLE:
        raise AssertionError("generator event budget invariant violated")
    return sample


def generate_split(split: str) -> List[TemporalSalienceSample]:
    return [generate_sample(split, i) for i in range(SPLIT_SIZES[split])]


def split_fingerprint(split: str) -> str:
    payload = [sample.to_dict() for sample in generate_split(split)]
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def balanced_accuracy(labels: Sequence[int], predictions: Sequence[int]) -> float:
    if len(labels) != len(predictions) or not labels:
        raise ValueError("labels/predictions must be non-empty and equal length")
    recalls = []
    for cls in (0, 1):
        idx = [i for i, y in enumerate(labels) if y == cls]
        if not idx:
            raise ValueError(f"missing class {cls}")
        recalls.append(sum(1 for i in idx if predictions[i] == cls) / len(idx))
    return sum(recalls) / 2.0


def majority_baseline_balanced_accuracy(split: str) -> float:
    samples = generate_split(split)
    labels = [s.label for s in samples]
    return balanced_accuracy(labels, [0] * len(samples))


def total_event_count_values(split: str) -> Tuple[int, ...]:
    return tuple(sorted({sample.event_count for sample in generate_split(split)}))
