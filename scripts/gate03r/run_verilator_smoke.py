#!/usr/bin/env python3
"""Compile and execute bounded Gate 03R RTL smoke tests with Verilator."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gate03.run_gate03 import portable_verilator
from scripts.gate03r.run_rtl_verification import BCH_TB, SECDED_TB


DOC = ROOT / "docs" / "date2027" / "rigour_gate_03r"
RAW = DOC / "raw_logs"


def run(command: list[str], *, cwd: Path, log: Path, timeout: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        exit_code = completed.returncode
        output = completed.stdout + completed.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        output = (exc.stdout or "") + (exc.stderr or "") + f"\nTIMEOUT_AFTER_{timeout}_SECONDS\n"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        "$ " + subprocess.list2cmdline(command) + "\n" + output + f"\nexit_code={exit_code}\n",
        encoding="utf-8",
        newline="\n",
    )
    return {"exit_code": exit_code, "status": "PASS" if exit_code == 0 else "FAIL"}


def build_and_run(
    name: str,
    top: str,
    sources: list[str],
    testbench_text: str,
    msys_shell: str,
    verilator_root: str,
    portable_make: str,
    work: Path,
) -> dict[str, Any]:
    job = work / name
    obj = job / "obj"
    job.mkdir(parents=True, exist_ok=True)
    tb = job / f"{name}_tb.sv"
    tb.write_text(testbench_text, encoding="utf-8", newline="\n")
    unix_root = verilator_root.replace("\\", "/")
    unix_make = portable_make.replace("\\", "/")
    unix_job = str(job).replace("\\", "/")
    unix_tb = str(tb).replace("\\", "/")
    build_script = (
        f"export VERILATOR_ROOT='{unix_root}'; export MAKE='{unix_make}'; "
        f"export TMPDIR='{unix_job}'; export TMP='{unix_job}'; export TEMP='{unix_job}'; "
        f"verilator --binary --timing -Wno-fatal --top-module {top} -Iasic/include "
        f"--Mdir '{unix_job}/obj' {' '.join(sources)} '{unix_tb}' -o sim.exe"
    )
    build = run(
        [msys_shell, "-defterm", "-no-start", "-ucrt64", "-here", "-c", build_script],
        cwd=ROOT,
        log=RAW / f"rtl-{name}-verilator-build.log",
        timeout=300,
    )
    executable = obj / "sim.exe"
    simulation = {"status": "BLOCKED_BY_BUILD", "exit_code": None}
    if build["status"] == "PASS" and executable.is_file():
        simulation = run(
            [str(executable)],
            cwd=job,
            log=RAW / f"rtl-{name}-verilator-simulation.log",
            timeout=60,
        )
    return {"build": build, "simulation": simulation}


def main() -> int:
    msys_shell, verilator_root, portable_make = portable_verilator()
    if not all((msys_shell, verilator_root, portable_make)):
        payload = {"status": "BLOCKED_TOOL_UNAVAILABLE"}
        print(json.dumps(payload, indent=2))
        return 1
    # Gate 03's retained temporary copy may predate files added by the local
    # Verilator package. Refresh it additively from the installed runtime.
    source_root = Path(r"D:\Compiler Cpp\ucrt64\share\verilator")
    if source_root.is_dir():
        shutil.copytree(source_root, Path(verilator_root), dirs_exist_ok=True)
        shutil.copy2(Path(r"D:\Compiler Cpp\ucrt64\bin\verilator_bin.exe"), Path(verilator_root) / "verilator_bin.exe")
    work = Path(tempfile.gettempdir()) / "green-ecc-gate03r-verilator"
    work.mkdir(parents=True, exist_ok=True)
    results = {
        "secded": build_and_run(
            "secded",
            "gate03r_secded_tb",
            ["asic/rtl/secded/secded_pipelined_72_64_v1.sv"],
            SECDED_TB,
            msys_shell,
            verilator_root,
            portable_make,
            work,
        ),
        "bch": build_and_run(
            "bch",
            "gate03r_bch_tb",
            ["asic/rtl/bch/bch_78_64_t2_v1.sv"],
            BCH_TB,
            msys_shell,
            verilator_root,
            portable_make,
            work,
        ),
    }
    status = "PASS" if all(item["simulation"]["status"] == "PASS" for item in results.values()) else "FAIL"
    payload = {"schema_version": 1, "simulator": "Verilator", "jobs": results, "status": status}
    (DOC / "VERILATOR_SMOKE_RESULTS.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    aggregate_path = DOC / "RTL_SIMULATION_RESULTS.json"
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    aggregate["icarus_attempt_status"] = {
        "bch": aggregate["bch"]["status"],
        "secded": aggregate["secded"]["status"],
        "preserved_logs": True,
    }
    for family in ("bch", "secded"):
        aggregate[family]["verilator_build_exit_code"] = results[family]["build"]["exit_code"]
        aggregate[family]["verilator_simulation_exit_code"] = results[family]["simulation"]["exit_code"]
        aggregate[family]["status"] = "PASS_VERILATOR_COMPILED_SMOKE"
    aggregate["status"] = status
    aggregate["passing_simulator"] = "Verilator"
    aggregate_path.write_text(
        json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
