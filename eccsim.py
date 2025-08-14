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

from esii import ESIIInputs, compute_esii, KWH_PER_J
from carbon import embodied_kg, operational_kg, default_alpha
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
    esii_parser.add_argument("--embodied-kg", type=float)
    esii_parser.add_argument(
        "--embodied-override-kg",
        type=str,
        default="none",
        help="Use this embodied carbon value instead of computing from area",
    )
    esii_parser.add_argument(
        "--basis", choices=["per_gib", "system"], required=True
    )
    esii_parser.add_argument("--out", type=Path)

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
            e_dyn_kwh = energy["dynamic_kWh"]
            e_leak_kwh = energy["leakage_kWh"]
        else:
            if args.e_dyn_j is None or args.e_leak_j is None:
                parser.error("Provide --energy or both --e-dyn-j and --e-leak-j")
            e_dyn_kwh = args.e_dyn_j / KWH_PER_J
            e_leak_kwh = args.e_leak_j / KWH_PER_J

        embodied: float | None = None
        if args.embodied_override_kg.lower() != "none":
            embodied = float(args.embodied_override_kg)
        elif args.embodied_kg is not None:
            embodied = args.embodied_kg
        elif args.area:
            area = json.load(open(args.area))
            logic_mm2 = area["logic_mm2"]
            macro_mm2 = area["macro_mm2"]
            node_nm = area["node_nm"]
            alpha_logic, alpha_macro = default_alpha(node_nm)
            embodied = embodied_kg(logic_mm2, macro_mm2, alpha_logic, alpha_macro)
        else:
            parser.error(
                "Provide --embodied-kg, --area or --embodied-override-kg"
            )

        inp = ESIIInputs(
            fit_base=fit_base,
            fit_ecc=fit_ecc,
            e_dyn=e_dyn_kwh,
            e_leak=e_leak_kwh,
            ci_kg_per_kwh=args.ci,
            embodied_kg=embodied,
            energy_units="kWh",
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
                "ci": args.ci,
                "embodied_kg": embodied,
            },
            "carbon": {
                "operational_kg": result["operational_kg"],
                "embodied_kg": embodied,
                "total_kg": result["total_carbon_kg"],
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

        embodied = embodied_kg(area_logic, area_macro, alpha_logic, alpha_macro)
        operational = operational_kg(args.Edyn, args.Eleak, args.ci)
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
            print(f"{'Dynamic (kWh)':<15} {result['dynamic_kWh']:.3e}")
            print(f"{'Leakage (kWh)':<15} {result['leakage_kWh']:.3e}")
            print(f"{'Total (kWh)':<15} {result['total_kWh']:.3e}")
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
