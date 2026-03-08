from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ecc_selector import select
from ml.sram_advisory import run_sram_advisory


KNOWN_SCHEMES = ["SEC", "SECDED", "DEC", "TAEC", "DAEC", "BCH", "Reed-Solomon", "Polar", "Reed-Polar"]
SUPPORTED_FAULT_MODES = ["sbu", "dbu", "adjacent_dbu", "mbu", "burst", "random"]

FAULT_TO_MBU = {
    "sbu": "light",
    "dbu": "light",
    "adjacent_dbu": "light",
    "mbu": "moderate",
    "burst": "heavy",
    "random": "moderate",
}


def _mkdirs(base: Path) -> dict[str, Path]:
    dirs = {
        "root": base,
        "summary": base / "summary",
        "data": base / "data",
        "tables": base / "tables",
        "plots": base / "plots",
        "ml": base / "ml",
    }
    for p in dirs.values():
        p.mkdir(parents=True, exist_ok=True)
    return dirs


@dataclass
class ToolkitInput:
    sram_capacity_gib: float
    word_length_bits: int
    tech_node_nm: int
    vdd_volts: float
    temperature_c: float
    ber: float | None = None
    ser: float | None = None
    altitude_km: float = 0.0
    burst_length: int = 1
    fault_modes: tuple[str, ...] = ("sbu", "dbu", "mbu", "burst")
    carbon_intensity_kgco2_per_kwh: float = 0.55
    grid_score: float | None = None
    required_correction: int | None = None
    energy_budget: float | None = None
    sustainability_mode: bool = False
    ml_enabled: bool = False
    ml_model: Path | None = None
    ml_confidence_min: float | None = None
    ml_ood_max: float | None = None
    output_dir: Path = Path("results/run")


def _validate(inp: ToolkitInput) -> None:
    if inp.sram_capacity_gib <= 0:
        raise ValueError("sram_capacity_gib must be > 0")
    if inp.word_length_bits <= 0:
        raise ValueError("word_length_bits must be > 0")
    if inp.vdd_volts <= 0:
        raise ValueError("vdd_volts must be > 0")
    if inp.temperature_c < -273.15:
        raise ValueError("temperature_c is below absolute zero")
    if inp.ber is not None and inp.ber < 0:
        raise ValueError("ber must be non-negative")
    if inp.ser is not None and inp.ser < 0:
        raise ValueError("ser must be non-negative")


def _candidate_codes(word_bits: int) -> tuple[list[str], list[dict[str, str]], list[dict[str, str]]]:
    implemented: list[str] = []
    evaluated: list[dict[str, str]] = []
    known_not_evaluated: list[dict[str, str]] = []

    if word_bits in (8, 16, 32):
        mapping = {
            "SECDED": f"sram-secded-{word_bits}",
            "TAEC": f"sram-taec-{word_bits}",
            "BCH": f"sram-bch-{word_bits}",
            "Polar": f"sram-polar-{word_bits}",
        }
    elif word_bits == 64:
        mapping = {
            "SECDED": "sec-ded-64",
            "DAEC": "sec-daec-64",
            "TAEC": "taec-64",
            "BCH": "bch-63",
            "Polar": "polar-64-48",
        }
    else:
        mapping = {}

    for scheme in KNOWN_SCHEMES:
        if scheme in mapping:
            code = mapping[scheme]
            implemented.append(code)
            evaluated.append({"ecc_name": scheme, "selector_code": code})
        else:
            known_not_evaluated.append({"ecc_name": scheme, "reason": "not implemented in current codebase"})
    return implemented, evaluated, known_not_evaluated


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({k for row in rows for k in row.keys()}) if rows else []
    with path.open("w", newline="", encoding="utf-8") as fh:
        if not fieldnames:
            fh.write("\n")
            return
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _pareto_flags(rows: list[dict[str, Any]], x_key: str, y_key: str) -> set[int]:
    idxs: set[int] = set()
    for i, a in enumerate(rows):
        ax = a.get(x_key)
        ay = a.get(y_key)
        if ax is None or ay is None:
            continue
        dominated = False
        for j, b in enumerate(rows):
            if i == j:
                continue
            bx = b.get(x_key)
            by = b.get(y_key)
            if bx is None or by is None:
                continue
            if bx <= ax and by <= ay and (bx < ax or by < ay):
                dominated = True
                break
        if not dominated:
            idxs.add(i)
    return idxs


def _plot_scatter(rows: list[dict[str, Any]], x: str, y: str, out: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    xs = [r.get(x) for r in rows]
    ys = [r.get(y) for r in rows]
    labels = [r.get("ecc_name", r.get("code", "?")) for r in rows]
    valid = [(a, b, l) for a, b, l in zip(xs, ys, labels) if a is not None and b is not None]
    if valid:
        if any(isinstance(v[0], str) for v in valid):
            cats = []
            for v in valid:
                if v[0] not in cats:
                    cats.append(v[0])
            xs_num = [cats.index(v[0]) for v in valid]
            ax.scatter(xs_num, [v[1] for v in valid], s=40)
            ax.set_xticks(range(len(cats)))
            ax.set_xticklabels(cats, rotation=25, ha="right")
            for vx, vy, lbl in zip(xs_num, [v[1] for v in valid], [v[2] for v in valid]):
                ax.annotate(lbl, (vx, vy), fontsize=7)
        else:
            ax.scatter([v[0] for v in valid], [v[1] for v in valid], s=40)
            for vx, vy, lbl in valid:
                ax.annotate(lbl, (vx, vy), fontsize=7)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def evaluate_toolkit(inp: ToolkitInput) -> dict[str, Any]:
    _validate(inp)
    dirs = _mkdirs(inp.output_dir)

    codes, evaluated, known_not_evaluated = _candidate_codes(inp.word_length_bits)
    if not codes:
        raise ValueError("No implemented ECC codes for this word length")

    rows: list[dict[str, Any]] = []
    unsupported_fault_modes: list[str] = []

    for fault_mode in inp.fault_modes:
        if fault_mode not in SUPPORTED_FAULT_MODES:
            unsupported_fault_modes.append(fault_mode)
            continue

        res = select(
            codes,
            node=inp.tech_node_nm,
            vdd=inp.vdd_volts,
            temp=inp.temperature_c,
            capacity_gib=inp.sram_capacity_gib,
            ci=inp.carbon_intensity_kgco2_per_kwh,
            bitcell_um2=0.08,
            mbu=FAULT_TO_MBU[fault_mode],
            scrub_s=10.0,
            alt_km=inp.altitude_km,
            flux_rel=None,
            lifetime_h=8760.0,
        )

        best_code = res.get("best", {}).get("code") if isinstance(res.get("best"), dict) else None
        for rec in res.get("candidate_records", []):
            e_kwh = float(rec.get("E_dyn_kWh", 0.0)) + float(rec.get("E_leak_kWh", 0.0)) + float(rec.get("E_scrub_kWh", 0.0))
            operational_carbon = inp.carbon_intensity_kgco2_per_kwh * e_kwh
            embodied = max(0.0, float(rec.get("carbon_kg", 0.0)) - operational_carbon)
            rows.append(
                {
                    "run_id": res.get("scenario_hash"),
                    "ecc_name": rec.get("family"),
                    "ecc_family": rec.get("family"),
                    "code": rec.get("code"),
                    "fault_mode": fault_mode,
                    "fault_model_requested": fault_mode,
                    "fault_model_simulated": "selector_mbu_class",
                    "fault_model_approximated": True,
                    "capacity_bits": int(inp.sram_capacity_gib * (2**30) * 8),
                    "word_length_bits": inp.word_length_bits,
                    "node_nm": inp.tech_node_nm,
                    "vdd": inp.vdd_volts,
                    "temp_c": inp.temperature_c,
                    "ber_input": inp.ber,
                    "ser_input": inp.ser,
                    "altitude_input": inp.altitude_km,
                    "energy_per_read_j": None,
                    "energy_per_write_j": None,
                    "energy_total_j": e_kwh * 3_600_000.0,
                    "area_overhead_percent": rec.get("redundancy_overhead_pct"),
                    "gate_overhead": None,
                    "operational_carbon_kgco2e": operational_carbon,
                    "embodied_carbon_kgco2e": embodied,
                    "total_carbon_kgco2e": rec.get("carbon_kg"),
                    "grid_score": inp.grid_score,
                    "carbon_intensity": inp.carbon_intensity_kgco2_per_kwh,
                    "GREEN_Score": rec.get("GS"),
                    "ESII": rec.get("ESII"),
                    "NESII": rec.get("NESII"),
                    "FIT": rec.get("FIT"),
                    "feasible": True,
                    "infeasible_reason": None,
                    "deterministic_selected": rec.get("code") == best_code,
                    "ml_recommended": None,
                    "ml_confidence": None,
                    "ml_ood": None,
                    "fallback_used": None,
                }
            )

    pareto_energy = _pareto_flags(rows, "energy_total_j", "FIT")
    pareto_carbon = _pareto_flags(rows, "total_carbon_kgco2e", "FIT")
    for i, row in enumerate(rows):
        row["pareto_optimal_energy_reliability"] = i in pareto_energy
        row["pareto_optimal_carbon_reliability"] = i in pareto_carbon
        row["pareto_optimal"] = row["pareto_optimal_energy_reliability"] or row["pareto_optimal_carbon_reliability"]
        row["pareto_rank"] = 1 if row["pareto_optimal"] else 2

    ml_meta: dict[str, Any] = {"ml_enabled": False, "status": "disabled"}
    if inp.ml_enabled:
        if inp.ml_model and inp.ml_model.exists() and rows:
            base_rows = [r for r in rows if r["fault_mode"] == inp.fault_modes[0]]
            candidate_records = []
            for r in base_rows:
                candidate_records.append(
                    {
                        "code": r["code"],
                        "FIT": r["FIT"],
                        "latency_ns": 0.0,
                        "area_logic_mm2": 0.0,
                        "area_macro_mm2": 0.0,
                        "node": inp.tech_node_nm,
                        "vdd": inp.vdd_volts,
                        "temp": inp.temperature_c,
                        "capacity_gib": inp.sram_capacity_gib,
                        "ci": inp.carbon_intensity_kgco2_per_kwh,
                        "bitcell_um2": 0.08,
                        "scrub_s": 10.0,
                        "NESII": r.get("NESII", 0.0),
                    }
                )
            baseline = next((r["code"] for r in base_rows if r["deterministic_selected"]), None)
            ml_meta = run_sram_advisory(
                model_dir=inp.ml_model,
                candidates=candidate_records,
                baseline_choice=baseline,
                size_kb=max(1, int(inp.sram_capacity_gib * 1024 * 1024)),
                word_bits=inp.word_length_bits,
                fault_model=inp.fault_modes[0],
                iterations=1,
                confidence_min_override=inp.ml_confidence_min,
                ood_threshold_override=inp.ml_ood_max,
            )
            for row in rows:
                row["ml_recommended"] = ml_meta.get("advisory_choice")
                row["ml_confidence"] = ml_meta.get("advisory_confidence")
                row["ml_ood"] = ml_meta.get("advisory_ood_score")
                row["fallback_used"] = ml_meta.get("fallback_used")
        else:
            ml_meta = {"ml_enabled": True, "status": "unavailable_model", "reason": "model not provided or missing"}

    _write_csv(dirs["data"] / "all_candidates.csv", rows)
    (dirs["data"] / "all_candidates.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    _write_csv(dirs["data"] / "feasible_candidates.csv", [r for r in rows if r.get("feasible")])
    _write_csv(dirs["data"] / "infeasible_candidates.csv", [r for r in rows if not r.get("feasible")])

    per_ecc = {}
    for row in rows:
        per_ecc.setdefault(row["code"], []).append(row)
    per_ecc_rows = []
    for code, code_rows in per_ecc.items():
        per_ecc_rows.append(
            {
                "code": code,
                "ecc_name": code_rows[0].get("ecc_name"),
                "fault_modes_evaluated": len(code_rows),
                "avg_fit": sum(float(r.get("FIT", 0.0)) for r in code_rows) / len(code_rows),
                "avg_total_carbon_kgco2e": sum(float(r.get("total_carbon_kgco2e", 0.0)) for r in code_rows) / len(code_rows),
                "avg_energy_total_j": sum(float(r.get("energy_total_j", 0.0)) for r in code_rows) / len(code_rows),
            }
        )
        _write_csv(dirs["tables"] / f"{code.replace('-', '_')}_table.csv", code_rows)
    _write_csv(dirs["data"] / "per_ecc_summary.csv", per_ecc_rows)

    per_fault = {}
    for row in rows:
        per_fault.setdefault(row["fault_mode"], []).append(row)
    per_fault_rows = []
    for fm, fm_rows in per_fault.items():
        per_fault_rows.append(
            {
                "fault_mode": fm,
                "candidates": len(fm_rows),
                "best_fit": min(float(r.get("FIT", math.inf)) for r in fm_rows),
                "best_carbon": min(float(r.get("total_carbon_kgco2e", math.inf)) for r in fm_rows),
            }
        )
    _write_csv(dirs["data"] / "per_faultmode_summary.csv", per_fault_rows)

    _write_csv(dirs["tables"] / "ecc_comparison_full.csv", rows)
    _write_csv(dirs["tables"] / "ecc_comparison_condensed.csv", per_ecc_rows)

    pareto_rows = [r for r in rows if r.get("pareto_optimal")]
    _write_csv(dirs["data"] / "pareto_points.csv", pareto_rows)
    (dirs["data"] / "pareto_points.json").write_text(json.dumps(pareto_rows, indent=2), encoding="utf-8")

    metric_defs = {
        "FIT": "Failures in Time metric from selector logic (minimize)",
        "energy_total_j": "Total energy converted from selector kWh terms (minimize)",
        "total_carbon_kgco2e": "Total carbon from selector (minimize)",
        "GREEN_Score": "Green score from gs.py integration (maximize)",
        "ESII": "ESII value from esii.py (maximize)",
        "NESII": "Normalized ESII used by selector (maximize)",
    }
    (dirs["data"] / "metric_definitions.json").write_text(json.dumps(metric_defs, indent=2), encoding="utf-8")
    calibration_used = {
        "carbon_intensity_kgco2_per_kwh": inp.carbon_intensity_kgco2_per_kwh,
        "grid_score": inp.grid_score,
        "assumptions": [
            "Operational carbon computed from selector energy terms and provided carbon intensity.",
            "Embodied carbon inferred as total minus operational; values may be approximate depending on selector outputs.",
            "Fault model mapping uses existing selector MBU classes.",
        ],
    }
    (dirs["data"] / "calibration_used.json").write_text(json.dumps(calibration_used, indent=2), encoding="utf-8")

    _plot_scatter(rows, "energy_total_j", "FIT", dirs["plots"] / "pareto_energy_vs_reliability.png", "Pareto: energy vs reliability")
    _plot_scatter(rows, "operational_carbon_kgco2e", "FIT", dirs["plots"] / "pareto_carbon_vs_reliability.png", "Pareto: op carbon vs reliability")
    _plot_scatter(rows, "total_carbon_kgco2e", "FIT", dirs["plots"] / "pareto_total_carbon_vs_reliability.png", "Pareto: total carbon vs reliability")
    _plot_scatter(rows, "GREEN_Score", "FIT", dirs["plots"] / "pareto_green_score_ranking.png", "GREEN score ranking")
    _plot_scatter(rows, "ESII", "FIT", dirs["plots"] / "ranking_esii.png", "ESII ranking")
    _plot_scatter(rows, "NESII", "FIT", dirs["plots"] / "ranking_nesii.png", "NESII ranking")
    _plot_scatter(rows, "vdd", "FIT", dirs["plots"] / "selected_ecc_vs_vdd.png", "VDD vs reliability")
    _plot_scatter(rows, "ber_input", "FIT", dirs["plots"] / "selected_ecc_vs_ber.png", "BER vs reliability")
    _plot_scatter(rows, "ecc_name", "energy_total_j", dirs["plots"] / "energy_vs_ecc.png", "Energy vs ECC")
    _plot_scatter(rows, "ecc_name", "total_carbon_kgco2e", dirs["plots"] / "carbon_vs_ecc.png", "Carbon vs ECC")
    _plot_scatter(rows, "fault_mode", "FIT", dirs["plots"] / "faultmode_comparison.png", "Fault mode comparison")

    integrated_report = {
        "run_configuration": asdict(inp),
        "ecc_schemes_evaluated": evaluated,
        "known_but_not_evaluated": known_not_evaluated,
        "fault_modes_requested": list(inp.fault_modes),
        "fault_modes_simulated": sorted({r["fault_mode"] for r in rows}),
        "unsupported_fault_modes": unsupported_fault_modes,
        "calibration_context": calibration_used,
        "deterministic_recommendation": next((r for r in rows if r.get("deterministic_selected")), None),
        "ml_advisory": ml_meta,
        "limitations": [
            "Per-read/per-write energy metrics are unavailable in current selector outputs.",
            "Decoder complexity and detailed matrix metadata are unavailable for most schemes in Python workflow.",
            "Fault mode simulation is mapped to selector MBU classes and marked as approximation.",
        ],
    }
    (dirs["summary"] / "integrated_report.json").write_text(json.dumps(integrated_report, indent=2, default=str), encoding="utf-8")

    md = [
        "# Integrated ECC Evaluation Report",
        "",
        "## Run configuration",
        "```json",
        json.dumps(asdict(inp), indent=2, default=str),
        "```",
        "",
        "## ECC schemes evaluated",
        json.dumps(evaluated, indent=2),
        "",
        "## Known but not evaluated",
        json.dumps(known_not_evaluated, indent=2),
        "",
        "## Fault modes",
        f"Requested: {', '.join(inp.fault_modes)}",
        f"Simulated: {', '.join(sorted({r['fault_mode'] for r in rows}))}",
        f"Unsupported: {', '.join(unsupported_fault_modes) if unsupported_fault_modes else 'none'}",
        "",
        "## Deterministic recommendation",
        json.dumps(integrated_report["deterministic_recommendation"], indent=2, default=str),
        "",
        "## ML advisory (separate)",
        json.dumps(ml_meta, indent=2, default=str),
        "",
        "## Limitations",
    ]
    md.extend([f"- {x}" for x in integrated_report["limitations"]])
    (dirs["summary"] / "integrated_report.md").write_text("\n".join(md), encoding="utf-8")

    (dirs["summary"] / "executive_summary.txt").write_text(
        f"Evaluated {len(per_ecc_rows)} ECC schemes across {len(per_fault_rows)} fault modes. "
        f"Deterministic recommendation: {integrated_report['deterministic_recommendation']['code'] if integrated_report['deterministic_recommendation'] else 'none'}.\n",
        encoding="utf-8",
    )

    ml_json = dirs["ml"] / "ml_advisory_output.json"
    ml_json.write_text(json.dumps(ml_meta, indent=2, default=str), encoding="utf-8")
    (dirs["ml"] / "ml_feature_snapshot.json").write_text(
        json.dumps({"features": ["node", "vdd", "temp", "capacity_gib", "code"], "status": "available_when_model_present"}, indent=2),
        encoding="utf-8",
    )
    (dirs["ml"] / "ml_inference_summary.txt").write_text(
        "ML remains advisory-only. Deterministic baseline selection governs final recommendation.\n"
        + json.dumps(ml_meta, indent=2, default=str),
        encoding="utf-8",
    )
    (dirs["ml"] / "ml_confidence_report.json").write_text(json.dumps(ml_meta, indent=2, default=str), encoding="utf-8")
    _write_csv(
        dirs["ml"] / "ml_vs_baseline.csv",
        [
            {
                "baseline_choice": integrated_report["deterministic_recommendation"]["code"] if integrated_report["deterministic_recommendation"] else None,
                "ml_advisory_choice": ml_meta.get("advisory_choice"),
                "ml_used": ml_meta.get("ml_used"),
                "fallback_used": ml_meta.get("fallback_used"),
            }
        ],
    )

    return {
        "output_dir": str(inp.output_dir),
        "rows": len(rows),
        "evaluated_schemes": len(per_ecc_rows),
        "fault_modes": len(per_fault_rows),
    }
