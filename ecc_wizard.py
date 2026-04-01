#!/usr/bin/env python3
"""Interactive guided frontend for ECCSim workflows.

This module is intentionally additive: it shells out to the existing eccsim.py
CLI so all backend logic, artifacts, and output schemas remain unchanged.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parent
ECCSIM_PATH = REPO_ROOT / "eccsim.py"

SPECIAL_HELP = {"help", "?"}
SPECIAL_QUIT = {"quit", "q", "exit"}
SPECIAL_BACK = {"back", "b"}


@dataclass(frozen=True)
class FieldSpec:
    key: str
    prompt: str
    default: str | None = None
    validator: Callable[[str], str] | None = None


class WizardControl(Exception):
    def __init__(self, action: str):
        self.action = action


def _is_float(value: str) -> str:
    float(value)
    return value


def _is_int(value: str) -> str:
    int(value)
    return value


def _is_path_exists(value: str) -> str:
    if not Path(value).exists():
        raise ValueError(f"Path not found: {value}")
    return value


def _csv_nonempty(value: str) -> str:
    parts = [p.strip() for p in value.split(",") if p.strip()]
    if not parts:
        raise ValueError("Provide at least one comma-separated value")
    return ",".join(parts)


def _enum(*allowed: str) -> Callable[[str], str]:
    allowed_set = {item.lower(): item for item in allowed}

    def _validate(value: str) -> str:
        key = value.lower()
        if key not in allowed_set:
            raise ValueError(f"Expected one of {', '.join(allowed)}")
        return allowed_set[key]

    return _validate


def _print_special_help() -> None:
    print("[help] show this help, [back] go to previous menu, [quit] exit wizard")


def _prompt(field: FieldSpec) -> str:
    while True:
        suffix = f" [{field.default}]" if field.default is not None else ""
        raw = input(f"{field.prompt}{suffix}: ").strip()
        lowered = raw.lower()
        if lowered in SPECIAL_HELP:
            _print_special_help()
            continue
        if lowered in SPECIAL_BACK:
            raise WizardControl("back")
        if lowered in SPECIAL_QUIT:
            raise WizardControl("quit")
        if not raw and field.default is not None:
            raw = field.default
        if not raw:
            print("Input required.")
            continue
        try:
            return field.validator(raw) if field.validator else raw
        except ValueError as exc:
            print(f"Invalid value: {exc}")


def _show_mode_header(title: str, theory: str, examples: list[str], inference: list[str]) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    print(theory)
    print("\nExample command(s):")
    for ex in examples:
        print(f"  {ex}")
    print("\nOutput interpretation notes:")
    for line in inference:
        print(f"  - {line}")
    print()


def _command_action(command: list[str]) -> None:
    full = [sys.executable, str(ECCSIM_PATH), *command]
    pretty = " ".join(shlex.quote(p) for p in ["python", "eccsim.py", *command])
    print("Generated command:")
    print(f"  {pretty}")
    choice = input("Choose action: [1] run [2] print only [3] save command > ").strip()
    if choice == "1":
        proc = subprocess.run(full, cwd=REPO_ROOT, text=True, capture_output=True)
        if proc.stdout:
            print(proc.stdout.rstrip())
        if proc.returncode != 0:
            if proc.stderr:
                print(proc.stderr.rstrip())
            print(f"Command failed with exit code {proc.returncode}")
        elif proc.stderr:
            print(proc.stderr.rstrip())
    elif choice == "2":
        print("Command not executed.")
    elif choice == "3":
        out = input("Save path for command text file: ").strip()
        Path(out).write_text(pretty + "\n", encoding="utf-8")
        print(f"Saved command to {out}")
    else:
        print("Unknown option, returning to menu.")


def _collect(fields: list[FieldSpec]) -> dict[str, str]:
    values: dict[str, str] = {}
    for field in fields:
        values[field.key] = _prompt(field)
    return values


def _energy_mode() -> None:
    _show_mode_header(
        "1) Energy Estimation Mode",
        "Computes dynamic, leakage, and total energy for an ECC operating point. "
        "Use this when comparing workload-driven versus idle-dominated regimes.",
        [
            "python eccsim.py energy --code sec-ded --node 7 --vdd 0.8 --temp 45 --ops 1000000 --lifetime-h 8760",
        ],
        [
            "Dynamic term scales with operations and switching activity.",
            "Leakage dominates in long-lifetime, low-activity deployments.",
            "Total energy reflects both always-on and access-driven components.",
        ],
    )
    vals = _collect(
        [
            FieldSpec("code", "ECC code (sec-ded/sec-daec/taec/polar)", "sec-ded", _enum("sec-ded", "sec-daec", "taec", "polar")),
            FieldSpec("node", "Node (nm)", "7", _is_float),
            FieldSpec("vdd", "Supply voltage V", "0.8", _is_float),
            FieldSpec("temp", "Temperature C", "45", _is_float),
            FieldSpec("ops", "Operations count", "1000000", _is_float),
            FieldSpec("lifetime", "Lifetime hours", "8760", _is_float),
        ]
    )
    _command_action(["energy", "--code", vals["code"], "--node", vals["node"], "--vdd", vals["vdd"], "--temp", vals["temp"], "--ops", vals["ops"], "--lifetime-h", vals["lifetime"]])


def _carbon_mode() -> None:
    mode = input("Choose carbon mode: [a] legacy [b] calibrated: ").strip().lower()
    calibrated = mode == "b"
    _show_mode_header(
        "2) Carbon Estimation Mode",
        "Estimates embodied and operational carbon impacts for ECC scenarios. "
        "Legacy mode uses area/alpha inputs; calibrated mode adds node/lifetime/grid context.",
        [
            "python eccsim.py carbon --areas 0.1,0.2 --alpha 120,140 --ci 0.55 --Edyn 0.01 --Eleak 0.02",
            "python eccsim.py carbon --calibrated --node 7 --area-cm2 0.15 --grid-region global_avg --years 5 --accesses-per-day 1000000 --areas 0.1,0.2 --alpha 120,140 --ci 0.55 --Edyn 0.01 --Eleak 0.02",
        ],
        [
            "Embodied carbon links mostly to area/manufacturing assumptions.",
            "Operational carbon scales with energy and grid intensity/workload.",
            "Total carbon exposes manufacturing vs usage tradeoffs.",
        ],
    )
    base = _collect(
        [
            FieldSpec("areas", "Areas CSV (mm^2)", "0.1,0.2", _csv_nonempty),
            FieldSpec("alpha", "Alpha CSV", "120,140", _csv_nonempty),
            FieldSpec("ci", "Carbon intensity", "0.55", _is_float),
            FieldSpec("Edyn", "Dynamic energy kWh", "0.01", _is_float),
            FieldSpec("Eleak", "Leakage energy kWh", "0.02", _is_float),
        ]
    )
    cmd = ["carbon", "--areas", base["areas"], "--alpha", base["alpha"], "--ci", base["ci"], "--Edyn", base["Edyn"], "--Eleak", base["Eleak"]]
    if calibrated:
        extra = _collect(
            [
                FieldSpec("node", "Node (nm)", "7", _is_int),
                FieldSpec("area", "Area cm^2", "0.15", _is_float),
                FieldSpec("grid", "Grid region", "global_avg"),
                FieldSpec("years", "Lifetime years", "5", _is_float),
                FieldSpec("accesses", "Accesses per day", "1000000", _is_float),
            ]
        )
        cmd.extend(["--calibrated", "--node", extra["node"], "--area-cm2", extra["area"], "--grid-region", extra["grid"], "--years", extra["years"], "--accesses-per-day", extra["accesses"]])
    _command_action(cmd)


def _selection_mode() -> None:
    constrained = input("Selection path: [a] unconstrained [b] constrained: ").strip().lower() == "b"
    _show_mode_header(
        "3) ECC Selection Mode",
        "Runs deterministic multi-objective candidate ranking across FIT/carbon/latency. "
        "Use constraints to hard-filter infeasible designs while preserving deterministic choice rules.",
        [
            "python eccsim.py select --codes sec-ded-64,sec-daec-64,taec-64,bch-63 --node 7 --vdd 0.8 --temp 45 --mbu moderate --capacity-gib 16 --ci 0.55 --bitcell-um2 0.08",
            "python eccsim.py select --codes sec-ded-64,sec-daec-64,taec-64,bch-63 --node 7 --vdd 0.8 --temp 45 --mbu moderate --capacity-gib 16 --ci 0.55 --bitcell-um2 0.08 --constraints fit_max=1e-9,latency_ns_max=10,carbon_kg_max=5",
        ],
        [
            "Chosen code is deterministic under the configured objective/constraints.",
            "Candidate table shows tradeoffs across reliability, latency, and sustainability metrics.",
            "Constraint feasibility indicates hard-filter pass/fail before ranking.",
        ],
    )
    vals = _collect(
        [
            FieldSpec("codes", "Codes CSV", "sec-ded-64,sec-daec-64,taec-64,bch-63", _csv_nonempty),
            FieldSpec("node", "Node (nm)", "7", _is_int),
            FieldSpec("vdd", "VDD", "0.8", _is_float),
            FieldSpec("temp", "Temp C", "45", _is_float),
            FieldSpec("mbu", "MBU class", "moderate", _enum("light", "moderate", "heavy")),
            FieldSpec("capacity", "Capacity GiB", "16", _is_float),
            FieldSpec("ci", "Carbon intensity", "0.55", _is_float),
            FieldSpec("bitcell", "Bitcell um^2", "0.08", _is_float),
        ]
    )
    cmd = ["select", "--codes", vals["codes"], "--node", vals["node"], "--vdd", vals["vdd"], "--temp", vals["temp"], "--mbu", vals["mbu"], "--capacity-gib", vals["capacity"], "--ci", vals["ci"], "--bitcell-um2", vals["bitcell"]]
    if constrained:
        constraints = _prompt(FieldSpec("constraints", "Constraints CSV", "fit_max=1e-9,latency_ns_max=10,carbon_kg_max=5", _csv_nonempty))
        cmd.extend(["--constraints", constraints])
    _command_action(cmd)


def _reliability_mode() -> None:
    sub = input("Reliability flow: [a] Hazucha [b] report: ").strip().lower()
    _show_mode_header(
        "4) Reliability Path",
        "Analyzes upset susceptibility and ECC mitigation efficacy. "
        "Hazucha mode is compact SER intuition; report mode provides FIT/MTTF style system-level context.",
        [
            "python eccsim.py reliability hazucha --qcrit 0.4 --qs 1.0 --area 1.0",
            "python eccsim.py reliability report --qs 1.0 --area 1.0 --node-nm 14 --vdd 0.8 --tempC 75 --ecc SEC-DED --mbu moderate --basis per_gib --json",
        ],
        [
            "FIT and MTTF quantify failure exposure before/after ECC coverage.",
            "Pre/post-ECC deltas show protection value under the same environment.",
            "Basis parameter distinguishes per-GiB normalized view vs system-wide totals.",
        ],
    )
    if sub == "a":
        vals = _collect([FieldSpec("qcrit", "qcrit", "0.4", _is_float), FieldSpec("qs", "qs", "1.0", _is_float), FieldSpec("area", "area", "1.0", _is_float)])
        _command_action(["reliability", "hazucha", "--qcrit", vals["qcrit"], "--qs", vals["qs"], "--area", vals["area"]])
    else:
        vals = _collect([
            FieldSpec("qs", "qs", "1.0", _is_float),
            FieldSpec("area", "area", "1.0", _is_float),
            FieldSpec("node", "node-nm", "14", _is_int),
            FieldSpec("vdd", "vdd", "0.8", _is_float),
            FieldSpec("temp", "tempC", "75", _is_float),
            FieldSpec("ecc", "ECC label", "SEC-DED"),
            FieldSpec("mbu", "MBU class", "moderate", _enum("light", "moderate", "heavy")),
            FieldSpec("basis", "basis", "per_gib", _enum("per_gib", "system")),
        ])
        _command_action(["reliability", "report", "--qs", vals["qs"], "--area", vals["area"], "--node-nm", vals["node"], "--vdd", vals["vdd"], "--tempC", vals["temp"], "--ecc", vals["ecc"], "--mbu", vals["mbu"], "--basis", vals["basis"], "--json"])


def _integrated_mode() -> None:
    _show_mode_header(
        "5) Integrated Tool Workflow Mode",
        "Runs end-to-end evaluation and emits data/tables/plots/summary artifacts in one package. "
        "This mode is intended for comparative studies and demo-ready report generation.",
        [
            "python eccsim.py evaluate --capacity 8 --word-length 64 --node 14 --vdd 0.8 --temp 75 --fault-modes sbu dbu mbu burst --ci 0.55 --grid-score 0.62 --outdir results/run1",
        ],
        [
            "Generated package includes Pareto views and per-metric ranking plots where data is available.",
            "ESII/NESII/GREEN score traces are included from existing integrated toolkit outputs.",
            "Summary/data/tables/plots are written under the chosen outdir.",
        ],
    )
    vals = _collect([
        FieldSpec("capacity", "capacity GiB", "8", _is_float),
        FieldSpec("word", "word length bits", "64", _is_int),
        FieldSpec("node", "node nm", "14", _is_int),
        FieldSpec("vdd", "vdd", "0.8", _is_float),
        FieldSpec("temp", "temp C", "75", _is_float),
        FieldSpec("fault", "fault modes (space-separated)", "sbu dbu mbu burst"),
        FieldSpec("ci", "carbon intensity", "0.55", _is_float),
        FieldSpec("grid", "grid score", "0.62", _is_float),
        FieldSpec("outdir", "output directory", "results/run1"),
    ])
    cmd = [
        "evaluate", "--capacity", vals["capacity"], "--word-length", vals["word"], "--node", vals["node"],
        "--vdd", vals["vdd"], "--temp", vals["temp"], "--fault-modes", *vals["fault"].split(), "--ci", vals["ci"],
        "--grid-score", vals["grid"], "--outdir", vals["outdir"],
    ]
    _command_action(cmd)


def _config_mode() -> None:
    _show_mode_header(
        "6) Configuration Driven Run",
        "Executes integrated evaluation from a JSON config, useful for reproducibility and batch studies.",
        ["python eccsim.py compare --input-config config.json --outdir results/run2"],
        [
            "Config path centralizes scenario definition and reduces CLI repetition.",
            "Use this for signoff-like replayable runs under version control.",
        ],
    )
    vals = _collect([FieldSpec("config", "input config path", validator=_is_path_exists), FieldSpec("outdir", "output directory", "results/run2")])
    _command_action(["compare", "--input-config", vals["config"], "--outdir", vals["outdir"]])


def _ml_mode() -> None:
    _show_mode_header(
        "7) Optional ML Advisory Workflow Mode",
        "ML remains advisory-only. Deterministic selector output is authoritative, with confidence/OOD gates controlling fallback.",
        [
            "python eccsim.py ml build-dataset ...",
            "python eccsim.py ml split-dataset ...",
            "python eccsim.py ml train ...",
            "python eccsim.py ml evaluate ...",
            "python eccsim.py ml check-drift ...",
        ],
        [
            "Confidence quantifies advisory certainty under the trained manifold.",
            "OOD score signals distribution mismatch and can trigger deterministic fallback.",
            "Advisory mode helps accelerate exploration while preserving baseline rigor.",
        ],
    )
    print("This mode is instructional. Use the displayed sequence and --help for each ml subcommand.")


MODES: dict[str, tuple[str, Callable[[], None]]] = {
    "1": ("Energy Estimation Mode", _energy_mode),
    "2": ("Carbon Estimation Mode", _carbon_mode),
    "3": ("ECC Selection Mode", _selection_mode),
    "4": ("Reliability Path", _reliability_mode),
    "5": ("Integrated Tool Workflow Mode", _integrated_mode),
    "6": ("Configuration Driven Run", _config_mode),
    "7": ("Optional ML Advisory Workflow Mode", _ml_mode),
}


def run_wizard() -> int:
    print("ECC Guided Workflow Wizard")
    while True:
        print("\nSelect a mode:")
        for key, (name, _) in MODES.items():
            print(f"  {key}. {name}")
        print("  q. Quit")
        choice = input("Mode: ").strip().lower()
        if choice in SPECIAL_QUIT:
            return 0
        mode = MODES.get(choice)
        if not mode:
            print("Invalid choice. Enter 1-7, or q.")
            continue
        try:
            mode[1]()
        except WizardControl as ctrl:
            if ctrl.action == "quit":
                return 0
            print("Returning to main menu.")


def main() -> None:
    raise SystemExit(run_wizard())


if __name__ == "__main__":
    main()
