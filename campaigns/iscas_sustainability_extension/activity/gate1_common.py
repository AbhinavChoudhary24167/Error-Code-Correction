#!/usr/bin/env python3
"""Shared, dependency-free helpers for sustainability Gate 1."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable, Mapping, Sequence


POWER_ROW = re.compile(
    r"^(Sequential|Combinational|Clock|Macro|Pad|Total)\s+"
    r"([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def aggregate_hash(mapping: Mapping[str, str]) -> str:
    payload = json.dumps(dict(mapping), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def parse_power_report(path: Path) -> dict[str, dict[str, float]]:
    rows: dict[str, dict[str, float]] = {}
    for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        match = POWER_ROW.match(line.strip())
        if match:
            group, internal, switching, leakage, total = match.groups()
            rows[group] = {
                "internal_power_w": float(internal),
                "switching_power_w": float(switching),
                "leakage_power_w": float(leakage),
                "total_power_w": float(total),
            }
    required = {"Sequential", "Combinational", "Clock", "Total"}
    missing = sorted(required - rows.keys())
    if missing:
        raise ValueError(f"missing required power groups in {path}: {missing}")
    total = rows["Total"]
    component_sum = total["internal_power_w"] + total["switching_power_w"] + total["leakage_power_w"]
    # OpenSTA's separately reported group components and Total differ by up to
    # O(1e-8) relative in both the frozen DATE W0 reports and the new reports.
    # This is a report reconstruction check, not a demand for bit-identical
    # floating-point accumulation order.
    tolerance = max(1e-12, abs(total["total_power_w"]) * 1e-7)
    if abs(component_sum - total["total_power_w"]) > tolerance:
        raise ValueError(
            f"power components do not reconstruct total in {path}: "
            f"components={component_sum:.15g}, total={total['total_power_w']:.15g}"
        )
    return rows


def energy_per_op_pj(total_power_w: float, trace_duration_ps: int, useful_operations: int) -> float:
    if trace_duration_ps <= 0 or useful_operations <= 0:
        raise ValueError("trace duration and useful operation count must be positive")
    return total_power_w * (trace_duration_ps * 1e-12) / useful_operations * 1e12
