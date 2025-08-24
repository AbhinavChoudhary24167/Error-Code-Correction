#!/usr/bin/env python3
"""Command line entry point for ECC simulations.

Currently this binary exposes only version information which combines:

* the Git commit hash,
* the SHA256 hash of ``tech_calib.json``, and
* the semantic version string stored in ``VERSION``.

The script will be extended in the future to provide additional simulation
interfaces.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
from pathlib import Path
import json
import sys
from typing import Dict

from esii import ESIIInputs, compute_esii
from carbon import embodied_kgco2e, operational_kgco2e, default_alpha
from ser_model import HazuchaParams, ser_hazucha, flux_from_location
from fit import (
    compute_fit_pre,
    compute_fit_post,
    ecc_coverage_factory,
    fit_system,
    mttf_from_fit,
    FitEstimate,
)
from energy_model import energy_report
from ecc_selector import select


def _format_reliability_report(result: dict) -> str:
    """Return a human-readable reliability report string.

    Parameters
    ----------
    result:
        Mapping of metric names to values as produced by the reliability
        backend.

    Returns
    -------
    str
        Multi-line string with metrics in a stable order, formatted to three
        significant figures for floats.
    """

    order = [
        "qcrit",
        "qs",
        "flux_rel",
        "fit_bit",
        "fit_word_pre",
        "fit_word_post",
        "fit_system",
        "mttf",
    ]

    lines = []
    for key in order:
        value = result[key]
        if isinstance(value, FitEstimate):
            if value.stddev is not None:
                lines.append(
                    f"{key:<15} {value.nominal:.3e} ± {value.stddev:.1e}"
                )
            else:
                lines.append(f"{key:<15} {value.nominal:.3e}")
        elif isinstance(value, float):
            lines.append(f"{key:<15} {value:.3e}")
        else:
            lines.append(f"{key:<15} {value}")
    return "\n".join(lines)


def _git_hash() -> str:
    """Return the current Git commit hash or ``unknown`` if unavailable."""
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


def _file_hash(path: Path) -> str:
    """Return the SHA256 hash for the contents of ``path``."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> None:
    repo_path = Path(__file__).resolve().parent
    version_base = (repo_path / "VERSION").read_text().strip()
    tech_hash = _file_hash(repo_path / "tech_calib.json")
    git_hash = _git_hash()

    parser = argparse.ArgumentParser(description="ECC simulator")
    parser.add_argument(
        "--version",
        action="version",
        version=f"{git_hash} {tech_hash} {version_base}",
    )
    sub = parser.add_subparsers(dest="command")

    energy_parser = sub.add_parser("energy", help="Estimate energy use")
    energy_parser.add_argument(
        "--code", type=str, required=True, choices=["sec-ded", "sec-daec", "taec"]
    )
    energy_parser.add_argument("--node", type=float, required=True)
    energy_parser.add_argument("--vdd", type=float, required=True)
    energy_parser.add_argument("--temp", type=float, required=True)
    energy_parser.add_argument("--ops", type=float, required=True)
    energy_parser.add_argument("--lifetime-h", type=float, required=True)
    energy_parser.add_argument(
        "--report", type=str, choices=["json"], default=None
    )

    carbon_parser = sub.add_parser("carbon", help="Estimate carbon footprint")
    carbon_parser.add_argument(
        "--areas",
        type=str,
        required=True,
        help="Comma separated logic and macro areas in mm^2",
    )
    carbon_parser.add_argument(
        "--alpha",
        type=str,
        required=True,
        help="Comma separated alpha factors for logic and macros",
    )
    carbon_parser.add_argument("--ci", type=float, required=True)
    carbon_parser.add_argument("--Edyn", type=float, required=True)
    carbon_parser.add_argument("--Eleak", type=float, required=True)

    esii_parser = sub.add_parser("esii", help="Compute the ESII metric")
    esii_parser.add_argument("--reliability", type=Path)
    esii_parser.add_argument("--energy", type=Path)
    esii_parser.add_argument("--area", type=Path)
    esii_parser.add_argument("--fit-base", type=float)
    esii_parser.add_argument("--fit-ecc", type=float)
    esii_parser.add_argument("--e-dyn-j", type=float)
    esii_parser.add_argument("--e-leak-j", type=float)
    esii_parser.add_argument("--ci", type=float, required=True)
    esii_parser.add_argument("--embodied-kgco2e", type=float)
    esii_parser.add_argument(
        "--embodied-override-kgco2e",
        type=str,
        default="none",
        help="Use this embodied carbon value instead of computing from area",
    )
    esii_parser.add_argument(
        "--basis", choices=["per_gib", "system"], required=True
    )
    esii_parser.add_argument("--out", type=Path)

    select_parser = sub.add_parser(
        "select", help="Multi-objective ECC selection"
    )
    select_parser.add_argument(
        "--codes",
        type=str,
        required=True,
        help="Comma separated code identifiers",
    )
    select_parser.add_argument(
        "--weights",
        type=str,
        default="1.0,1.0,0.25",
        help="Comma separated weights for reliability, carbon, latency",
    )
    select_parser.add_argument(
        "--constraints",
        type=str,
        default="",
        help="Comma separated key=value constraints",
    )
    select_parser.add_argument("--node", type=int, required=True)
    select_parser.add_argument("--vdd", type=float, required=True)
    select_parser.add_argument("--temp", type=float, required=True)
    select_parser.add_argument("--mbu", type=str, default="moderate")
    select_parser.add_argument("--scrub-s", type=float, default=10.0)
    select_parser.add_argument("--capacity-gib", type=float, required=True)
    select_parser.add_argument("--ci", type=float, required=True)
    select_parser.add_argument("--bitcell-um2", type=float, required=True)
    select_parser.add_argument("--lifetime-h", type=float, default=float("nan"))
    select_parser.add_argument("--ci-source", type=str, default="unspecified")
    select_parser.add_argument("--report", type=Path, default=None)
    select_parser.add_argument("--plot", type=Path, default=None)
    select_parser.add_argument(
        "--emit-candidates", type=Path, default=None, help="Write feasible candidates to CSV"
    )

    analyze_parser = sub.add_parser("analyze", help="Post-selection analysis")
    analyze_sub = analyze_parser.add_subparsers(dest="analyze_command")

    trade_parser = analyze_sub.add_parser("tradeoffs", help="Quantify trade-offs")
    trade_parser.add_argument("--from", dest="from_csv", type=Path, required=True)
    trade_parser.add_argument("--out", type=Path, required=True)
    trade_parser.add_argument("--basis", choices=["per_gib", "system"], default="per_gib")
    trade_parser.add_argument("--filter", type=str, default=None)
    trade_parser.add_argument("--seed", type=int, default=0)
    trade_parser.add_argument("--resamples", type=int, default=10000)

    arch_parser = analyze_sub.add_parser("archetype", help="Classify archetypes")
    arch_parser.add_argument("--from", dest="from_csv", type=Path, required=True)
    arch_parser.add_argument("--out", type=Path, required=True)

    surface_parser = analyze_sub.add_parser(
        "surface", help="Analyse feasible surface from candidates"
    )
    surface_parser.add_argument(
        "--from-candidates", dest="cand_csv", type=Path, required=True
    )
    surface_parser.add_argument("--out-csv", dest="out_csv", type=Path, required=True)
    surface_parser.add_argument("--plot", type=Path, default=None)

    sens_parser = analyze_sub.add_parser(
        "sensitivity", help="One-factor sensitivity analysis"
    )
    sens_parser.add_argument("--factor", type=str, required=True)
    sens_parser.add_argument("--grid", type=str, required=True)
    sens_parser.add_argument("--from", dest="from_json", type=Path, required=True)
    sens_parser.add_argument("--out", type=Path, required=True)

    reliability_parser = sub.add_parser(
        "reliability", help="Reliability calculations"
    )
    reliability_sub = reliability_parser.add_subparsers(dest="reliability_command")

    hazucha_parser = reliability_sub.add_parser(
        "hazucha", help="Hazucha-Svensson SER model"
    )
    hazucha_parser.add_argument("--qcrit", type=float, required=True)
    hazucha_parser.add_argument("--qs", type=float, required=True)
    hazucha_parser.add_argument("--area", type=float, required=True)
    hazucha_parser.add_argument("--alt-km", type=float, default=0.0)
    hazucha_parser.add_argument("--latitude", type=float, default=45.0)
    hazucha_parser.add_argument("--flux-rel", type=float, default=None)

    report_parser = reliability_sub.add_parser(
        "report", help="Generate reliability report"
    )
    report_parser.add_argument("--qcrit", type=float, required=True)
    report_parser.add_argument("--qs", type=float, required=True)
    report_parser.add_argument("--area", type=float, required=True)
    report_parser.add_argument("--alt-km", type=float, default=0.0)
    report_parser.add_argument("--latitude", type=float, default=45.0)
    report_parser.add_argument("--flux-rel", type=float, default=None)
    report_parser.add_argument("--word-bits", type=int, default=64)
    report_parser.add_argument(
        "--ecc",
        type=str,
        default="SEC-DED",
        choices=["SEC-DED", "SEC-DAEC", "TAEC"],
    )
    report_parser.add_argument("--scrub-interval", type=float, default=0.0)
    report_parser.add_argument("--capacity-gib", type=float, default=1.0)
    report_parser.add_argument("--basis", choices=["per_gib", "system"], default="per_gib")
    report_parser.add_argument("--mbu", type=str, default="none")
    report_parser.add_argument("--node-nm", type=int, required=True)
    report_parser.add_argument("--vdd", type=float, required=True)
    report_parser.add_argument("--tempC", type=float, required=True)
    report_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "analyze":
        if args.analyze_command == "tradeoffs":
            from analysis.tradeoff import TradeoffConfig, analyze_tradeoffs

            cfg = TradeoffConfig(
                n_resamples=args.resamples,
                seed=args.seed,
                filter_expr=args.filter,
                basis=args.basis,
            )
            analyze_tradeoffs(args.from_csv, args.out, cfg)
        elif args.analyze_command == "archetype":
            from analysis.archetype import classify_archetypes

            classify_archetypes(args.from_csv, args.out)
        elif args.analyze_command == "surface":
            from analysis.surface import analyze_surface

            analyze_surface(args.cand_csv, args.out_csv, args.plot)
        elif args.analyze_command == "sensitivity":
            from analysis.sensitivity import analyze_sensitivity

            grid_vals = [float(x) for x in args.grid.split(",") if x.strip()]
            analyze_sensitivity(args.from_json, args.factor, grid_vals, args.out)
        else:
            parser.error("analyze subcommand required")
        return

    if args.command == "select":
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
        try:
            w_vals = [float(x) for x in args.weights.split(",")]
            weights = {
                "reliability": w_vals[0],
                "carbon": w_vals[1],
                "latency": w_vals[2] if len(w_vals) > 2 else 0.0,
            }
        except Exception:
            parser.error("--weights must be three comma separated floats")

        constraints: Dict[str, float] = {}
        if args.constraints:
            for part in args.constraints.split(","):
                if not part:
                    continue
                try:
                    k, v = part.split("=")
                    constraints[k] = float(v)
                except Exception:
                    parser.error("Invalid constraint format")

        params = {
            "node": args.node,
            "vdd": args.vdd,
            "temp": args.temp,
            "capacity_gib": args.capacity_gib,
            "ci": args.ci,
            "bitcell_um2": args.bitcell_um2,
            "lifetime_h": args.lifetime_h,
            "ci_source": args.ci_source,
        }

        result = select(
            codes,
            weights=weights,
            constraints=constraints,
            mbu=args.mbu,
            scrub_s=args.scrub_s,
            **params,
        )

        if args.report:
            import csv

            fieldnames = [
                "code",
                "scrub_s",
                "FIT",
                "carbon_kg",
                "latency_ns",
                "ESII",
                "NESII",
                "p5",
                "p95",
                "N_scale",
                "area_logic_mm2",
                "area_macro_mm2",
                "E_dyn_kWh",
                "E_leak_kWh",
                "E_scrub_kWh",
                "notes",
            ]
            with open(args.report, "w", newline="") as fh:
                writer = csv.DictWriter(
                    fh, fieldnames=fieldnames, extrasaction="ignore"
                )
                writer.writeheader()
                for rec in result["pareto"]:
                    writer.writerow(rec)

        if args.emit_candidates:
            import csv

            fieldnames = [
                "code",
                "scrub_s",
                "FIT",
                "carbon_kg",
                "latency_ns",
                "ESII",
                "NESII",
                "areas",
                "energies",
                "violations",
                "scenario_hash",
            ]
            with open(args.emit_candidates, "w", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                for rec in result.get("candidate_records", []):
                    areas = {
                        "logic_mm2": rec.get("area_logic_mm2", 0.0),
                        "macro_mm2": rec.get("area_macro_mm2", 0.0),
                    }
                    energies = {
                        "E_dyn_kWh": rec.get("E_dyn_kWh", 0.0),
                        "E_leak_kWh": rec.get("E_leak_kWh", 0.0),
                        "E_scrub_kWh": rec.get("E_scrub_kWh", 0.0),
                    }
                    row = {
                        "code": rec.get("code"),
                        "scrub_s": rec.get("scrub_s"),
                        "FIT": rec.get("FIT"),
                        "carbon_kg": rec.get("carbon_kg"),
                        "latency_ns": rec.get("latency_ns"),
                        "ESII": rec.get("ESII"),
                        "NESII": rec.get("NESII"),
                        "areas": json.dumps(areas, sort_keys=True),
                        "energies": json.dumps(energies, sort_keys=True),
                        "violations": json.dumps(rec.get("violations", []), sort_keys=True),
                        "scenario_hash": result.get("scenario_hash"),
                    }
                    writer.writerow(row)

        if args.plot:
            try:
                import matplotlib.pyplot as plt  # type: ignore
            except Exception:  # pragma: no cover - optional dependency
                print("matplotlib not available; skipping plot", file=sys.stderr)
            else:
                xs = [r["carbon_kg"] for r in result["pareto"]]
                ys = [r["FIT"] for r in result["pareto"]]
                plt.scatter(xs, ys)
                for r in result["pareto"]:
                    plt.annotate(r["code"], (r["carbon_kg"], r["FIT"]))
                plt.xlabel("carbon_kg")
                plt.ylabel("FIT")
                plt.tight_layout()
                plt.savefig(args.plot)

        if result["best"]:
            print(result["best"]["code"])
        return

    if args.command == "esii":
        fit_base: float
        fit_ecc: float
        basis = args.basis

        if args.reliability:
            rel = json.load(open(args.reliability))
            fit_base = rel["fit"]["base"]
            fit_ecc = rel["fit"]["ecc"]
            if rel.get("basis") and rel["basis"] != basis:
                parser.error("Basis mismatch between --basis and reliability report")
        else:
            if args.fit_base is None or args.fit_ecc is None:
                parser.error(
                    "Provide --reliability or both --fit-base and --fit-ecc"
                )
            fit_base = args.fit_base
            fit_ecc = args.fit_ecc

        if args.energy:
            energy = json.load(open(args.energy))
            e_dyn_j = energy["dynamic_J"]
            e_leak_j = energy["leakage_J"]
        else:
            if args.e_dyn_j is None or args.e_leak_j is None:
                parser.error("Provide --energy or both --e-dyn-j and --e-leak-j")
            e_dyn_j = args.e_dyn_j
            e_leak_j = args.e_leak_j

        embodied: float | None = None
        if args.embodied_override_kgco2e.lower() != "none":
            embodied = float(args.embodied_override_kgco2e)
        elif args.embodied_kgco2e is not None:
            embodied = args.embodied_kgco2e
        elif args.area:
            area = json.load(open(args.area))
            logic_mm2 = area["logic_mm2"]
            macro_mm2 = area["macro_mm2"]
            node_nm = area["node_nm"]
            alpha_logic, alpha_macro = default_alpha(node_nm)
            embodied = embodied_kgco2e(logic_mm2, macro_mm2, alpha_logic, alpha_macro)
        else:
            parser.error(
                "Provide --embodied-kgco2e, --area or --embodied-override-kgco2e"
            )

        inp = ESIIInputs(
            fit_base=fit_base,
            fit_ecc=fit_ecc,
            e_dyn=e_dyn_j,
            e_leak=e_leak_j,
            e_scrub=0.0,
            ci_kgco2e_per_kwh=args.ci,
            embodied_kgco2e=embodied,
        )
        result = compute_esii(inp)

        provenance = {
            "git": git_hash,
            "tech_calib": tech_hash,
            "qcrit": _file_hash(repo_path / "data" / "qcrit_sram6t.json"),
        }
        out = {
            "provenance": provenance,
            "basis": basis,
            "inputs": {
                "fit_base": fit_base,
                "fit_ecc": fit_ecc,
                "E_dyn_kWh": result["E_dyn_kWh"],
                "E_leak_kWh": result["E_leak_kWh"],
                "E_scrub_kWh": result["E_scrub_kWh"],
                "ci_kgCO2e_per_kWh": args.ci,
                "embodied_kgCO2e": embodied,
            },
            "carbon": {
                "operational_kgCO2e": result["operational_kgCO2e"],
                "embodied_kgCO2e": embodied,
                "total_kgCO2e": result["total_kgCO2e"],
            },
            "delta_FIT": result["delta_FIT"],
            "ESII": result["ESII"],
        }

        if args.out:
            json.dump(out, open(args.out, "w"))
        else:
            json.dump(out, sys.stdout)
            sys.stdout.write("\n")
        return

    if args.command == "carbon":
        try:
            area_logic, area_macro = [float(x) for x in args.areas.split(",")]
            alpha_logic, alpha_macro = [float(x) for x in args.alpha.split(",")]
        except Exception:
            parser.error("--areas and --alpha require two comma separated floats")

        embodied = embodied_kgco2e(area_logic, area_macro, alpha_logic, alpha_macro)
        operational = operational_kgco2e(args.Edyn, args.Eleak, args.ci, 0.0)
        total = embodied + operational
        print(f"{'Embodied (kgCO2e)':<20} {embodied:.3f}")
        print(f"{'Operational (kgCO2e)':<20} {operational:.3f}")
        print(f"{'Total (kgCO2e)':<20} {total:.3f}")
        return

    if args.command == "energy":
        result = energy_report(
            args.code,
            args.node,
            args.vdd,
            args.temp,
            args.ops,
            args.lifetime_h,
        )
        if args.report == "json":
            json.dump(result, sys.stdout)
            sys.stdout.write("\n")
        else:
            print(f"{'Dynamic (J)':<15} {result['dynamic_J']:.3e}")
            print(f"{'Leakage (J)':<15} {result['leakage_J']:.3e}")
            print(f"{'Total (J)':<15} {result['total_J']:.3e}")
        return

    if args.command == "reliability":
        if args.reliability_command == "hazucha":
            flux = flux_from_location(
                args.alt_km, args.latitude, flux_rel=args.flux_rel
            )
            hp = HazuchaParams(
                Qs_fC=args.qs, flux_rel=flux, area_um2=args.area
            )
            fit = ser_hazucha(args.qcrit, hp)
            print(f"{fit:.3e}")
            return
        if args.reliability_command == "report":
            flux = flux_from_location(
                args.alt_km, args.latitude, flux_rel=args.flux_rel
            )
            hp = HazuchaParams(
                Qs_fC=args.qs, flux_rel=flux, area_um2=args.area
            )
            fit_bit = ser_hazucha(args.qcrit, hp)
            mbu_rates = {}
            fit_pre = compute_fit_pre(args.word_bits, fit_bit, mbu_rates)
            coverage = ecc_coverage_factory(args.ecc)
            fit_post = compute_fit_post(
                args.word_bits, fit_bit, mbu_rates, coverage, args.scrub_interval
            )
            if args.basis == "system":
                fit_base = fit_system(args.capacity_gib, fit_pre)
                fit_ecc = fit_system(args.capacity_gib, fit_post)
            else:
                fit_base = fit_system(1.0, fit_pre)
                fit_ecc = fit_system(1.0, fit_post)

            fit_sys = fit_system(args.capacity_gib, fit_post)
            mttf = mttf_from_fit(
                fit_sys.nominal if isinstance(fit_sys, FitEstimate) else fit_sys
            )
            result = {
                "qcrit": args.qcrit,
                "qs": args.qs,
                "flux_rel": flux,
                "fit_bit": fit_bit,
                "fit_word_pre": fit_pre,
                "fit_word_post": fit_post,
                "fit_system": fit_sys,
                "mttf": mttf,
            }
            report_str = _format_reliability_report(result)
            if args.json:
                json_out = {
                    "basis": args.basis,
                    "fit": {
                        "base": fit_base.nominal
                        if isinstance(fit_base, FitEstimate)
                        else fit_base,
                        "ecc": fit_ecc.nominal
                        if isinstance(fit_ecc, FitEstimate)
                        else fit_ecc,
                    },
                    "mbu": args.mbu,
                    "scrub_s": args.scrub_interval,
                    "node_nm": args.node_nm,
                    "vdd": args.vdd,
                    "tempC": args.tempC,
                }
                json.dump(json_out, sys.stdout)
                sys.stdout.write("\n")
                print(report_str, file=sys.stderr)
            else:
                print(report_str)
            return

    # If no command is provided the parser will show usage via argparse


if __name__ == "__main__":
    main()
