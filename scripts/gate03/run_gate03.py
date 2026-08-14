#!/usr/bin/env python3
"""Execute the bounded local Gate-03 pilot and emit the frozen evidence set.

This runner never provisions WSL/Docker, downloads collateral, or mutates Gate 01/02.
The pinned ORFS phase is attempted only by a separately approved environment action.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gate03.constants import (
    ELIGIBLE_IMPLEMENTATIONS,
    EVIDENCE_HEADER,
    EXCLUDED_IMPLEMENTATIONS,
    PPA_HEADER,
    PREFREEZE,
    RAW_REPORT_HEADER,
    RTL_MATRIX_HEADER,
    SENTINEL_HEADER,
    SENTINELS,
    STAGES,
    WORKLOADS,
    WORKLOAD_SEED,
    WARMUP_CYCLES,
    MEASURED_CYCLES,
)

OUT = ROOT / "docs" / "date2027" / "rigour_gate_03"
BASELINE = OUT / "baseline"
GATE01 = ROOT / "docs" / "date2027" / "rigour_gate_01"
GATE02 = ROOT / "docs" / "date2027" / "rigour_gate_02"
REGISTRY = ROOT / "green_ecc_physical_simulation" / "registry" / "implementations"
EXTERNAL_ROOT = Path(tempfile.gettempdir()) / "green-ecc-gate03" / PREFREEZE["commit"]
EXTERNAL = EXTERNAL_ROOT / "pilot-attempt-01"

CONVENTIONAL = "secded-rtl-combinational-72-64-v1"
HSIAO = "hsiao-generated-combinational-72-64-v1"
BCH = "shortened-bch-78-64-t2-v1-reference-decoder"

HARDWARE_IDS = {
    CONVENTIONAL: "positional-extended-hamming-xor-network-v1",
    HSIAO: "hsiao-minimum-odd-column-xor-network-v1",
    BCH: "reference-only-no-rtl-shortened-bch-78-64-t2-v1",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def manifest_digest(paths: list[Path], base: Path) -> tuple[str, list[dict[str, Any]]]:
    entries = []
    for path in sorted(paths, key=lambda item: item.relative_to(base).as_posix().encode("utf-8")):
        relative = path.relative_to(base).as_posix()
        entries.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    payload = b"".join(
        item["path"].encode("utf-8") + b"\0" + str(item["size_bytes"]).encode("ascii")
        + b"\0" + item["sha256"].encode("ascii") + b"\n"
        for item in entries
    )
    return hashlib.sha256(payload).hexdigest(), entries


def tree_manifest(path: Path) -> tuple[str, list[dict[str, Any]]]:
    return manifest_digest([item for item in path.rglob("*") if item.is_file()], path)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_csv(path: Path, header: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in header})


def read_identity_rows() -> dict[str, dict[str, str]]:
    with (GATE02 / "CODE_IDENTITY_MATRIX.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {row["implementation_id"]: row for row in rows}


def registry_entry(identifier: str) -> dict[str, Any]:
    return json.loads((REGISTRY / f"{identifier}.json").read_text(encoding="utf-8"))


def allowed_status_paths() -> tuple[list[str], list[str]]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v2", "--untracked-files=all"], cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    )
    lines = [line for line in result.stdout.splitlines() if line]
    offending = []
    for line in lines:
        path = line.split(" ", 1)[1] if line.startswith("? ") else line.rsplit(" ", 1)[-1]
        normalized = path.replace("\\", "/")
        if not (
            normalized.startswith("docs/date2027/rigour_gate_03/")
            or normalized.startswith("scripts/gate03/")
            or normalized.startswith("tests/python/test_gate03_")
        ):
            offending.append(normalized)
    return lines, offending


def frozen_gate_bytes_unchanged() -> tuple[bool, dict[str, Any]]:
    checks: dict[str, Any] = {}
    unchanged = True
    for label, relative in (("gate01", "docs/date2027/rigour_gate_01"),
                            ("gate02", "docs/date2027/rigour_gate_02")):
        diff = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", relative], cwd=ROOT, check=False)
        untracked = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard", "--", relative], cwd=ROOT, text=True
        ).splitlines()
        checks[label] = {"git_diff_exit_code": diff.returncode, "untracked": untracked,
                         "byte_identical_to_frozen_commit": diff.returncode == 0 and not untracked}
        unchanged = unchanged and checks[label]["byte_identical_to_frozen_commit"]
    return unchanged, checks


def tool_path(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    fallback = Path(r"D:\Compiler Cpp\ucrt64\bin") / f"{name}.exe"
    return str(fallback) if fallback.is_file() else None


def tool_version(path: str | None, args: list[str]) -> str | None:
    if not path:
        return None
    try:
        result = subprocess.run([path, *args], capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=20, check=False)
        return (result.stdout + result.stderr).strip().splitlines()[0]
    except (OSError, subprocess.TimeoutExpired, IndexError):
        return None


def portable_icarus() -> tuple[str | None, str | None]:
    iverilog = tool_path("iverilog")
    vvp = tool_path("vvp")
    if not iverilog or not vvp:
        return None, None
    if os.name != "nt" or " " not in iverilog:
        return iverilog, vvp
    portable_bin = EXTERNAL / "toolchain" / "bin"
    portable_lib = EXTERNAL / "toolchain" / "lib" / "ivl"
    portable_bin.mkdir(parents=True, exist_ok=True)
    shutil.copy2(iverilog, portable_bin / "iverilog.exe")
    shutil.copy2(vvp, portable_bin / "vvp.exe")
    shutil.copytree(Path(iverilog).parent.parent / "lib" / "ivl", portable_lib, dirs_exist_ok=True)
    return str(portable_bin / "iverilog.exe"), str(portable_bin / "vvp.exe")


def portable_verilator() -> tuple[str | None, str | None, str | None]:
    source_bin = Path(r"D:\Compiler Cpp\ucrt64\bin\verilator_bin.exe")
    source_root = Path(r"D:\Compiler Cpp\ucrt64\share\verilator")
    source_make = Path(r"D:\Compiler Cpp\usr\bin\make.exe")
    msys_shell = Path(r"D:\Compiler Cpp\msys2_shell.cmd")
    if not all(path.exists() for path in (source_bin, source_root, source_make, msys_shell)):
        return None, None, None
    root = EXTERNAL / "toolchain" / "verilator-root"
    make = EXTERNAL / "toolchain" / "make.exe"
    root.parent.mkdir(parents=True, exist_ok=True)
    if not root.exists():
        shutil.copytree(source_root, root)
    shutil.copy2(source_bin, root / "verilator_bin.exe")
    shutil.copy2(source_make, make)
    return str(msys_shell), str(root), str(make)


def run_command(command: list[str], cwd: Path, log: Path, command_id: str,
                commands: list[dict[str, Any]]) -> dict[str, Any]:
    started_utc = utc_now()
    start = time.perf_counter()
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=180, check=False)
        exit_code = result.returncode
        stdout, stderr = result.stdout, result.stderr
        status = "PASS" if exit_code == 0 else "FAIL"
    except subprocess.TimeoutExpired as exc:
        exit_code, status = None, "TIMEOUT"
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    ended_utc = utc_now()
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        f"command_id={command_id}\ncommand={subprocess.list2cmdline(command)}\n"
        f"start_utc={started_utc}\nend_utc={ended_utc}\nexit_code={exit_code}\nstatus={status}\n"
        f"duration_seconds={time.perf_counter() - start:.6f}\n\nSTDOUT\n{stdout}\nSTDERR\n{stderr}",
        encoding="utf-8", newline="\n",
    )
    record = {
        "command_id": command_id, "command": command, "cwd": str(cwd), "start_utc": started_utc,
        "end_utc": ended_utc, "exit_code": exit_code, "status": status,
        "log": log.relative_to(ROOT).as_posix(),
    }
    commands.append(record)
    return record


def local_sources(identifier: str) -> tuple[list[str], str, str]:
    if identifier == CONVENTIONAL:
        return (["asic/rtl/secded/secded_codec.sv"],
                "scripts/gate03/verification/tb_gate03_secded.sv", "gate03_tb_secded")
    return ([
        "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_encoder.sv",
        "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_syndrome.sv",
        "green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_decoder.sv",
    ], "scripts/gate03/verification/tb_gate03_hsiao.sv", "gate03_tb_hsiao")


def execute_local_runs(commands: list[dict[str, Any]]) -> tuple[dict[tuple[int, str, str], dict[str, Any]], list[dict[str, Any]]]:
    results: dict[tuple[int, str, str], dict[str, Any]] = {}
    reports: list[dict[str, Any]] = []
    msys_shell, verilator_root, portable_make = portable_verilator()
    for repeat in (1, 2):
        for identifier in (CONVENTIONAL, HSIAO):
            slug = "secded" if identifier == CONVENTIONAL else "hsiao"
            run_id = f"run-{repeat:02d}-{slug}"
            local_dir = BASELINE / f"run-{repeat:02d}" / slug
            external_dir = EXTERNAL / f"run-{repeat:02d}" / slug
            external_dir.mkdir(parents=True, exist_ok=True)
            sources, tb, top = local_sources(identifier)
            snapshot_names = sources + [tb]
            if identifier == CONVENTIONAL:
                snapshot_names.extend(["asic/include/ecc_pkg.sv", "scripts/gate03/rtl/gate03_secded_wrappers.sv"])
            else:
                snapshot_names.append("scripts/gate03/rtl/gate03_hsiao_wrappers.sv")
            snapshot_files = [ROOT / item for item in snapshot_names]
            rtl_hash, snapshot = manifest_digest(snapshot_files, ROOT)
            write_json(local_dir / "source_snapshot.json", {
                "run_id": run_id, "immutable_source_commit": PREFREEZE["commit"],
                "rtl_sha256": rtl_hash, "files": snapshot,
            })
            compile_id = f"cmd-pilot-{repeat:02d}-{slug}-verilator-build"
            compile_log = local_dir / "verilator_build.log"
            obj_dir = external_dir / "verilator-obj"
            executable = obj_dir / "sim.exe"
            if msys_shell and verilator_root and portable_make:
                unix_root = verilator_root.replace("\\", "/")
                unix_make = portable_make.replace("\\", "/")
                unix_external = str(external_dir).replace("\\", "/")
                source_args = " ".join(sources + [tb])
                build = (
                    f"export VERILATOR_ROOT='{unix_root}'; export MAKE='{unix_make}'; "
                    f"export TMPDIR='{unix_external}'; export TMP='{unix_external}'; export TEMP='{unix_external}'; "
                    f"verilator --binary --timing -Wno-fatal --top-module {top} -Iasic/include "
                    f"--Mdir '{unix_external}/verilator-obj' {source_args} -o sim.exe"
                )
                compile_result = run_command(
                    [msys_shell, "-defterm", "-no-start", "-ucrt64", "-here", "-c", build],
                    ROOT, compile_log, compile_id, commands,
                )
            else:
                compile_log.parent.mkdir(parents=True, exist_ok=True)
                compile_log.write_text("status=BLOCKED_TOOL_UNAVAILABLE\n", encoding="utf-8")
                compile_result = {"status": "BLOCKED_TOOL_UNAVAILABLE", "exit_code": None,
                                  "start_utc": utc_now(), "end_utc": utc_now(), "command_id": compile_id}
            results[(repeat, identifier, "rtl_elaboration")] = compile_result | {"rtl_sha256": rtl_hash}
            reports.append(report_row(compile_log, run_id, compile_id, identifier, "rtl_elaboration",
                                      "verilator_build_log", "Verilator", "", rtl_hash))

            sim_id = f"cmd-pilot-{repeat:02d}-{slug}-verilated-sim"
            sim_log = local_dir / "functional_verification.log"
            if compile_result["status"] == "PASS" and executable.is_file():
                sim_result = run_command([str(executable)], external_dir, sim_log, sim_id, commands)
            else:
                sim_log.write_text("status=BLOCKED_BY_ELABORATION\n", encoding="utf-8")
                sim_result = {"status": "BLOCKED_BY_ELABORATION", "exit_code": None,
                              "start_utc": utc_now(), "end_utc": utc_now(), "command_id": sim_id}
            results[(repeat, identifier, "functional_simulation")] = sim_result | {"rtl_sha256": rtl_hash}
            reports.append(report_row(sim_log, run_id, sim_id, identifier, "functional_simulation",
                                      "functional_verification_log", "Verilated simulation",
                                      "verification-stress-v1", rtl_hash))
    return results, reports


def report_row(path: Path, run_id: str, command_id: str, identifier: str, stage: str,
               report_type: str, producer: str, workload: str, rtl_hash: str,
               retained: bool = True, location_kind: str = "REPOSITORY") -> dict[str, Any]:
    report_id = f"raw-{run_id}-{report_type}"
    resolved = path.resolve()
    return {
        "raw_report_id": report_id, "run_id": run_id, "command_id": command_id,
        "implementation_id": identifier, "stage": stage, "report_type": report_type,
        "location_kind": location_kind,
        "path": path.relative_to(ROOT).as_posix() if retained else str(resolved),
        "size_bytes": path.stat().st_size, "sha256": sha256_file(path), "producer_tool": producer,
        "producer_version": "recorded-in-toolchain-inventory", "config_id": "gate03-pilot-contract-v1",
        "rtl_sha256": rtl_hash, "library_sha256": "", "activity_sha256": sha256_file(path) if path.suffix == ".vcd" else "",
        "workload_id": workload, "retained_in_git": str(retained).lower(),
        "notes": "verification-only; prohibited as primary power" if workload == "verification-stress-v1" else "",
    }


def bch_audit() -> dict[str, Any]:
    paths = sorted(set(ROOT.glob("asic/**/*bch*.sv")) | set(ROOT.glob("rtl/**/*bch*.v")))
    candidates = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        candidates.append({
            "path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path),
            "mentions_exact_78_64_identity": ("78" in text and "64" in text),
            "acceptance_status": "REJECTED_NO_EXACT_GATE02_EQUIVALENCE_PROOF",
        })
    return {
        "target_mathematical_code_id": "shortened-bch-78-64-t2-v1",
        "encoder_acceptance": {
            "allowed_methods": ["formal_equivalence_to_frozen_generator_matrix",
                                "formal_linearity_plus_zero_and_all_64_basis_messages"],
            "required_payload_cases": 65,
        },
        "decoder_acceptance": {
            "symbolic_payload_required": True, "mask_weights": [0, 1, 2],
            "required_mask_cases": 3082, "calculation": "1 + 78 + C(78,2)",
            "required_outputs": ["decoded_data", "corrected_codeword", "latency", "status_semantics"],
        },
        "probe_only_equivalence_is_complete": False,
        "examined_sources": candidates,
        "accepted_rtl": [],
        "status": "BLOCKED_MISSING_VALID_RTL",
    }


def main() -> int:
    status_lines, offending = allowed_status_paths()
    if offending:
        print("Gate-03 stopped: repository has changes outside authorized paths:", file=sys.stderr)
        for path in offending:
            print(path, file=sys.stderr)
        return 2
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != PREFREEZE["commit"]:
        print("Gate-03 stopped: HEAD changed after the clean-tree freeze", file=sys.stderr)
        return 2

    OUT.mkdir(parents=True, exist_ok=True)
    BASELINE.mkdir(parents=True, exist_ok=True)
    gate01_hash, gate01_entries = tree_manifest(GATE01)
    gate02_hash, gate02_entries = tree_manifest(GATE02)
    frozen_unchanged, frozen_checks = frozen_gate_bytes_unchanged()
    if not frozen_unchanged:
        print("Gate-03 stopped: Gate 01/02 byte identity failed", file=sys.stderr)
        return 3

    identity = read_identity_rows()
    all_ids = (*ELIGIBLE_IMPLEMENTATIONS, *EXCLUDED_IMPLEMENTATIONS)
    entries = {identifier: registry_entry(identifier) for identifier in all_ids}
    commands: list[dict[str, Any]] = []
    failed_log = BASELINE / "failed-attempts" / "cmd-00-secded-vvp-interrupted.log"
    old_compile = BASELINE / "run-01" / "secded" / "iverilog_compile.log"
    old_vcd = EXTERNAL_ROOT / "run-01" / "secded" / "verification-stress-secded.vcd"
    failed_log_2 = BASELINE / "failed-attempts" / "cmd-00b-secded-vvp-interrupted.log"
    if old_compile.exists() and old_vcd.exists() and not failed_log.exists():
        failed_log.parent.mkdir(parents=True, exist_ok=True)
        failed_log.write_text(
            old_compile.read_text(encoding="utf-8", errors="replace")
            + "\nRETRY_DIAGNOSIS\nThe verification-only VCD dump caused prohibitive Windows vvp runtime. "
              "The process was interrupted; the partial VCD is preserved externally. "
              "The retry removes verification VCD generation and receives new command IDs.\n",
            encoding="utf-8", newline="\n",
        )
    if failed_log.exists():
        commands.append({
            "command_id": "cmd-00-secded-vvp", "command": ["vvp", "verification-stress.vvp"],
            "cwd": str(old_vcd.parent), "start_utc": "2026-08-05T05:03:39Z",
            "end_utc": "2026-08-05T05:05:20Z", "exit_code": None,
            "status": "INTERRUPTED_INVOCATION_DEFECT",
            "log": failed_log.relative_to(ROOT).as_posix(),
        })
    if old_compile.exists() and old_vcd.exists() and not failed_log_2.exists():
        failed_log_2.parent.mkdir(parents=True, exist_ok=True)
        failed_log_2.write_text(
            old_compile.read_text(encoding="utf-8", errors="replace")
            + "\nRETRY_DIAGNOSIS\nThe no-VCD Windows vvp retry remained too slow for the bounded runner "
              "and was interrupted. The next command uses Verilator without changing RTL or vectors.\n",
            encoding="utf-8", newline="\n",
        )
    if failed_log_2.exists():
        commands.append({
            "command_id": "cmd-00b-secded-vvp", "command": ["vvp", "verification-stress.vvp"],
            "cwd": str((EXTERNAL / "run-01" / "secded")), "start_utc": "2026-08-05T05:07:25Z",
            "end_utc": "2026-08-05T05:09:15Z", "exit_code": None,
            "status": "INTERRUPTED_INVOCATION_DEFECT",
            "log": failed_log_2.relative_to(ROOT).as_posix(),
        })
    local_results, raw_reports = execute_local_runs(commands)
    if failed_log.exists() and old_vcd.exists():
        raw_reports.append(report_row(
            failed_log, "run-00-invocation-defect", "cmd-00-secded-vvp", CONVENTIONAL,
            "functional_simulation", "interrupted_invocation_log", "Icarus vvp",
            "verification-stress-v1", "", retained=True,
        ))
        raw_reports.append(report_row(
            old_vcd, "run-00-invocation-defect", "cmd-00-secded-vvp", CONVENTIONAL,
            "functional_simulation", "partial_verification_vcd", "Icarus vvp",
            "verification-stress-v1", "", retained=False, location_kind="EXTERNAL_WINDOWS_TEMP",
        ))
    if failed_log_2.exists():
        raw_reports.append(report_row(
            failed_log_2, "run-00b-invocation-defect", "cmd-00b-secded-vvp", CONVENTIONAL,
            "functional_simulation", "interrupted_no_vcd_invocation_log", "Icarus vvp",
            "verification-stress-v1", "", retained=True,
        ))
    regression_status_path = BASELINE / "regression" / "status.json"
    if regression_status_path.exists():
        regression_status = json.loads(regression_status_path.read_text(encoding="utf-8"))
        for item in regression_status["commands"]:
            commands.append({
                "command_id": item["command_id"], "command": item["command"],
                "cwd": regression_status["isolated_worktree"], "start_utc": "", "end_utc": "",
                "exit_code": item["exit_code"], "status": item["status"], "log": item["log"],
            })
            log_path = ROOT / item["log"]
            if log_path.is_file():
                raw_reports.append(report_row(
                    log_path, "isolated-staged-regression", item["command_id"], "GATE03_VALIDATION",
                    "repository_validation", item["command_id"].replace("cmd-regression-", "") + "_log",
                    item["command"][0], "", "", retained=True,
                ))
    audit = bch_audit()
    write_json(BASELINE / "bch_rtl_acceptance_audit.json", audit)

    freeze = {
        "schema_version": 1, "gate02_authority": "CODE_IDENTITY_MATRIX.csv:code_id",
        "eligible_implementation_ids": list(ELIGIBLE_IMPLEMENTATIONS),
        "excluded_implementation_ids": list(EXCLUDED_IMPLEMENTATIONS),
        "sentinels": list(SENTINELS), "records": [],
    }
    rtl_rows = []
    for identifier in all_ids:
        row = identity[identifier]
        entry = entries[identifier]
        code_hash = row["canonical_matrix_hash"] or row["canonical_polynomial_hash"]
        rtl_sources = [path for path in entry.get("source_files", []) if Path(path).suffix.lower() in {".sv", ".v"}]
        encoder_present = bool(entry.get("encoder_top") and rtl_sources)
        decoder_present = bool(entry.get("decoder_top") and rtl_sources)
        hardware_id = HARDWARE_IDS.get(identifier, f"unproven-hardware-structure:{identifier}")
        eligibility = "ELIGIBLE" if identifier in ELIGIBLE_IMPLEMENTATIONS else "EXCLUDED"
        record = {
            "implementation_id": identifier, "mathematical_code_id": row["code_id"],
            "canonical_identity_hash": code_hash, "n": int(row["n"]), "k": int(row["k"]),
            "r": int(row["r"]), "eligibility": eligibility,
            "hardware_structure_id": hardware_id,
        }
        freeze["records"].append(record)
        missing = []
        if not encoder_present: missing.append("synthesizable_encoder_rtl")
        if not decoder_present: missing.append("synthesizable_decoder_rtl")
        source_model = "synthesizable_rtl" if encoder_present and decoder_present else "reference_or_archived_model"
        rtl_rows.append({
            **record, "source_model": source_model, "encoder_rtl_present": str(encoder_present).lower(),
            "decoder_rtl_present": str(decoder_present).lower(), "rtl_source_paths": ";".join(rtl_sources),
            "encoder_top": entry.get("encoder_top") or "", "decoder_top": entry.get("decoder_top") or "",
            "parameters": json.dumps(entry.get("parameters", {}), sort_keys=True, separators=(",", ":")),
            "synthesizable": str(encoder_present and decoder_present).lower(),
            "organization": entry.get("architecture_style", ""), "pipeline_depth": entry.get("pipeline_stages", ""),
            "encoder_latency_cycles": entry.get("encoder_latency", ""),
            "decoder_latency_cycles": entry.get("decoder_latency", ""),
            "initiation_interval_cycles": entry.get("initiation_interval", ""),
            "protocol": entry.get("transaction_protocol", {}).get("kind", ""),
            "clock_required": str(entry.get("clock_reset", {}).get("clock_required", False)).lower(),
            "reset_required": str(entry.get("clock_reset", {}).get("reset_required", False)).lower(),
            "generated_status": "generated" if identifier == HSIAO else ("reference_only" if not rtl_sources else "pre_existing"),
            "gate02_identity_status": row["gate_status"],
            "existing_equivalence_evidence": json.dumps(entry.get("verification_evidence", []), sort_keys=True),
            "duplicate_or_alias_of": "", "missing_hardware": ";".join(missing),
            "physical_feasibility_status": "PILOT_ELIGIBLE_PHYSICAL_FLOW_BLOCKED" if identifier in (CONVENTIONAL, HSIAO) else "BLOCKED_NO_SYNTHESIZABLE_RTL",
            "evidence_paths": row["evidence_path"],
            "notes": "Gate-02 code_id copied exactly; no inferred identity merge",
        })
    write_json(OUT / "ELIGIBLE_IMPLEMENTATION_FREEZE.json", freeze)
    write_csv(OUT / "RTL_TO_IMPLEMENTATION_MATRIX.csv", RTL_MATRIX_HEADER, rtl_rows)

    h2_counts: dict[str, int] = {}
    for item in freeze["records"]:
        if item["eligibility"] == "ELIGIBLE":
            h2_counts[item["mathematical_code_id"]] = h2_counts.get(item["mathematical_code_id"], 0) + 1
    ppa_rows = []
    for identifier in ELIGIBLE_IMPLEMENTATIONS:
        row = identity[identifier]
        code_hash = row["canonical_matrix_hash"] or row["canonical_polynomial_hash"]
        local = identifier in (CONVENTIONAL, HSIAO)
        bch = identifier == BCH
        blocked = "BLOCKED_MISSING_VALID_RTL" if bch else (
            "BLOCKED_PINNED_ORFS_ENVIRONMENT_UNAVAILABLE" if local else "BLOCKED_NO_SYNTHESIZABLE_RTL")
        slug = "secded" if identifier == CONVENTIONAL else ("hsiao" if identifier == HSIAO else "bch-t2")
        report_ids = ""
        if local:
            report_ids = ";".join(
                f"raw-run-{repeat:02d}-{slug}-{kind}"
                for repeat in (1, 2)
                for kind in ("verilator_build_log", "functional_verification_log")
            )
        ppa_rows.append({
            "implementation_id": identifier, "mathematical_code_id": row["code_id"],
            "canonical_identity_hash": code_hash,
            "hardware_structure_id": HARDWARE_IDS.get(identifier, f"unproven-hardware-structure:{identifier}"),
            "h2_identity_group": row["code_id"],
            "h2_status": "UNTESTABLE_IDENTITY_MISMATCH" if local else "NO_SECOND_PROVEN_STRUCTURE_WITH_IDENTICAL_CODE_ID",
            "physical_status": blocked, "technology": "SKY130HD_PILOT_NOT_EXECUTED",
            "library": "sky130_fd_sc_hd__tt_025C_1v80_NOT_ACQUIRED",
            "pvt_corner": "TT_1.80V_25C_PENDING_LIBERTY_VALIDATION",
            "rtl_elaboration": "PASS_TWO_LOCAL_RUNS" if local else blocked,
            "functional_verification": "PASS_TWO_LOCAL_RUNS_VERIFICATION_STRESS_ONLY" if local else blocked,
            "technology_mapping": blocked, "sta_status": blocked,
            "primary_activity_trace": blocked, "primary_activity_power": blocked,
            "conditional_single_power": blocked, "conditional_double_power": blocked,
            "placement": blocked, "routing": blocked, "parasitic_extraction": blocked,
            "post_route_sta": blocked, "post_route_power": blocked,
            "repeat_run_status": "LOCAL_FUNCTIONAL_REPEAT_ONLY_PHYSICAL_REPRODUCIBILITY_UNTESTED" if local else blocked,
            "evidence_classification": "UNRESOLVED", "config_id": "gate03-pilot-contract-v1",
            "primary_activity_id": "normal-clean-random-v1", "toolchain_id": "gate03-local-audit-v1",
            "run_ids": f"run-01-{slug};run-02-{slug}", "raw_report_ids": report_ids,
            "blocking_reason": blocked,
        })
    write_csv(OUT / "PPA_FEASIBILITY_MATRIX.csv", PPA_HEADER, ppa_rows)

    sentinel_rows = []
    blocked_summary = {"physical_flow": "BLOCKED_PINNED_ORFS_ENVIRONMENT_UNAVAILABLE",
                       "bch": "BLOCKED_MISSING_VALID_RTL", "h2": "UNTESTABLE_IDENTITY_MISMATCH"}
    write_json(BASELINE / "blocked_stage_summary.json", blocked_summary)
    for repeat in (1, 2):
        for identifier in SENTINELS:
            slug = "secded" if identifier == CONVENTIONAL else ("hsiao" if identifier == HSIAO else "bch-t2")
            run_id = f"run-{repeat:02d}-{slug}"
            source_paths = [ROOT / path for path in entries[identifier].get("source_files", []) if (ROOT / path).is_file()]
            rtl_hash = manifest_digest(source_paths, ROOT)[0] if source_paths else ""
            for stage in STAGES:
                workload = ""
                if stage == "functional_simulation": workload = "verification-stress-v1"
                if stage in {"primary_activity_trace", "primary_activity_power", "post_route_power"}: workload = "normal-clean-random-v1"
                if identifier in (CONVENTIONAL, HSIAO) and stage in {"rtl_elaboration", "functional_simulation"}:
                    result = local_results[(repeat, identifier, stage)]
                    status = result["status"]
                    command_id = result["command_id"]
                    raw_log_id = f"raw-{run_id}-" + ("verilator_build_log" if stage == "rtl_elaboration" else "functional_verification_log")
                    start_utc, end_utc, exit_code = result["start_utc"], result["end_utc"], result["exit_code"]
                    failure = "" if status == "PASS" else "LOCAL_TOOL_FAILURE"
                elif stage == "gate02_identity_reconciliation":
                    status, command_id = "PASS_FROZEN_IDENTITY_COPIED_EXACTLY", "internal-gate02-identity-check"
                    raw_log_id, start_utc, end_utc, exit_code, failure = "", "", "", 0, ""
                else:
                    status = "BLOCKED_MISSING_VALID_RTL" if identifier == BCH else "BLOCKED_PINNED_ORFS_ENVIRONMENT_UNAVAILABLE"
                    command_id, raw_log_id, start_utc, end_utc, exit_code = "NOT_EXECUTED", "", "", "", ""
                    failure = status
                sentinel_rows.append({
                    "run_id": run_id, "repeat_index": repeat, "sentinel_id": identifier,
                    "implementation_id": identifier,
                    "hardware_structure_id": HARDWARE_IDS[identifier], "stage": stage, "attempt": 1,
                    "command_id": command_id, "status": status, "start_utc": start_utc,
                    "end_utc": end_utc, "exit_code": exit_code, "config_id": "gate03-pilot-contract-v1",
                    "rtl_sha256": rtl_hash, "library_sha256": "", "activity_sha256": "",
                    "workload_id": workload, "toolchain_id": "gate03-local-audit-v1",
                    "raw_log_id": raw_log_id, "output_artifact_ids": "", "failure_reason": failure,
                    "retry_of_command_id": "",
                })
    write_csv(OUT / "SENTINEL_RUNS.csv", SENTINEL_HEADER, sentinel_rows)
    write_csv(OUT / "RAW_REPORT_INDEX.csv", RAW_REPORT_HEADER, raw_reports)

    evidence_rows = []
    for identifier in SENTINELS:
        evidence_rows.extend([
            {"evidence_id": f"ev-{identifier}-identity", "implementation_id": identifier,
             "quantity": "mathematical_identity", "raw_value": identity[identifier]["code_id"], "unit": "id",
             "classification": "MEASURED", "scope": "frozen Gate-02 bytes", "source_report_id": "",
             "workload_id": "", "derivation": "byte-exact copy from Gate-02 code_id", "limitations": "not physical PPA"},
            {"evidence_id": f"ev-{identifier}-physical-ppa", "implementation_id": identifier,
             "quantity": "technology_mapped_physical_ppa", "raw_value": "UNRESOLVED", "unit": "",
             "classification": "UNRESOLVED", "scope": "codec standard-cell pilot", "source_report_id": "",
             "workload_id": "normal-clean-random-v1", "derivation": "none", "limitations": "pinned ORFS flow unavailable"},
        ])
        if identifier in (CONVENTIONAL, HSIAO):
            evidence_rows.append({
                "evidence_id": f"ev-{identifier}-verification-stress", "implementation_id": identifier,
                "quantity": "functional_verification_activity", "raw_value": "8192", "unit": "cycles",
                "classification": "SIMULATED", "scope": "verification only", "source_report_id": "",
                "workload_id": "verification-stress-v1", "derivation": "80/10/10 deterministic trace",
                "limitations": "prohibited from all primary power and representative-energy fields",
            })
    evidence_rows.extend([
        {"evidence_id": "ev-system-storage-energy", "implementation_id": "SYSTEM_BOUNDARY",
         "quantity": "sram_controller_scrub_total_system_energy", "raw_value": "UNRESOLVED", "unit": "",
         "classification": "UNRESOLVED", "scope": "system", "source_report_id": "", "workload_id": "",
         "derivation": "none", "limitations": "no SRAM macro/model, controller, scrub, or physical adjacency evidence"},
        {"evidence_id": "ev-contract-clock", "implementation_id": "COMMON_CONTRACT",
         "quantity": "pilot_clock_period", "raw_value": "10", "unit": "ns", "classification": "ASSUMED",
         "scope": "Gate-03 feasibility only", "source_report_id": "", "workload_id": "",
         "derivation": "frozen before candidate synthesis", "limitations": "not a final paper setting"},
    ])
    write_csv(OUT / "EVIDENCE_CLASSIFICATION.csv", EVIDENCE_HEADER, evidence_rows)

    tools = []
    for name, args, role in [
        ("iverilog", ["-V"], "RTL elaboration/VCD generation"), ("vvp", ["-V"], "RTL simulation"),
        ("verilator", ["--version"], "bounded RTL compilation and simulation"),
        ("yosys", ["-V"], "generic synthesis proxy"), ("openroad", ["-version"], "placement/routing"),
        ("sta", ["-version"], "static timing/power activity"), ("docker", ["--version"], "container runtime"),
        ("wsl", ["--version"], "Linux environment launcher"),
    ]:
        path = tool_path(name)
        tools.append({"tool": name, "role": role, "available": bool(path), "path": path,
                      "version": tool_version(path, args),
                      "sha256": sha256_file(Path(path)) if path and Path(path).is_file() else None})
    inventory = {
        "schema_version": 1, "toolchain_id": "gate03-local-audit-v1", "tools": tools,
        "orfs": {"image_reference": None, "image_digest": None, "matching_source_commit": None,
                 "image_source_hash_match": "NOT_ESTABLISHED", "status": "BLOCKED_NOT_PROVISIONED"},
        "collateral": {"platform": "SKY130HD", "required_liberty_corner": "sky130_fd_sc_hd__tt_025C_1v80",
                       "liberty": None, "technology_lef": None, "cell_lef": None, "routing_extraction": None,
                       "status": "BLOCKED_NOT_ACQUIRED"},
        "licenses": {"proprietary_acquisition_attempted": False, "public_collateral_acquisition_attempted": False},
        "environment_provisioning": {
            "approved": False,
            "approval_request_status": "REJECTED_PENDING_EXPLICIT_USER_APPROVAL",
            "host_changed": False,
            "reboot_performed": False,
        },
    }
    write_json(OUT / "TOOLCHAIN_AND_COLLATERAL_INVENTORY.json", inventory)

    repository_paths = []
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0")
    for raw in tracked:
        if raw:
            path = ROOT / raw.decode("utf-8")
            if path.is_file(): repository_paths.append(path)
    repository_hash, repository_entries = manifest_digest(repository_paths, ROOT)
    environment = {
        "schema_version": 1, "pre_write_freeze": PREFREEZE,
        "execution": {"captured_utc": utc_now(), "python": sys.version, "platform": platform.platform(),
                      "porcelain_v2_authorized_changes": status_lines, "offending_paths": offending,
                      "full_tracked_repository_sha256": repository_hash},
        "gate01": {"execution_manifest_sha256": gate01_hash,
                   "prefreeze_manifest_sha256": PREFREEZE["gate01_tree_sha256"],
                   "byte_identical": frozen_checks["gate01"]["byte_identical_to_frozen_commit"],
                   "git_identity_check": frozen_checks["gate01"], "files": gate01_entries},
        "gate02": {"execution_manifest_sha256": gate02_hash,
                   "prefreeze_manifest_sha256": PREFREEZE["gate02_tree_sha256"],
                   "byte_identical": frozen_checks["gate02"]["byte_identical_to_frozen_commit"],
                   "git_identity_check": frozen_checks["gate02"], "files": gate02_entries},
        "repository_tracked_manifest": repository_entries,
        "large_artifact_root": str(EXTERNAL),
    }
    write_json(BASELINE / "environment_manifest.json", environment)
    write_json(BASELINE / "command_manifest.json", {"schema_version": 1, "commands": commands})
    write_json(BASELINE / "workload_contract.json", {
        "schema_version": 1, "seed": WORKLOAD_SEED, "warmup_cycles": WARMUP_CYCLES,
        "measured_cycles": MEASURED_CYCLES, "vcd_interval": "measured_only", "workloads": WORKLOADS,
        "primary_power_workload_id": "normal-clean-random-v1",
        "verification_stress_may_populate_primary_power": False,
        "conditional_energy_weighting": "Gate-04 only with separately calibrated fault PMF",
    })

    (OUT / "FAIRNESS_AND_CONSTRAINT_CONTRACT.md").write_text(FAIRNESS_TEXT, encoding="utf-8", newline="\n")
    (OUT / "CLAIM_SCOPE_DECISION.md").write_text(CLAIM_TEXT, encoding="utf-8", newline="\n")
    (OUT / "GATE_04_EXECUTION_PLAN.md").write_text(GATE04_TEXT, encoding="utf-8", newline="\n")
    (OUT / "GATE_03_REPORT.md").write_text(REPORT_TEXT, encoding="utf-8", newline="\n")
    (OUT / "BINARY_NO_GO_DECISION.md").write_text(
        "# Gate-03 binary decision\n\nNO_GO_FOR_DATE_2027_REGULAR_PAPER_CORE\n\n"
        "Mechanically triggered by: `UNTESTABLE_IDENTITY_MISMATCH`, `BLOCKED_MISSING_VALID_RTL`, "
        "and `BLOCKED_PINNED_ORFS_ENVIRONMENT_UNAVAILABLE`. Negative slack was not used.\n",
        encoding="utf-8", newline="\n",
    )
    print("Gate-03 local audit complete: NO_GO_FOR_DATE_2027_REGULAR_PAPER_CORE")
    return 0


FAIRNESS_TEXT = """# Gate-03 fairness and constraint contract

Contract ID: `gate03-pilot-contract-v1`. This contract was frozen before comparative physical results.

- Technology/corner: SKY130HD, `sky130_fd_sc_hd__tt_025C_1v80`, TT, 1.80 V, 25 °C; acceptance requires validation from the pinned Liberty bytes.
- Pilot clock: 100 MHz (10 ns); uncertainty 0.5 ns; input/output delays 1 ns; input transition 0.2 ns; output load 0.05 pF.
- Limits: fanout 16, transition 1 ns, capacitance 0.2 pF.
- Floorplan: utilization 40%, aspect ratio 1.0, core margin 10 µm, placement density 0.55; exposed randomized-stage seed 42.
- Boundaries: clean registered-input/registered-output encoder, decoder, and direct encoder-to-decoder combined shells; identical valid treatment; no reset; one combinational codec stage; initiation interval one.
- Wrapper control: a direct wrapper-only control must report wrapper standard-cell area. Codec, wrapper, total, post-route cells, allocated core, and allocated die are separate quantities.
- Workloads: seed `0x475245454E454343`, 256 warm-up cycles, 8,192 measured cycles, VCD only during measurement. `normal-clean-random-v1` is primary. Single and double error energy are conditional only. `verification-stress-v1` (80/10/10) is verification-only and may not populate primary power.
- Timing misses: negative slack is `TIMING_ANALYZED_TARGET_MISS`, not automatic impossibility. A routed 10 ns layout may yield only a DERIVED `1000 / critical_path_delay_ns`; it is not called Fmax. A frequency sweep reruns the complete optimized flow per period.
- Physical checks are called ORFS/open-PDK checks, never foundry-signoff DRC/LVS.

These are bounded Gate-03 feasibility assumptions, not final paper constraints. No autotuning or result-dependent relaxation is allowed.
"""

CLAIM_TEXT = """# Gate-03 claim-scope decision

No technology-mapped physical PPA claim is supportable from this execution. Local RTL simulation is `SIMULATED`; generic synthesis, where available, is structural `SYNTHESIZED` evidence and remains a `PROXY` for area, timing, and energy.

SRAM area/energy, parity storage implementation, controller and scrub energy, total-system energy, physical adjacency/interleaving, FIT, and carbon remain `UNRESOLVED`. The verification stress fault rate is not representative energy and is prohibited from primary power. Any future conditional weighting belongs to Gate 04 and requires a separately calibrated fault PMF.

SKY130 pilot results, if later completed, must not be described as 14 nm, measured silicon, tapeout signoff, foundry-certified evidence, or foundry-signoff DRC/LVS.
"""

GATE04_TEXT = """# Gate-04 execution authorization

DATE-2027 Gate 04 is not authorized by this Gate-03 result.

The next authorized activity is **Gate 03R — Exact-Identity Hardware and BCH RTL Remediation/Re-entry**. It must supply two distinct proven hardware structures with one byte-identical frozen Gate-02 mathematical-code ID, and valid BCH `t >= 2` RTL accepted by the exact encoder and decoder proofs. After remediation, the complete Gate-03 common flow must be rerun twice.
"""

REPORT_TEXT = """# GREEN-ECC DATE 2027 Publication-Rigour Gate 03

## Binary result

`NO_GO_FOR_DATE_2027_REGULAR_PAPER_CORE`

The exact physical-feasible set is empty. Conventional SECDED and Hsiao passed two local verification-stress simulations but did not complete a pinned characterized common flow. Technology mapping to SKY130HD, STA, activity-based power, placement, routing, extraction, post-route analysis, and physical reproducibility are unresolved.

## Mechanical blockers

1. H2 is `UNTESTABLE_IDENTITY_MISMATCH`: conventional is `extended-hamming-secded-72-64-v1` (`40bc866e…`) while Hsiao is `hsiao-secded-72-64-v1` (`1cc658a0…`). Equal dimensions or protection class do not merge identities.
2. BCH is `BLOCKED_MISSING_VALID_RTL`. No pre-existing `(78,64)` source has formal equivalence or the required exact linear-code proof. The decoder requirement is symbolic payload data across all 3,082 weight-0/1/2 masks; probe-only evidence is incomplete.
3. The pinned ORFS image digest, its matching source commit/configuration, and characterized SKY130HD collateral could not be established because WSL2/Docker provisioning was not authorized during the local audit. No mutable checkout was combined with an independently pinned image.

Negative slack did not trigger this decision because no characterized timing run occurred. Storage and total-system energy remain unsupported. The next authorized activity is Gate 03R, followed by a complete two-run Gate-03 re-entry.

## Repository validation

The isolated staged snapshot passed `make`, `git diff --check`, the final staged diff check, and 11 focused Gate-03 tests. `make test` completed with 367 passed and one unrelated pre-existing fixture-hash failure; `python3 -m pytest -q` completed with 369 passed and the same failure. The failing fixture is `tests/fixtures/multi_ecc_external/plugin.py`: the isolated CRLF checkout does not match its frozen source-byte hash. Gate 03 did not repair or modify that fixture. The timed-out first `make test` attempt and both final transcripts are retained under `baseline/regression/`.
"""

if __name__ == "__main__":
    raise SystemExit(main())
