#!/usr/bin/env python3
"""Generate deterministic GREEN-ECC-PHY documentation figures and data."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import textwrap
from typing import Any, Callable, Iterable, Mapping, Sequence

os.environ.setdefault("SOURCE_DATE_EPOCH", "0")

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.labelsize": 9,
        "legend.fontsize": 8,
        "figure.dpi": 120,
        "savefig.dpi": 320,
        "svg.hashsalt": "green-ecc-phy-documentation-v1",
        "pdf.compression": 9,
    }
)
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from green_ecc_phy.hashing import canonical_hash
from green_ecc_phy.pareto_validation import (
    Objective,
    crowding_distance,
    hypervolume_2d,
    knee_point,
    pareto_front,
)


EVALUATION = Path("green_ecc_physical_simulation/multi_ecc_evaluation")
REGISTRY = Path("green_ecc_physical_simulation/registry")
EVIDENCE_COLORS = {
    "exact_functional": "#0072B2",
    "analytical_model": "#E69F00",
    "structural_tool": "#7B61A8",
    "physical_characterization": "#009E73",
    "hardware_measurement": "#006D5B",
    "unsupported": "#8A8A8A",
}
STATUS_COLORS = {
    "verified": "#0072B2",
    "partially_verified": "#E69F00",
    "rejected": "#D55E00",
    "unsupported": "#8A8A8A",
    "not_applicable": "#E5E5E5",
}


LABELS = {
    "extended-hamming-secded-72-64-v1": "extended Hamming SECDED (72,64)",
    "forge-hotspot-8-4-v1": "Forge hotspot (8,4)",
    "forge-spatial-hotspot-72-64-v1": "Forge spatial (72,64)",
    "forge-sram-portfolio-72-64-v1-geometry-filtered-joint": "Forge geometry portfolio",
    "forge-sram-portfolio-72-64-v1-spatial-hotspot-joint": "Forge spatial portfolio",
    "hsiao-secded-72-64-v1": "Hsiao SECDED (72,64)",
    "odd-column-secded-4-8": "odd-column SECDED (8,4)",
    "odd-column-secded-64-72": "odd-column SECDED (72,64)",
    "primitive-bch-63-51-t2-v1": "primitive BCH (63,51,t=2)",
    "repository-cyclic-63-51-v1": "cyclic-labelled (rejected)",
    "safeforge-robust-72-64-mapping-v1": "SafeForge robust (72,64)",
    "safeforge-robust-8-4-v1": "SafeForge robust (8,4)",
    "shortened-bch-71-64-t1-v1": "shortened BCH (71,64,t=1)",
    "shortened-bch-78-64-t2-v1": "shortened BCH (78,64,t=2)",
    "shortened-bch-85-64-t3-v1": "shortened BCH (85,64,t=3)",
    "cyclic-rtl-bounded-search-63-51-v1": "cyclic-labelled (rejected)",
    "forge-hotspot-8-4-v1-archived-table-decoder": "Forge hotspot (8,4)",
    "forge-spatial-hotspot-72-64-v1-archived-table-decoder": "Forge spatial (72,64)",
    "forge-sram-portfolio-72-64-v1-geometry-filtered-joint-archived-table-decoder": "Forge geometry portfolio",
    "forge-sram-portfolio-72-64-v1-spatial-hotspot-joint-archived-table-decoder": "Forge spatial portfolio",
    "hsiao-generated-combinational-72-64-v1": "Hsiao SECDED (72,64)",
    "odd-column-secded-4-8-archived-table-decoder": "odd-column SECDED (8,4)",
    "odd-column-secded-64-72-archived-table-decoder": "odd-column SECDED (72,64)",
    "primitive-bch-63-51-t2-v1-reference-decoder": "primitive BCH (63,51,t=2)",
    "safeforge-robust-72-64-mapping-v1-archived-table-decoder": "SafeForge robust (72,64)",
    "safeforge-robust-8-4-v1-archived-table-decoder": "SafeForge robust (8,4)",
    "secdaec-rtl-bounded-72-64-v1": "bounded SEC-DAEC (rejected)",
    "secded-rtl-combinational-72-64-v1": "conventional SECDED (72,64)",
    "shortened-bch-71-64-t1-v1-reference-decoder": "shortened BCH (71,64,t=1)",
    "shortened-bch-78-64-t2-v1-reference-decoder": "shortened BCH (78,64,t=2)",
    "shortened-bch-85-64-t3-v1-reference-decoder": "shortened BCH (85,64,t=3)",
    "taec-rtl-bounded-72-64-v1": "bounded TAEC (partial)",
    "NO_WINNER": "no winner",
}


def label(identifier: str, limit: int = 34) -> str:
    value = LABELS.get(identifier, identifier.replace("-archived-table-decoder", ""))
    return value if len(value) <= limit else value[: limit - 1] + "…"


def wrapped_label(identifier: str, width: int = 24) -> str:
    """Return a complete display label split across lines instead of ellipsized."""
    value = LABELS.get(identifier, identifier.replace("-archived-table-decoder", ""))
    return "\n".join(
        textwrap.wrap(
            value,
            width=width,
            break_long_words=False,
            break_on_hyphens=True,
        )
    )


def read_json(root: Path, relative: Path | str) -> dict[str, Any]:
    path = root / relative
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def source_records(root: Path, paths: Iterable[Path | str]) -> list[dict[str, str]]:
    records = []
    for relative in sorted({Path(path).as_posix() for path in paths}):
        records.append({"path": relative, "sha256": sha256(root / relative)})
    return records


def save_figure(fig: plt.Figure, destination: Path) -> dict[str, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    paths = {}
    for extension in ("svg", "png", "pdf"):
        path = destination.with_suffix("." + extension)
        metadata: dict[str, Any]
        if extension == "svg":
            metadata = {"Creator": "GREEN-ECC-PHY documentation builder", "Date": "1970-01-01"}
        elif extension == "png":
            metadata = {"Software": "GREEN-ECC-PHY documentation builder"}
        else:
            metadata = {
                "Creator": "GREEN-ECC-PHY documentation builder",
                "Producer": "Matplotlib",
                "CreationDate": None,
                "ModDate": None,
            }
        fig.savefig(path, format=extension, dpi=320, metadata=metadata, bbox_inches="tight")
        paths[extension] = path.name
    plt.close(fig)
    return paths


def categorical_cmap(values: Sequence[str]) -> tuple[ListedColormap, BoundaryNorm, dict[str, int]]:
    unique = sorted(set(values))
    palette = [
        "#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00",
        "#F0E442", "#332288", "#88CCEE", "#44AA99", "#117733", "#999933",
        "#DDCC77", "#CC6677", "#882255", "#AA4499", "#661100", "#6699CC",
    ]
    mapping = {value: index for index, value in enumerate(unique)}
    cmap = ListedColormap(palette[: len(unique)])
    norm = BoundaryNorm(np.arange(-0.5, len(unique) + 0.5), cmap.N)
    return cmap, norm, mapping


class Context:
    def __init__(self, root: Path):
        self.root = root
        self.summary = read_json(root, EVALUATION / "framework_summary.json")
        self.study = read_json(root, EVALUATION / "software_study_summary.json")
        self.scope = read_json(root, EVALUATION / "ecc_scope_matrix.json")
        self.capability = read_json(root, EVALUATION / "implementation_capability_matrix.json")
        self.profiles = read_json(root, EVALUATION / "exact_functional_profiles.json")
        self.metrics = read_json(root, EVALUATION / "normalized_exact_metrics.json")
        self.scenarios = read_json(root, EVALUATION / "scenario_selection_results.json")
        self.pareto = read_json(root, EVALUATION / "pareto_and_regret.json")
        self.uncertainty = read_json(root, EVALUATION / "uncertainty_and_sensitivity.json")
        self.regions = read_json(root, EVALUATION / "scenario_regions.json")
        self.registry = read_json(root, REGISTRY / "registry.json")
        self.verification = {
            path.stem: json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((root / EVALUATION / "verification").glob("*.json"))
        }
        self.characterization = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((root / EVALUATION / "characterization").glob("*.json"))
        ]
        self.codes = {}
        for raw in self.registry["codes"]:
            path = (root / REGISTRY / raw).resolve() if not Path(raw).is_absolute() else Path(raw)
            if not path.exists():
                path = root / raw
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.codes[str(payload["code_id"])] = payload


def _source_payload(figure_id: str, evidence: Sequence[str], sources: list[dict[str, str]], records: Any) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "figure_id": figure_id,
        "evidence_classes": list(evidence),
        "source_artifacts": sources,
        "records": records,
    }


def portfolio(ctx: Context) -> tuple[dict[str, Any], plt.Figure]:
    rows = []
    cap_by_code: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for item in ctx.capability["rows"]:
        raw = item["capability_verification_status"]
        status = "rejected" if raw == "rejected" else "partially_verified" if raw == "partially_verified" else "verified"
        cap_by_code[item["code_spec_id"]][status] += 1
    for code_id in sorted(ctx.codes):
        rows.append({"code_spec_id": code_id, **cap_by_code[code_id]})
    experimental = sum("experimental" in str(item["status"]) for item in ctx.scope["rows"])
    excluded = sum(str(item.get("selection_scope", "")) == "excluded" for item in ctx.scope["rows"])
    fig, ax = plt.subplots(figsize=(10.5, 7.3), layout="constrained")
    y = np.arange(len(rows))
    left = np.zeros(len(rows))
    for status, hatch in (("verified", ""), ("partially_verified", "//"), ("rejected", "xx")):
        values = np.array([row.get(status, 0) for row in rows])
        ax.barh(y, values, left=left, color=STATUS_COLORS[status], edgecolor="black", linewidth=0.4, hatch=hatch, label=status.replace("_", " "))
        left += values
    ax.set_yticks(y, [label(row["code_spec_id"], 31) for row in rows], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("Registered encoder/decoder implementations (count)")
    ax.set_title("Registered portfolio: mathematical codes and implementation status")
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax.legend(loc="center right")
    ax.text(
        0.99, 0.01,
        f"codes: {len(ctx.codes)}   implementations: {len(ctx.capability['rows'])}\n"
        f"architectures: {len(ctx.registry['architectures'])}   experimental inventory rows: {experimental}   excluded code rows: {excluded}",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=8,
        bbox={"facecolor": "white", "edgecolor": "#666666", "alpha": 0.92},
    )
    return {"code_rows": rows, "summary": {"architecture_count": len(ctx.registry["architectures"]), "experimental_inventory_rows": experimental, "excluded_code_rows": excluded}}, fig


def code_rate(ctx: Context) -> tuple[dict[str, Any], plt.Figure]:
    rows = []
    for code_id, code in sorted(ctx.codes.items()):
        k, n = int(code["k"]), int(code["n"])
        words = math.ceil(64 / k)
        rows.append({"code_spec_id": code.get("code_spec_id", code_id), "k": k, "n": n, "parity_bits": n - k, "code_rate": k / n, "encoded_bits_per_64b_payload": words * n, "padding_information_bits": words * k - 64})
    fig, (left, right) = plt.subplots(1, 2, figsize=(13, 7), layout="constrained")
    y = np.arange(len(rows))
    left.barh(y, [row["parity_bits"] for row in rows], color=EVIDENCE_COLORS["exact_functional"], edgecolor="black", linewidth=0.35)
    left.set_yticks(y, [label(row["code_spec_id"], 34) for row in rows], fontsize=7)
    left.invert_yaxis(); left.set_xlabel("Parity bits per codeword (bits)"); left.set_title("Redundancy")
    for pos, row in zip(y, rows):
        left.text(row["parity_bits"] + 0.25, pos, f"({row['n']},{row['k']})", va="center", fontsize=6.5)
    right.scatter([row["code_rate"] for row in rows], y, color=EVIDENCE_COLORS["exact_functional"], marker="o", label="code rate k/n")
    right.scatter([row["encoded_bits_per_64b_payload"] / 64 for row in rows], y, color="#CC79A7", marker="s", label="encoded bits / 64-bit payload")
    right.set_yticks(y, [label(row["code_spec_id"], 34) for row in rows], fontsize=7); right.invert_yaxis()
    right.set_xlabel("Dimensionless normalized ratio"); right.set_title("Rate and equal-payload storage")
    right.legend(loc="lower right")
    fig.suptitle("Exact code-rate and redundancy comparison (64-bit information payload)")
    return {"normalization": "ceil(64/k) independent codewords; final information word is zero padded", "code_rows": rows}, fig


def capability_heatmap(ctx: Context) -> tuple[dict[str, Any], plt.Figure]:
    columns = ["overall", "no_error", "SEC", "DED", "adjacent_double_correction", "unrestricted_double_correction", "adjacent_triple_correction", "BCH_t_bit_correction", "malformed_input", "protocol_reset"]
    rows = []
    for item in ctx.capability["rows"]:
        identifier = item["implementation_id"]
        report = ctx.verification[identifier]
        classes = item["class_results"]

        def class_status(predicate: Callable[[Mapping[str, Any]], bool]) -> str:
            matches = [entry for entry in classes if predicate(entry)]
            if not matches:
                return "unsupported"
            return "verified" if all(entry["passed"] for entry in matches) else "rejected"

        overall = item["capability_verification_status"]
        overall = "partially_verified" if overall == "partially_verified" else "rejected" if overall == "rejected" else "verified"
        checks = report["checks"]
        protocol_items = [checks["protocol_testing"], checks["reset_testing"]]
        protocol = "not_applicable" if all(entry.get("status") == "not_applicable" for entry in protocol_items) else "verified" if all(entry.get("status") == "passed" for entry in protocol_items) else "unsupported" if any(entry.get("status") == "missing" for entry in protocol_items) else "rejected"
        values = {
            "overall": overall,
            "no_error": "verified" if checks["no_error_decoding"] else "rejected",
            "SEC": class_status(lambda entry: entry["class_id"] in {"all-single-bit-errors", "all-weight-1-errors"} and "CORRECTED" in entry["acceptable_statuses"]),
            "DED": class_status(lambda entry: entry["class_id"] == "all-double-bit-errors" and "DETECTED_UNCORRECTABLE" in entry["acceptable_statuses"]),
            "adjacent_double_correction": class_status(lambda entry: "adjacent-double" in entry["class_id"] and "CORRECTED" in entry["acceptable_statuses"]),
            "unrestricted_double_correction": class_status(lambda entry: entry["class_id"] == "all-weight-2-errors" and "CORRECTED" in entry["acceptable_statuses"]),
            "adjacent_triple_correction": class_status(lambda entry: "adjacent-triple" in entry["class_id"] and "CORRECTED" in entry["acceptable_statuses"]),
            "BCH_t_bit_correction": "not_applicable" if "bch" not in identifier else class_status(lambda entry: entry["class_id"].startswith("all-weight-") and "CORRECTED" in entry["acceptable_statuses"]),
            "malformed_input": "verified" if checks["malformed_encode_rejected"] and checks["wrong_length_decode_rejected"] else "rejected",
            "protocol_reset": protocol,
        }
        rows.append({"implementation_id": identifier, "cells": values})
    order = ["not_applicable", "unsupported", "partially_verified", "rejected", "verified"]
    cmap = ListedColormap([STATUS_COLORS[key] for key in order])
    matrix = np.array([[order.index(row["cells"][column]) for column in columns] for row in rows])
    fig, ax = plt.subplots(figsize=(13.5, 7.5), layout="constrained")
    ax.imshow(matrix, aspect="auto", cmap=cmap, norm=BoundaryNorm(np.arange(-0.5, len(order) + 0.5), cmap.N))
    ax.set_xticks(np.arange(len(columns)), [value.replace("_", "\n") for value in columns], rotation=25, ha="right", fontsize=7)
    ax.set_yticks(np.arange(len(rows)), [label(row["implementation_id"], 34) for row in rows], fontsize=7)
    for i, row in enumerate(rows):
        for j, column in enumerate(columns):
            status = row["cells"][column]
            ax.text(j, i, {"verified": "V", "partially_verified": "P", "rejected": "R", "unsupported": "U", "not_applicable": "—"}[status], ha="center", va="center", fontsize=6.5, color="white" if status in {"verified", "rejected"} else "black")
    ax.set_title("Capability verification matrix (V verified; P partial; R rejected; U unsupported; — not applicable)")
    ax.legend(handles=[Patch(facecolor=STATUS_COLORS[key], edgecolor="black", label=key.replace("_", " ")) for key in order], loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=5)
    return {"columns": columns, "implementation_rows": rows}, fig


def outcomes(ctx: Context) -> tuple[dict[str, Any], plt.Figure]:
    categories = ["correctly_corrected", "detected_uncorrectable", "abstained", "unsupported", "silently_miscorrected"]
    rows = []
    for item in ctx.capability["rows"]:
        counts: Counter[str] = Counter()
        for entry in item["class_results"]:
            raw = entry["outcome_counts"]
            counts["correctly_corrected"] += int(raw.get("CORRECTED", 0))
            counts["detected_uncorrectable"] += int(raw.get("DETECTED_UNCORRECTABLE", 0))
            counts["abstained"] += int(raw.get("ABSTAINED", 0))
            counts["unsupported"] += int(raw.get("UNSUPPORTED", 0) + raw.get("INVALID_CONFIGURATION", 0))
            counts["silently_miscorrected"] += int(raw.get("MISCORRECTED", 0))
        total = sum(counts.values())
        rows.append({"implementation_id": item["implementation_id"], "declared_tested_patterns": total, **{category: counts[category] for category in categories}})
    colors = ["#0072B2", "#56B4E9", "#E69F00", "#8A8A8A", "#D55E00"]
    fig, ax = plt.subplots(figsize=(12.5, 7.6), layout="constrained")
    y = np.arange(len(rows)); left = np.zeros(len(rows))
    for category, color, hatch in zip(categories, colors, ["", "//", "..", "xx", "\\\\"]):
        values = np.array([100 * row[category] / row["declared_tested_patterns"] if row["declared_tested_patterns"] else 0 for row in rows])
        ax.barh(y, values, left=left, label=category.replace("_", " "), color=color, edgecolor="black", linewidth=0.3, hatch=hatch)
        left += values
    ax.set_yticks(y, [label(row["implementation_id"], 34) for row in rows], fontsize=7); ax.invert_yaxis()
    ax.set_xlabel("Exact outcomes across declared tested error universes (%)")
    ax.set_xlim(0, 118)
    for pos, row in zip(y, rows): ax.text(101, pos, f"N={row['declared_tested_patterns']:,}", va="center", fontsize=6.5)
    ax.set_title("Exact verification outcomes, including rejected negative results")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3)
    return {"categories": categories, "implementation_rows": rows, "counting_note": "Counts aggregate each implementation's declared class_results; overlapping declared universes remain separate tests."}, fig


def evidence_matrix(ctx: Context) -> tuple[dict[str, Any], plt.Figure]:
    columns = ["functional", "structural", "analytical_energy", "analytical_carbon", "physical_area", "physical_timing", "physical_energy", "routing", "mux_controller", "transition_reencoding", "uncertainty"]
    selectable = set(ctx.metrics["implementations"])
    rows = []
    for item in ctx.characterization:
        identifier = item["implementation_id"]
        values = {
            "functional": item["provenance"].get("verification_status") == "passed",
            "structural": bool((item.get("structural_metrics") or {}).get("available")),
            "analytical_energy": identifier in selectable,
            "analytical_carbon": identifier in selectable,
            "physical_area": any(item.get(key) is not None for key in ("cell_area", "routed_area")),
            "physical_timing": any(item.get(key) is not None for key in ("critical_path", "maximum_frequency", "setup_slack", "hold_slack")),
            "physical_energy": any(item.get(key) is not None for key in ("encoder_energy", "no_error_decode_energy", "corrected_decode_energy", "due_decode_energy")),
            "routing": any(item.get(key) is not None for key in ("wirelength", "congestion")),
            "mux_controller": any(item.get(key) is not None for key in ("mux_area", "mux_energy", "controller_area", "controller_energy")),
            "transition_reencoding": any(item.get(key) is not None for key in ("transition_energy", "transition_latency", "reencoding_energy")),
            "uncertainty": item.get("uncertainty") is not None,
        }
        rows.append({"implementation_id": identifier, "architecture_id": item["architecture_id"], "backend_id": item["backend_id"], "available": values})
    matrix = np.array([[int(row["available"][column]) for column in columns] for row in rows])
    cmap = ListedColormap(["#D9D9D9", "#0072B2"])
    fig, ax = plt.subplots(figsize=(14, 8), layout="constrained")
    ax.imshow(matrix, aspect="auto", cmap=cmap, norm=BoundaryNorm([-0.5, 0.5, 1.5], cmap.N))
    ax.set_xticks(np.arange(len(columns)), [value.replace("_", "\n") for value in columns], rotation=25, ha="right", fontsize=7)
    ax.set_yticks(np.arange(len(rows)), [f"{label(row['implementation_id'], 25)}\n{label(row['architecture_id'], 25)}" for row in rows], fontsize=6.5)
    for i, row in enumerate(rows):
        for j, column in enumerate(columns): ax.text(j, i, "available" if row["available"][column] else "not\ncharacterized", ha="center", va="center", fontsize=5.2, color="white" if row["available"][column] else "#333333")
    ax.set_title("Evidence availability by characterized implementation/architecture record\nGrey cells are null or not characterized—not zero")
    return {"columns": columns, "characterization_rows": rows}, fig


def structural(ctx: Context) -> tuple[dict[str, Any], plt.Figure]:
    rows = []
    for identifier, item in sorted(ctx.metrics["implementations"].items()):
        metrics = item["structural_metrics"]
        rows.append({"implementation_id": identifier, "encoder_xor_operations": metrics["encoder_xor_operations"], "syndrome_xor_operations": metrics["syndrome_xor_operations"], "decoder_complexity_proxy": metrics["decoder_complexity_proxy"], "logic_depth_proxy": metrics["logic_depth_proxy"], "generic_structural_cell_count": metrics["generic_structural_cell_count"]})
    max_complexity = max(row["decoder_complexity_proxy"] for row in rows)
    for row in rows: row["normalized_decoder_complexity"] = row["decoder_complexity_proxy"] / max_complexity if max_complexity else 0
    fig, (left, right) = plt.subplots(1, 2, figsize=(13, 7), layout="constrained")
    y = np.arange(len(rows))
    decoder_complexity = [row["decoder_complexity_proxy"] for row in rows]
    left.scatter(decoder_complexity, y, color=EVIDENCE_COLORS["structural_tool"], edgecolors="black", linewidths=0.35, marker="D", s=32)
    left.set_yticks(y, [label(row["implementation_id"], 31) for row in rows], fontsize=7); left.invert_yaxis()
    left.set_xscale("log")
    left.grid(axis="x", which="both", alpha=0.22)
    dynamic_range = max_complexity / min(decoder_complexity)
    left.set_xlabel("Decoder complexity proxy (log scale; structural only)")
    left.set_title(f"{dynamic_range:,.0f}\N{MULTIPLICATION SIGN} dynamic range")
    right.scatter([row["logic_depth_proxy"] for row in rows], y, color=EVIDENCE_COLORS["structural_tool"], marker="D", label="logic-depth proxy")
    right.scatter([row["encoder_xor_operations"] + row["syndrome_xor_operations"] for row in rows], y, color="#CC79A7", marker="o", label="encoder + syndrome XOR count")
    right.set_yticks(y, [label(row["implementation_id"], 31) for row in rows], fontsize=7); right.invert_yaxis(); right.set_xlabel("Technology-independent structural count / proxy")
    right.legend(loc="lower right")
    fig.suptitle("Structural-only complexity comparison—not physical PPA or measured delay")
    return {"normalization_denominator_decoder_complexity_proxy": max_complexity, "implementation_rows": rows, "null_note": "generic_structural_cell_count is null where no comparable synthesis count exists"}, fig


def pareto_objectives() -> list[Objective]:
    return [
        Objective("SDC probability", lambda item: item["analytical_metrics"]["expected_sdc_probability_per_64b_access"]["value"], "min"),
        Objective("DUE probability", lambda item: item["analytical_metrics"]["expected_due_probability_per_64b_access"]["value"], "min"),
        Objective("total energy", lambda item: item["analytical_metrics"]["modelled_total_energy"]["value"], "min"),
        Objective("encoded bits", lambda item: item["exact_metrics"]["payload_normalization"]["protected_64b_word"]["encoded_bits"], "min"),
        Objective("decoder complexity", lambda item: item["exact_metrics"]["structural_metrics"]["decoder_complexity_proxy"], "min"),
    ]


def validate_engine_pareto(ctx: Context) -> dict[str, Any]:
    objectives = pareto_objectives()
    mismatches = []
    for scenario in ctx.scenarios["scenarios"]:
        front, _ = pareto_front(scenario["candidate_records"], objectives, eligibility=lambda item: bool(item["constraints"]["feasible"]))
        actual = sorted(item["implementation_id"] for item in front)
        expected = sorted(scenario["pareto_implementation_ids"])
        if actual != expected:
            mismatches.append({"scenario_id": scenario["scenario_id"], "recorded": expected, "independent": actual})
    if mismatches:
        raise ValueError(f"independent Pareto mismatch in {len(mismatches)} scenarios")
    return {"scenarios_checked": len(ctx.scenarios["scenarios"]), "mismatch_count": 0, "objectives": [{"name": item.name, "direction": item.direction, "epsilon": item.epsilon} for item in objectives], "hard_constraint_order": ["functional verification", "scenario SDC limit", "scenario DUE limit", "non-null finite objectives", "Pareto dominance"], "duplicate_point_policy": "retain all identity-distinct epsilon-equivalent points"}


def representative(ctx: Context) -> Mapping[str, Any]:
    return next(item for item in ctx.scenarios["scenarios"] if item["winner"] is not None)


def reliability_cost(ctx: Context) -> tuple[dict[str, Any], plt.Figure]:
    scenario = representative(ctx); objectives = pareto_objectives()
    front, excluded = pareto_front(scenario["candidate_records"], objectives, eligibility=lambda item: bool(item["constraints"]["feasible"]))
    x = objectives[2]; y = objectives[0]
    knee = knee_point(front, x, y)
    reference_point = (max(float(x.getter(item)) for item in front) * 1.05, max(float(y.getter(item)) for item in front) * 1.05)
    hypervolume = hypervolume_2d(front, x, y, reference_point)
    front_ids = {item["implementation_id"] for item in front}
    records = []
    positive_records = []
    zero_records = []
    fig, (positive_ax, zero_ax) = plt.subplots(1, 2, figsize=(13.2, 6.5), gridspec_kw={"width_ratios": [1.2, 1.0]})
    for item in scenario["candidate_records"]:
        identifier = item["implementation_id"]; feasible = bool(item["constraints"]["feasible"]); on_front = identifier in front_ids
        xv, raw_y = float(x.getter(item)), float(y.getter(item))
        record = {"implementation_id": identifier, "analytical_total_energy_j_per_scenario": xv, "analytical_sdc_probability_per_64b_access": raw_y, "feasible": feasible, "pareto_5d": on_front, "selected": identifier == scenario["winner"], "knee_2d_projection": knee is not None and identifier == knee["implementation_id"]}
        records.append(record)
        (zero_records if raw_y == 0.0 else positive_records).append(record)
    for annotation_index, record in enumerate(sorted(positive_records, key=lambda item: (item["analytical_sdc_probability_per_64b_access"], item["analytical_total_energy_j_per_scenario"], item["implementation_id"]))):
        identifier = record["implementation_id"]; xv = record["analytical_total_energy_j_per_scenario"]; yv = record["analytical_sdc_probability_per_64b_access"]; feasible = record["feasible"]; on_front = record["pareto_5d"]
        if feasible:
            positive_ax.scatter(xv, yv, s=58 if on_front else 30, marker="o", facecolors=EVIDENCE_COLORS["analytical_model"] if on_front else "#BBBBBB", edgecolors="black", linewidths=0.6, alpha=1.0 if on_front else 0.65)
        else:
            positive_ax.scatter(xv, yv, s=30, marker="x", color="#666666", linewidths=0.8, alpha=0.75)
        if on_front or record["selected"]:
            positive_ax.annotate(label(identifier, 34), (xv, yv), xytext=(4, 4 + 4 * (annotation_index % 2)), textcoords="offset points", fontsize=6.2)
        if record["selected"]:
            positive_ax.scatter(xv, yv, s=150, facecolors="none", edgecolors="#D55E00", linewidths=1.7, marker="o")
        if record["knee_2d_projection"]:
            positive_ax.scatter(xv, yv, s=120, facecolors="none", edgecolors="#0072B2", linewidths=1.5, marker="s")
    zero_records.sort(key=lambda item: (item["analytical_total_energy_j_per_scenario"], item["implementation_id"]))
    zero_positions = np.arange(len(zero_records))
    for position, record in zip(zero_positions, zero_records):
        xv = record["analytical_total_energy_j_per_scenario"]
        if record["feasible"]:
            zero_ax.scatter(xv, position, s=58 if record["pareto_5d"] else 30, marker="o", facecolors=EVIDENCE_COLORS["analytical_model"] if record["pareto_5d"] else "#BBBBBB", edgecolors="black", linewidths=0.6)
        else:
            zero_ax.scatter(xv, position, s=30, marker="x", color="#666666", linewidths=0.8)
        if record["selected"]:
            zero_ax.scatter(xv, position, s=150, facecolors="none", edgecolors="#D55E00", linewidths=1.7, marker="o")
        if record["knee_2d_projection"]:
            zero_ax.scatter(xv, position, s=120, facecolors="none", edgecolors="#0072B2", linewidths=1.5, marker="s")
    positive_ax.set_yscale("log"); positive_ax.set_xlabel("Analytical total energy (J/scenario; minimize)"); positive_ax.set_ylabel("Positive analytical SDC probability / 64-bit access (minimize)")
    positive_ax.set_title("Positive modelled SDC probabilities")
    zero_ax.set_yticks(zero_positions, [wrapped_label(item["implementation_id"], 27) for item in zero_records], fontsize=6.5); zero_ax.invert_yaxis()
    zero_ax.set_xlabel("Analytical total energy (J/scenario; minimize)"); zero_ax.set_title("Exact-zero SDC values (not log-clamped)")
    fig.suptitle("Reliability–cost frontier for one traceable scenario\nPareto membership independently recomputed in the selector's five objectives")
    legend_handles = [
        Line2D([], [], marker="o", linestyle="none", markerfacecolor=EVIDENCE_COLORS["analytical_model"], markeredgecolor="black", label="five-objective Pareto member"),
        Line2D([], [], marker="o", linestyle="none", markerfacecolor="#BBBBBB", markeredgecolor="black", label="feasible, dominated"),
        Line2D([], [], marker="x", linestyle="none", color="#666666", label="infeasible"),
        Line2D([], [], marker="o", linestyle="none", markerfacecolor="none", markeredgecolor="#D55E00", label="selected minimum-energy candidate"),
        Line2D([], [], marker="s", linestyle="none", markerfacecolor="none", markeredgecolor="#0072B2", label="2D projected knee"),
    ]
    fig.legend(handles=legend_handles, loc="lower center", bbox_to_anchor=(0.5, 0.01), ncol=3)
    fig.tight_layout(rect=(0, 0.12, 1, 0.92))
    return {"scenario_id": scenario["scenario_id"], "scenario_factors": scenario["factors"], "objective_definition": validate_engine_pareto(ctx), "records": records, "excluded": excluded, "knee_implementation_id": knee["implementation_id"] if knee else None, "hypervolume_2d_projection": hypervolume, "hypervolume_reference_point": {"energy_j": reference_point[0], "sdc_probability": reference_point[1]}}, fig


def reliability_carbon(ctx: Context) -> tuple[dict[str, Any], plt.Figure]:
    scenario = representative(ctx)
    x = Objective("operational carbon", lambda item: item["analytical_metrics"]["modelled_operational_carbon"]["value"], "min")
    y = Objective("SDC probability", lambda item: item["analytical_metrics"]["expected_sdc_probability_per_64b_access"]["value"], "min")
    front, excluded = pareto_front(scenario["candidate_records"], [x, y], eligibility=lambda item: bool(item["constraints"]["feasible"]))
    front_ids = {item["implementation_id"] for item in front}; records = []; positive_records = []; zero_records = []
    fig, (positive_ax, zero_ax) = plt.subplots(1, 2, figsize=(13.2, 6.4), gridspec_kw={"width_ratios": [1.2, 1.0]})
    for item in scenario["candidate_records"]:
        identifier = item["implementation_id"]; feasible = bool(item["constraints"]["feasible"]); on_front = identifier in front_ids
        xv, raw_y = float(x.getter(item)), float(y.getter(item))
        record = {"implementation_id": identifier, "analytical_operational_carbon_kgco2e_per_scenario": xv, "analytical_sdc_probability_per_64b_access": raw_y, "feasible": feasible, "pareto_2d": on_front}
        records.append(record); (zero_records if raw_y == 0.0 else positive_records).append(record)
    for record in positive_records:
        xv = record["analytical_operational_carbon_kgco2e_per_scenario"]; yv = record["analytical_sdc_probability_per_64b_access"]
        positive_ax.scatter(xv, yv, marker="o" if record["feasible"] else "x", s=56 if record["pareto_2d"] else 28, color=EVIDENCE_COLORS["analytical_model"] if record["pareto_2d"] else "#BBBBBB", edgecolors="black" if record["feasible"] else None, linewidths=0.5)
        if record["pareto_2d"]: positive_ax.annotate(label(record["implementation_id"], 34), (xv, yv), xytext=(4, 4), textcoords="offset points", fontsize=6.5)
    zero_records.sort(key=lambda item: (item["analytical_operational_carbon_kgco2e_per_scenario"], item["implementation_id"]))
    zero_positions = np.arange(len(zero_records))
    for position, record in zip(zero_positions, zero_records):
        xv = record["analytical_operational_carbon_kgco2e_per_scenario"]
        zero_ax.scatter(xv, position, marker="o" if record["feasible"] else "x", s=56 if record["pareto_2d"] else 28, color=EVIDENCE_COLORS["analytical_model"] if record["pareto_2d"] else "#BBBBBB", edgecolors="black" if record["feasible"] else None, linewidths=0.5)
    positive_ax.set_yscale("log"); positive_ax.set_xlabel("Modelled operational carbon (kgCO₂e/scenario; minimize)"); positive_ax.set_ylabel("Positive analytical SDC probability / 64-bit access")
    positive_ax.set_title("Positive modelled SDC probabilities")
    zero_ax.set_yticks(zero_positions, [wrapped_label(item["implementation_id"], 27) for item in zero_records], fontsize=6.5); zero_ax.invert_yaxis()
    zero_ax.set_xlabel("Modelled operational carbon (kgCO₂e/scenario; minimize)"); zero_ax.set_title("Exact-zero SDC values (not log-clamped)")
    fig.suptitle("Reliability–operational-carbon frontier (analytical model)\nEmbodied carbon is unavailable and is not plotted")
    fig.legend(handles=[
        Line2D([], [], marker="o", linestyle="none", markerfacecolor=EVIDENCE_COLORS["analytical_model"], markeredgecolor="black", label="two-objective Pareto member"),
        Line2D([], [], marker="o", linestyle="none", markerfacecolor="#BBBBBB", markeredgecolor="black", label="feasible, dominated"),
        Line2D([], [], marker="x", linestyle="none", color="#666666", label="infeasible"),
    ], loc="lower center", bbox_to_anchor=(0.5, 0.01), ncol=3)
    fig.tight_layout(rect=(0, 0.10, 1, 0.92))
    return {"scenario_id": scenario["scenario_id"], "scenario_factors": scenario["factors"], "records": records, "excluded": excluded, "embodied_carbon": None, "operational_carbon_provenance": "energy / 3.6e6 × scenario carbon intensity"}, fig


def energy_complexity(ctx: Context) -> tuple[dict[str, Any], plt.Figure]:
    scenario = representative(ctx)
    x = Objective("logic-depth proxy", lambda item: item["exact_metrics"]["structural_metrics"]["logic_depth_proxy"], "min")
    y = Objective("analytical energy", lambda item: item["analytical_metrics"]["modelled_total_energy"]["value"], "min")
    front, excluded = pareto_front(scenario["candidate_records"], [x, y], eligibility=lambda item: bool(item["constraints"]["feasible"]))
    front_ids = {item["implementation_id"] for item in front}; records = []
    fig, ax = plt.subplots(figsize=(10.5, 6.2), layout="constrained")
    for item in scenario["candidate_records"]:
        identifier = item["implementation_id"]; feasible = bool(item["constraints"]["feasible"]); on_front = identifier in front_ids
        xv, yv = float(x.getter(item)), float(y.getter(item))
        records.append({"implementation_id": identifier, "logic_depth_proxy": xv, "analytical_total_energy_j_per_scenario": yv, "feasible": feasible, "pareto_2d": on_front})
        ax.scatter(xv, yv, marker="D" if on_front else "x" if not feasible else "o", color=EVIDENCE_COLORS["structural_tool"] if on_front else "#BBBBBB", s=56 if on_front else 30, edgecolors="black" if feasible else None, linewidths=0.5)
        if on_front: ax.annotate(label(identifier, 34), (xv, yv), xytext=(4, 4), textcoords="offset points", fontsize=6.5)
    ax.set_xlabel("Technology-independent logic-depth proxy (minimize; not measured delay)"); ax.set_ylabel("Analytical total energy (J/scenario; minimize)")
    ax.set_title("Energy–complexity Pareto frontier\nAnalytical energy and structural-only depth proxy—not physical PPA")
    ax.legend(handles=[
        Line2D([], [], marker="D", linestyle="none", markerfacecolor=EVIDENCE_COLORS["structural_tool"], markeredgecolor="black", label="two-objective Pareto member"),
        Line2D([], [], marker="o", linestyle="none", markerfacecolor="#BBBBBB", markeredgecolor="black", label="feasible, dominated"),
        Line2D([], [], marker="x", linestyle="none", color="#BBBBBB", label="infeasible"),
    ], loc="upper right")
    return {"scenario_id": scenario["scenario_id"], "scenario_factors": scenario["factors"], "records": records, "excluded": excluded}, fig


def multi_scenario(ctx: Context) -> tuple[dict[str, Any], plt.Figure]:
    ids = sorted(ctx.metrics["implementations"])
    total = len(ctx.scenarios["scenarios"])
    rows = [{"implementation_id": identifier, "pareto_scenarios": int(ctx.pareto["pareto_membership_frequency"].get(identifier, 0)), "selected_scenarios": int(ctx.pareto["winner_frequency"].get(identifier, 0)), "pareto_percent": 100 * int(ctx.pareto["pareto_membership_frequency"].get(identifier, 0)) / total, "selected_percent": 100 * int(ctx.pareto["winner_frequency"].get(identifier, 0)) / total} for identifier in ids]
    fig, ax = plt.subplots(figsize=(12.5, 7), layout="constrained")
    y = np.arange(len(rows)); height = 0.38
    ax.barh(y - height / 2, [row["pareto_percent"] for row in rows], height=height, color="#56B4E9", edgecolor="black", linewidth=0.3, label="Pareto-optimal")
    ax.barh(y + height / 2, [row["selected_percent"] for row in rows], height=height, color="#E69F00", edgecolor="black", linewidth=0.3, hatch="//", label="selected")
    ax.set_yticks(y, [label(row["implementation_id"], 34) for row in rows], fontsize=7); ax.invert_yaxis(); ax.set_xlabel(f"Share of {total} scenarios (%)")
    ax.set_title(f"Multi-scenario Pareto and selection summary (no-winner scenarios: {ctx.study['no_winner_scenario_count']})")
    ax.legend(loc="lower right")
    return {"scenario_count": total, "no_winner_scenario_count": ctx.study["no_winner_scenario_count"], "implementation_rows": rows}, fig


def winner_regions(ctx: Context) -> tuple[dict[str, Any], plt.Figure]:
    scenarios = ctx.scenarios["scenarios"]
    faults = sorted({item["factors"]["fault_profile_ids"] for item in scenarios})
    requirements = sorted({item["factors"]["reliability_requirement_ids"] for item in scenarios})
    region_winners = []
    for fault in faults:
        row = []
        for requirement in requirements:
            counts = Counter(item["winner"] or "NO_WINNER" for item in scenarios if item["factors"]["fault_profile_ids"] == fault and item["factors"]["reliability_requirement_ids"] == requirement)
            row.append(max(counts, key=lambda key: (counts[key], key)))
        region_winners.append(row)
    base = representative(ctx)["factors"]
    voltages = sorted({item["factors"]["supply_voltage_v"] for item in scenarios})
    temperatures = sorted({item["factors"]["temperature_c"] for item in scenarios})
    vt_winners = []
    fixed = {key: base[key] for key in ("scrub_interval_s", "carbon_intensity_kgco2_per_kwh", "fault_profile_ids", "workload_ids", "reliability_requirement_ids")}
    for temperature in temperatures:
        row = []
        for voltage in voltages:
            match = next(item for item in scenarios if item["factors"]["temperature_c"] == temperature and item["factors"]["supply_voltage_v"] == voltage and all(item["factors"][key] == value for key, value in fixed.items()))
            row.append(match["winner"] or "NO_WINNER")
        vt_winners.append(row)
    all_values = [value for row in region_winners + vt_winners for value in row]
    cmap, norm, mapping = categorical_cmap(all_values)
    fig, (left, right) = plt.subplots(1, 2, figsize=(13, 6.4))
    left.imshow([[mapping[value] for value in row] for row in region_winners], aspect="auto", cmap=cmap, norm=norm)
    left.set_xticks(np.arange(len(requirements)), requirements, rotation=20, ha="right"); left.set_yticks(np.arange(len(faults)), faults)
    left.set_xlabel("Reliability requirement"); left.set_ylabel("Fault profile"); left.set_title("All other grid axes aggregated (modal winner)")
    category_codes = {value: f"W{index + 1}" for index, value in enumerate(sorted(mapping))}
    for i, row in enumerate(region_winners):
        for j, value in enumerate(row): left.text(j, i, category_codes[value], ha="center", va="center", fontsize=7, fontweight="bold")
    right.imshow([[mapping[value] for value in row] for row in vt_winners], aspect="auto", cmap=cmap, norm=norm)
    right.set_xticks(np.arange(len(voltages)), [f"{value:g}" for value in voltages]); right.set_yticks(np.arange(len(temperatures)), [f"{value:g}" for value in temperatures])
    right.set_xlabel("Supply voltage (V)"); right.set_ylabel("Temperature (°C)"); right.set_title("Exact V × T slice (other factors fixed)")
    for i, row in enumerate(vt_winners):
        for j, value in enumerate(row): right.text(j, i, category_codes[value], ha="center", va="center", fontsize=7, fontweight="bold")
    fig.suptitle("Categorical winner regions—computed grid cells only; no interpolation")
    fig.legend(
        handles=[Patch(facecolor=cmap(norm(mapping[value])), edgecolor="black", label=f"{category_codes[value]}  {label(value, 80)}") for value in sorted(mapping)],
        loc="lower center", bbox_to_anchor=(0.5, 0.015), ncol=2, title="Winner identity",
    )
    fig.subplots_adjust(left=0.09, right=0.98, bottom=0.27, top=0.82, wspace=0.10)
    return {"fault_profiles": faults, "reliability_requirements": requirements, "fault_requirement_winners": region_winners, "voltages_v": voltages, "temperatures_c": temperatures, "voltage_temperature_winners": vt_winners, "fixed_slice_factors": fixed, "category_mapping": mapping, "category_codes": category_codes}, fig


def winner_identity(ctx: Context) -> tuple[dict[str, Any], plt.Figure]:
    implementation = Counter(); code = Counter(); architecture = Counter()
    for scenario in ctx.scenarios["scenarios"]:
        winner = scenario["winner"]
        if winner is None:
            implementation["NO_WINNER"] += 1; code["NO_WINNER"] += 1; architecture["NO_WINNER"] += 1
            continue
        record = next(item for item in scenario["candidate_records"] if item["implementation_id"] == winner)
        implementation[winner] += 1; code[record["code_spec_id"]] += 1; architecture[record["architecture_id"]] += 1
    groups = [("Mathematical code", code), ("Implementation / decoder policy", implementation), ("Deployment architecture", architecture)]
    fig, axes = plt.subplots(1, 3, figsize=(15, 6.5), layout="constrained")
    records = {}
    for ax, (title, counts) in zip(axes, groups):
        values = sorted(counts.items(), key=lambda item: (-item[1], item[0])); records[title] = [{"identity_id": key, "selected_scenarios": value, "selected_percent": 100 * value / len(ctx.scenarios["scenarios"])} for key, value in values]
        y = np.arange(len(values)); ax.barh(y, [value for _, value in values], color=EVIDENCE_COLORS["analytical_model"], edgecolor="black", linewidth=0.35)
        ax.set_yticks(y, [wrapped_label(key, 24) for key, _ in values], fontsize=6.3); ax.invert_yaxis(); ax.set_xlabel("Selected scenarios (count)"); ax.set_title(title)
        for pos, (_, value) in zip(y, values): ax.text(value + 0.5, pos, str(value), va="center", fontsize=7)
    fig.suptitle("Winner frequency by independent identity layer")
    return {"scenario_count": len(ctx.scenarios["scenarios"]), "identity_groups": records}, fig


def baseline_regret(ctx: Context) -> tuple[dict[str, Any], plt.Figure]:
    rows = [{"implementation_id": identifier, **values} for identifier, values in sorted(ctx.pareto["fixed_baseline_regret"].items())]
    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.9), layout="constrained")
    x = np.arange(len(rows))
    left.bar(x, [100 * (row["mean_fractional_regret"] or 0) for row in rows], color=EVIDENCE_COLORS["analytical_model"], edgecolor="black", hatch="//")
    left.set_xticks(x, [wrapped_label(row["implementation_id"], 22) for row in rows], rotation=20, ha="right", fontsize=7); left.set_ylabel("Mean analytical energy regret (%)"); left.set_title("Regret where baseline is feasible")
    total = len(ctx.scenarios["scenarios"])
    right.bar(x, [100 * row["constraint_failure_or_missing_scenarios"] / total for row in rows], color="#D55E00", edgecolor="black", hatch="xx")
    right.set_xticks(x, [wrapped_label(row["implementation_id"], 22) for row in rows], rotation=20, ha="right", fontsize=7); right.set_ylabel("Infeasible or missing scenarios (%)"); right.set_ylim(0, 105); right.set_title("Hard-constraint failures")
    fig.suptitle("Fixed-baseline regret relative to scenario winner (analytical energy)")
    return {"regret_definition": "R_s(b) = E_s(b) - E_s(w_s); fractional regret divides by E_s(b); infeasible baselines are reported separately", "scenario_count": total, "baseline_rows": rows}, fig


def stability(ctx: Context) -> tuple[dict[str, Any], plt.Figure]:
    rows = []
    for model_id, values in sorted(ctx.uncertainty["uncertainty_stability"].items()):
        ambiguous = len(ctx.scenarios["scenarios"]) - values["base_winner_agreement_count"]
        rows.append({"uncertainty_model_id": model_id, "scenario_evaluations": len(ctx.scenarios["scenarios"]), "deterministic_samples_per_scenario": 1, "seed": None, "distribution": "deterministic preregistered scale tuple; no random sampling", "stability_fraction": values["base_winner_agreement_fraction"], "stable_scenarios": values["base_winner_agreement_count"], "ambiguous_or_changed_scenarios": ambiguous, "winner_frequency": values["winner_frequency"]})
    fig, ax = plt.subplots(figsize=(8.8, 4.8), layout="constrained")
    x = np.arange(len(rows)); values = [100 * row["stability_fraction"] for row in rows]
    ax.bar(x, values, color=EVIDENCE_COLORS["analytical_model"], edgecolor="black", hatch="//")
    ax.set_xticks(x, [row["uncertainty_model_id"] for row in rows]); ax.set_ylabel("Base-winner agreement (%)"); ax.set_ylim(0, 105)
    for pos, row, value in zip(x, rows, values): ax.text(pos, value + 0.8, f"{row['stable_scenarios']}/{row['scenario_evaluations']}\nchanged={row['ambiguous_or_changed_scenarios']}", ha="center", fontsize=7)
    ax.set_title("Recommendation stability under deterministic analytical sensitivity models\nOne evaluation per scenario/model; random seed not applicable")
    return {"uncertainty_rows": rows}, fig


def sensitivity(ctx: Context) -> tuple[dict[str, Any], plt.Figure]:
    scenarios = ctx.scenarios["scenarios"]
    factor_names = [key for key in scenarios[0]["factors"] if key != "scenario_id"]
    observations = []
    for scenario in scenarios:
        winner = scenario["winner"]
        if winner is None:
            continue
        record = next(item for item in scenario["candidate_records"] if item["implementation_id"] == winner)
        observations.append({"factors": scenario["factors"], "winner": winner, "reliability": record["analytical_metrics"]["expected_sdc_probability_per_64b_access"]["value"], "energy": record["analytical_metrics"]["modelled_total_energy"]["value"], "carbon": record["analytical_metrics"]["modelled_operational_carbon"]["value"]})

    def normalized_group_range(factor: str, metric: str) -> float:
        grouped: defaultdict[str, list[float]] = defaultdict(list)
        for item in observations: grouped[str(item["factors"][factor])].append(float(item[metric]))
        means = [sum(values) / len(values) for values in grouped.values()]
        overall = [float(item[metric]) for item in observations]
        span = max(overall) - min(overall)
        return 0.0 if span == 0 else (max(means) - min(means)) / span

    def winner_tv(factor: str) -> float:
        groups: defaultdict[str, Counter[str]] = defaultdict(Counter)
        for item in observations: groups[str(item["factors"][factor])][item["winner"]] += 1
        distributions = []
        identities = sorted({winner for counts in groups.values() for winner in counts})
        for counts in groups.values():
            total = sum(counts.values()); distributions.append([counts[key] / total for key in identities])
        return max((0.5 * sum(abs(a - b) for a, b in zip(left, right)) for i, left in enumerate(distributions) for right in distributions[i + 1 :]), default=0.0)

    rows = [{"factor": factor, "reliability_group_range": normalized_group_range(factor, "reliability"), "energy_group_range": normalized_group_range(factor, "energy"), "carbon_group_range": normalized_group_range(factor, "carbon"), "winner_distribution_max_total_variation": winner_tv(factor)} for factor in factor_names]
    rows.sort(key=lambda item: (-max(item[key] for key in item if key != "factor"), item["factor"]))
    fig, ax = plt.subplots(figsize=(11.2, 5.8), layout="constrained")
    y = np.arange(len(rows)); width = 0.2
    metrics = [("reliability_group_range", "Reliability (SDC)", "#0072B2"), ("energy_group_range", "Energy", "#E69F00"), ("carbon_group_range", "Carbon", "#009E73"), ("winner_distribution_max_total_variation", "Selector outcome", "#CC79A7")]
    for offset, (key, name, color) in enumerate(metrics): ax.barh(y + (offset - 1.5) * width, [row[key] for row in rows], height=width, label=name, color=color, edgecolor="black", linewidth=0.25)
    ax.set_yticks(y, [row["factor"] for row in rows], fontsize=8); ax.invert_yaxis(); ax.set_xlim(0, 1.05); ax.set_xlabel("Normalized grouped-range / maximum total-variation sensitivity (0–1)")
    ax.set_title("Descriptive scenario-grid sensitivity—not causal importance")
    ax.legend(loc="lower right")
    return {"method": "For numeric outcomes: range of factor-level means divided by full outcome range. For selector outcome: maximum pairwise total-variation distance between winner distributions.", "causal_interpretation": False, "factor_rows": rows}, fig


def adaptive_threshold(ctx: Context) -> tuple[dict[str, Any], plt.Figure]:
    data = ctx.uncertainty["adaptive_threshold"]
    rows = list(data["hypothetical_sweep"])
    fig, ax = plt.subplots(figsize=(8.8, 5.3), layout="constrained")
    x = [100 * row["hypothetical_overhead_fraction_of_gross_gain"] for row in rows]
    y = [row["net_analytical_gain_j"] for row in rows]
    ax.plot(x, y, color=EVIDENCE_COLORS["analytical_model"], marker="o", linewidth=1.8)
    ax.axhline(0, color="#555555", linestyle="--", linewidth=1); ax.axvline(100, color="#D55E00", linestyle=":", linewidth=1.5, label="analytical threshold")
    ax.fill_between(x, y, 0, where=np.array(y) > 0, color="#56B4E9", alpha=0.25, hatch="//")
    ax.set_xlabel("Hypothetical total adaptation overhead (% of gross oracle advantage)"); ax.set_ylabel("Net analytical energy gain across grid (J)")
    ax.set_title("Parameterized analytical adaptive-overhead threshold\nNot a measured break-even point")
    ax.legend(loc="best")
    return {"status": data["status"], "best_single_fixed_candidate": data["best_single_fixed_candidate"], "gross_oracle_advantage_j": data["gross_oracle_advantage_j_across_comparable_grid"], "maximum_tolerable_total_analytical_overhead_j": data["maximum_tolerable_total_analytical_overhead_j"], "symbolic_condition": data["symbolic_condition"], "physical_break_even": data["physical_break_even"], "sweep_rows": rows}, fig


def physical_gap(ctx: Context) -> tuple[dict[str, Any], plt.Figure]:
    backend_rows = []
    fields = ["structural_tool", "physical_area", "physical_timing", "physical_energy", "routing", "mux_controller", "transition_reencoding"]
    results_by_backend: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in ctx.characterization: results_by_backend[item["backend_id"]].append(item)
    for backend_id, backend in sorted(ctx.summary["physical_backend_coverage"].items()):
        results = results_by_backend[backend_id]
        available = {
            "structural_tool": any(bool((item.get("structural_metrics") or {}).get("available")) for item in results),
            "physical_area": any(any(item.get(key) is not None for key in ("cell_area", "routed_area")) for item in results),
            "physical_timing": any(any(item.get(key) is not None for key in ("critical_path", "maximum_frequency")) for item in results),
            "physical_energy": any(any(item.get(key) is not None for key in ("encoder_energy", "no_error_decode_energy", "corrected_decode_energy", "due_decode_energy")) for item in results),
            "routing": any(any(item.get(key) is not None for key in ("wirelength", "congestion")) for item in results),
            "mux_controller": any(any(item.get(key) is not None for key in ("mux_area", "mux_energy", "controller_area", "controller_energy")) for item in results),
            "transition_reencoding": any(any(item.get(key) is not None for key in ("transition_energy", "transition_latency", "reencoding_energy")) for item in results),
        }
        backend_rows.append({"backend_id": backend_id, "configured_available": backend["available"], "physical_metrics_available": backend["physical_metrics_available"], "reason": backend["reason"], "available": available})
    matrix = np.array([[int(row["available"][field]) for field in fields] for row in backend_rows])
    fig, ax = plt.subplots(figsize=(11.5, 4.8), layout="constrained")
    ax.imshow(matrix, aspect="auto", cmap=ListedColormap(["#D9D9D9", EVIDENCE_COLORS["structural_tool"]]), norm=BoundaryNorm([-0.5, 0.5, 1.5], 2))
    ax.set_xticks(np.arange(len(fields)), [field.replace("_", "\n") for field in fields], rotation=20, ha="right")
    ax.set_yticks(np.arange(len(backend_rows)), [label(row["backend_id"], 38) for row in backend_rows], fontsize=8)
    for i, row in enumerate(backend_rows):
        for j, field in enumerate(fields): ax.text(j, i, "available" if row["available"][field] else "not\ncharacterized", ha="center", va="center", fontsize=6, color="white" if row["available"][field] else "#333333")
    ax.set_title("Physical-evidence gap: why a physical Pareto frontier is not computable\nGrey means null/unavailable—not zero")
    return {"physical_selection_computable": False, "backend_rows": backend_rows, "physical_gate": ctx.summary["physical_scientific_result_gate"]}, fig


FIGURES: list[tuple[str, str, Callable[[Context], tuple[dict[str, Any], plt.Figure]], Sequence[str], Sequence[Path | str], str, str, Sequence[str]]] = [
    ("registered_portfolio_overview", "Registered portfolio overview", portfolio, ["exact_functional", "unsupported"], [EVALUATION / "implementation_capability_matrix.json", EVALUATION / "ecc_scope_matrix.json", REGISTRY / "registry.json"], "Portfolio identities and verification states, including rejected and experimental inventory entries.", "Bars count implementations per mathematical code; hatching distinguishes partial and rejected status.", ["docs/ECC_CATALOGUE.md", "docs/RESULTS_AND_INTERPRETATION.md"]),
    ("code_rate_redundancy", "Code-rate and redundancy comparison", code_rate, ["exact_functional"], [EVALUATION / "normalized_exact_metrics.json", REGISTRY / "registry.json"], "Parity, rate, and equal-64-bit-payload storage for each registered mathematical code.", "Compare k/n only with the adjacent equal-payload normalization; short-k codes require multiple codewords.", ["docs/CONCEPTS_AND_IDENTITIES.md", "docs/FAIR_COMPARISON.md"]),
    ("capability_verification_heatmap", "Capability-verification heatmap", capability_heatmap, ["exact_functional", "unsupported"], [EVALUATION / "implementation_capability_matrix.json"], "Implementation capability cells marked verified, partial, rejected, unsupported, or not applicable.", "Read across a row: a family label never substitutes for a verified cell.", ["docs/VERIFICATION_METHODOLOGY.md", "docs/RESULTS_AND_INTERPRETATION.md"]),
    ("error_outcome_distributions", "Exact error-outcome distributions", outcomes, ["exact_functional"], [EVALUATION / "implementation_capability_matrix.json"], "Exact outcome proportions over declared verification universes, including SEC-DAEC and cyclic-labelled failures.", "A red hatched share is silent miscorrection; totals are exact tested patterns, not sampled rates.", ["docs/VERIFICATION_METHODOLOGY.md", "docs/RESULTS_AND_INTERPRETATION.md"]),
    ("evidence_availability_matrix", "Evidence-availability matrix", evidence_matrix, ["exact_functional", "analytical_model", "structural_tool", "unsupported"], [EVALUATION / "manifest.json", EVALUATION / "software_study_summary.json"], "Evidence presence for each generated implementation/architecture characterization record.", "Grey cells are not characterized and must not be read as zero.", ["docs/CHARACTERIZATION_AND_EVIDENCE.md", "docs/LIMITATIONS_AND_VALID_CLAIMS.md"]),
    ("structural_complexity_structural_only", "Structural-complexity comparison", structural, ["exact_functional", "structural_tool"], [EVALUATION / "normalized_exact_metrics.json"], "Technology-independent operation counts and structural proxies for selectable implementations.", "Use only for structural comparison; neither axis is physical area, energy, or delay.", ["docs/CHARACTERIZATION_AND_EVIDENCE.md", "docs/RESULTS_AND_INTERPRETATION.md"]),
    ("reliability_cost_pareto_analytical", "Reliability-versus-cost Pareto frontier", reliability_cost, ["exact_functional", "analytical_model"], [EVALUATION / "scenario_selection_results.json"], "Feasible, infeasible, dominated, Pareto, selected, and knee candidates in one traceable scenario.", "Both displayed objectives are minimized; five-objective membership is independently recomputed after hard constraints.", ["docs/PARETO_AND_SELECTION.md", "docs/RESULTS_AND_INTERPRETATION.md"]),
    ("reliability_carbon_pareto_analytical", "Reliability-versus-carbon Pareto frontier", reliability_carbon, ["exact_functional", "analytical_model"], [EVALUATION / "scenario_selection_results.json"], "Analytical SDC versus operational carbon for one traceable scenario; embodied carbon is absent.", "Operational carbon is proportional to scenario energy at fixed grid intensity; no embodied component is fabricated.", ["docs/ENERGY_AND_CARBON_MODELS.md", "docs/PARETO_AND_SELECTION.md"]),
    ("energy_complexity_pareto_analytical", "Energy-versus-complexity Pareto frontier", energy_complexity, ["analytical_model", "structural_tool"], [EVALUATION / "scenario_selection_results.json"], "Analytical energy versus technology-independent logic-depth proxy.", "The horizontal axis is a structural proxy, not measured latency.", ["docs/PARETO_AND_SELECTION.md", "docs/RESULTS_AND_INTERPRETATION.md"]),
    ("multi_scenario_pareto_summary", "Multi-scenario Pareto summary", multi_scenario, ["exact_functional", "analytical_model"], [EVALUATION / "pareto_and_regret.json", EVALUATION / "software_study_summary.json"], "Scenario shares in which each implementation is Pareto-optimal or selected.", "A candidate can be Pareto-optimal without being the minimum-energy winner.", ["docs/RESULTS_AND_INTERPRETATION.md"]),
    ("winner_region_heatmaps", "Winner-region heatmaps", winner_regions, ["exact_functional", "analytical_model"], [EVALUATION / "scenario_selection_results.json", EVALUATION / "scenario_regions.json"], "Categorical winners by fault/reliability region and an exact voltage-temperature slice.", "Cells are computed scenarios or modal aggregates; no categorical interpolation is used.", ["docs/SCENARIOS_AND_WORKLOADS.md", "docs/RESULTS_AND_INTERPRETATION.md"]),
    ("winner_frequency_by_identity", "Winner frequency by identity", winner_identity, ["exact_functional", "analytical_model"], [EVALUATION / "scenario_selection_results.json"], "Winner counts kept separate for code, implementation, and architecture identities.", "Equal counts across panels do not make the identity layers interchangeable.", ["docs/CONCEPTS_AND_IDENTITIES.md", "docs/RESULTS_AND_INTERPRETATION.md"]),
    ("fixed_baseline_regret", "Fixed-baseline regret", baseline_regret, ["analytical_model"], [EVALUATION / "pareto_and_regret.json"], "Analytical energy regret and hard-constraint failures for preregistered fixed baselines.", "Regret is computed only where the baseline is feasible; infeasible scenarios are shown separately.", ["docs/FAIR_COMPARISON.md", "docs/RESULTS_AND_INTERPRETATION.md"]),
    ("recommendation_stability", "Recommendation stability", stability, ["analytical_model"], [EVALUATION / "uncertainty_and_sensitivity.json"], "Base-winner agreement under three deterministic sensitivity parameter sets.", "These are discrete scale cases, not Monte Carlo confidence intervals; seed is not applicable.", ["docs/PARETO_AND_SELECTION.md", "docs/RESULTS_AND_INTERPRETATION.md"]),
    ("sensitivity_ranked", "Ranked sensitivity", sensitivity, ["analytical_model"], [EVALUATION / "scenario_selection_results.json"], "Descriptive grouped-range sensitivity of reliability, energy, carbon, and selection outcome to scenario factors.", "Ranks show association within this preregistered grid, not causal importance beyond it.", ["docs/SCENARIOS_AND_WORKLOADS.md", "docs/RESULTS_AND_INTERPRETATION.md"]),
    ("adaptive_overhead_threshold", "Adaptive-overhead threshold", adaptive_threshold, ["analytical_model", "unsupported"], [EVALUATION / "uncertainty_and_sensitivity.json"], "Net analytical gain as hypothetical adaptation overhead consumes the gross oracle advantage.", "The threshold is parameterized and analytical; missing physical overhead prevents an actual break-even claim.", ["docs/ENERGY_AND_CARBON_MODELS.md", "docs/LIMITATIONS_AND_VALID_CLAIMS.md"]),
    ("physical_evidence_gap", "Physical-evidence gap", physical_gap, ["structural_tool", "unsupported"], [EVALUATION / "framework_summary.json", EVALUATION / "manifest.json"], "Backend coverage matrix showing the absence of physical objectives.", "Generic Yosys structure is available, but physical area, timing, energy, routing, and adaptive overhead remain null.", ["docs/CHARACTERIZATION_AND_EVIDENCE.md", "docs/LIMITATIONS_AND_VALID_CLAIMS.md"]),
]


def generate(root: Path, output_root: Path) -> dict[str, Any]:
    ctx = Context(root)
    pareto_audit = validate_engine_pareto(ctx)
    figure_dir = output_root / "docs" / "figures"
    data_dir = output_root / "docs" / "figure_data"
    figure_dir.mkdir(parents=True, exist_ok=True); data_dir.mkdir(parents=True, exist_ok=True)
    manifest_entries = []
    for figure_id, title, builder, evidence, source_paths, alt_text, caption, included in FIGURES:
        expanded_sources = list(source_paths)
        if figure_id in {"registered_portfolio_overview", "code_rate_redundancy"}:
            expanded_sources.extend(REGISTRY / raw for raw in ctx.registry["codes"])
        if figure_id == "registered_portfolio_overview":
            expanded_sources.extend(REGISTRY / raw for raw in ctx.registry["implementations"])
            expanded_sources.extend(REGISTRY / raw for raw in ctx.registry["architectures"])
        if figure_id in {"capability_verification_heatmap", "error_outcome_distributions"}:
            expanded_sources.extend(
                path.relative_to(root) for path in sorted((root / EVALUATION / "verification").glob("*.json"))
            )
        if figure_id in {"evidence_availability_matrix", "physical_evidence_gap"}:
            expanded_sources.extend(
                path.relative_to(root) for path in sorted((root / EVALUATION / "characterization").glob("*.json"))
            )
        sources = source_records(root, expanded_sources)
        records, fig = builder(ctx)
        data_payload = _source_payload(figure_id, evidence, sources, records)
        data_path = data_dir / f"{figure_id}.json"
        write_json(data_path, data_payload)
        csv_rows = records.get("implementation_rows") or records.get("code_rows") or records.get("baseline_rows") or records.get("factor_rows") or records.get("uncertainty_rows")
        csv_path = None
        if isinstance(csv_rows, list) and csv_rows and all(isinstance(row, Mapping) and not any(isinstance(value, (dict, list)) for value in row.values()) for row in csv_rows):
            csv_path = data_dir / f"{figure_id}.csv"; write_csv(csv_path, csv_rows)
        names = save_figure(fig, figure_dir / figure_id)
        files = {extension: {"path": f"docs/figures/{name}", "sha256": sha256(figure_dir / name)} for extension, name in names.items()}
        data_files = [{"path": f"docs/figure_data/{data_path.name}", "sha256": sha256(data_path)}]
        if csv_path is not None: data_files.append({"path": f"docs/figure_data/{csv_path.name}", "sha256": sha256(csv_path)})
        manifest_entries.append({"figure_id": figure_id, "title": title, "evidence_classes": list(evidence), "alt_text": alt_text, "caption": caption, "source_artifacts": sources, "figure_data": data_files, "files": files, "generation_command": "python scripts/generate_documentation_figures.py", "included_in": list(included)})
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "generator": "scripts/generate_documentation_figures.py",
        "png_dpi": 320,
        "deterministic_ordering": True,
        "pareto_validation": pareto_audit,
        "figures": manifest_entries,
        "omitted_figures": [
            {"figure_id": "physical_pareto_frontier", "reason": "all physical objectives are null; a physical Pareto frontier is not computable", "evidence_class": "unsupported"},
            {"figure_id": "embodied_carbon_pareto", "reason": "the scenario study contains operational carbon only; implementation-specific embodied carbon provenance is unavailable", "evidence_class": "unsupported"},
            {"figure_id": "measured_latency_pareto", "reason": "no characterized timing or measured delay is available; the generated energy-complexity plot uses an explicit structural depth proxy", "evidence_class": "unsupported"},
        ],
    }
    manifest["manifest_sha256"] = canonical_hash(manifest)
    write_json(data_dir / "figure_manifest.json", manifest)
    return manifest


def check(root: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="green-ecc-doc-figures-") as raw:
        temporary = Path(raw)
        manifest = generate(root, temporary)
        expected = []
        for figure in manifest["figures"]:
            expected.extend(item["path"] for item in figure["files"].values())
            expected.extend(item["path"] for item in figure["figure_data"])
        expected.append("docs/figure_data/figure_manifest.json")
        stale = []
        for relative in expected:
            actual = root / relative; regenerated = temporary / relative
            if not actual.exists(): stale.append(f"missing: {relative}")
            elif sha256(actual) != sha256(regenerated): stale.append(f"stale: {relative}")
        if stale:
            raise SystemExit("Documentation figures are stale:\n" + "\n".join(stale))
    print(f"Documentation figure check passed: {len(manifest['figures'])} figures; independent Pareto audit {manifest['pareto_validation']['scenarios_checked']}/0 mismatches")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true", help="Regenerate in a temporary directory and compare hashes without modifying documentation")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    if args.check:
        check(root)
    else:
        manifest = generate(root, root)
        print(json.dumps({"figures_generated": len(manifest["figures"]), "png_dpi": manifest["png_dpi"], "pareto_scenarios_independently_validated": manifest["pareto_validation"]["scenarios_checked"], "manifest": "docs/figure_data/figure_manifest.json"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
