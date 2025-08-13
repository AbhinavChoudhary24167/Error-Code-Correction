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
from dataclasses import asdict

from esii import compute_esii
from ser_model import HazuchaParams, ser_hazucha, flux_from_location
from fit import (
    compute_fit_pre,
    compute_fit_post,
    ecc_coverage_factory,
    fit_system,
    mttf_from_fit,
    FitEstimate,
)


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

    esii_parser = sub.add_parser("esii", help="Compute the ESII metric")
    esii_parser.add_argument("--fit-base", type=float, required=True)
    esii_parser.add_argument("--fit-ecc", type=float, required=True)
    esii_parser.add_argument("--E-dyn", type=float, required=True)
    esii_parser.add_argument("--E-leak", type=float, required=True)
    esii_parser.add_argument("--ci", type=float, required=True)
    esii_parser.add_argument("--EC-embodied", type=float, required=True)

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
    report_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "esii":
        result = compute_esii(
            args.fit_base,
            args.fit_ecc,
            args.E_dyn,
            args.E_leak,
            args.ci,
            args.EC_embodied,
        )
        dynamic = args.E_dyn * args.ci
        leakage = args.E_leak * args.ci
        embodied = args.EC_embodied
        total = dynamic + leakage + embodied
        print(f"ESII: {result:.3f}")
        print("Breakdown:")
        print(f"{'Dynamic (kgCO2e)':<20} {dynamic:.3f}")
        print(f"{'Leakage (kgCO2e)':<20} {leakage:.3f}")
        print(f"{'Embodied (kgCO2e)':<20} {embodied:.3f}")
        print(f"{'Total (kgCO2e)':<20} {total:.3f}")
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
            fit_sys = fit_system(args.capacity_gib, fit_post)
            mttf = mttf_from_fit(fit_sys.nominal if isinstance(fit_sys, FitEstimate) else fit_sys)
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
                json_result = {
                    k: (asdict(v) if isinstance(v, FitEstimate) else v)
                    for k, v in result.items()
                }
                json.dump(json_result, sys.stdout)
                sys.stdout.write("\n")
                print(report_str, file=sys.stderr)
            else:
                print(report_str)
            return

    # If no command is provided the parser will show usage via argparse


if __name__ == "__main__":
    main()
