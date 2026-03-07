"""Deterministic dataset splitting utilities."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


def _score_for_group(group_key: str, seed: int) -> float:
    payload = f"{seed}:{group_key}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    raw = int(digest[:16], 16)
    return raw / float(0xFFFFFFFFFFFFFFFF)


def create_deterministic_splits(
    dataset_dir: Path,
    out_path: Path | None = None,
    *,
    seed: int = 1,
    train_ratio: float = 0.7,
    validation_ratio: float = 0.15,
    holdout_ratio: float = 0.15,
    group_column: str = "scenario_hash",
) -> Path:
    """Create deterministic train/validation/holdout splits for dataset.csv."""

    if abs((train_ratio + validation_ratio + holdout_ratio) - 1.0) > 1e-9:
        raise ValueError("Split ratios must sum to 1.0")

    dataset_path = dataset_dir / "dataset.csv"
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Missing dataset file: {dataset_path}")

    df = pd.read_csv(dataset_path)
    if group_column not in df.columns:
        raise ValueError(f"Missing group column in dataset: {group_column}")

    if out_path is None:
        out_path = dataset_dir / "dataset_splits.json"

    unique_groups = sorted({str(v) for v in df[group_column].astype(str)})
    split_by_group: dict[str, str] = {}
    train_cutoff = float(train_ratio)
    validation_cutoff = float(train_ratio + validation_ratio)

    for group_key in unique_groups:
        score = _score_for_group(group_key, seed)
        if score < train_cutoff:
            split_by_group[group_key] = "train"
        elif score < validation_cutoff:
            split_by_group[group_key] = "validation"
        else:
            split_by_group[group_key] = "holdout"

    # Ensure all buckets receive at least one group when feasible.
    if len(unique_groups) >= 3:
        for bucket in ("train", "validation", "holdout"):
            if bucket not in split_by_group.values():
                donor = next((b for b in ("train", "validation", "holdout") if list(split_by_group.values()).count(b) > 1), None)
                if donor is not None:
                    donor_groups = sorted([g for g, b in split_by_group.items() if b == donor])
                    split_by_group[donor_groups[0]] = bucket

    split_rows: dict[str, list[int]] = {"train": [], "validation": [], "holdout": []}
    for idx, row in df.iterrows():
        group_key = str(row[group_column])
        split_rows[split_by_group[group_key]].append(int(idx))

    payload = {
        "dataset": str(dataset_path),
        "seed": int(seed),
        "group_column": str(group_column),
        "ratios": {
            "train": float(train_ratio),
            "validation": float(validation_ratio),
            "holdout": float(holdout_ratio),
        },
        "groups": {name: sorted(keys) for name, keys in {
            "train": [g for g, s in split_by_group.items() if s == "train"],
            "validation": [g for g, s in split_by_group.items() if s == "validation"],
            "holdout": [g for g, s in split_by_group.items() if s == "holdout"],
        }.items()},
        "rows": {name: sorted(indices) for name, indices in split_rows.items()},
        "counts": {
            "train": int(len(split_rows["train"])),
            "validation": int(len(split_rows["validation"])),
            "holdout": int(len(split_rows["holdout"])),
            "total": int(len(df)),
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


__all__ = ["create_deterministic_splits"]
