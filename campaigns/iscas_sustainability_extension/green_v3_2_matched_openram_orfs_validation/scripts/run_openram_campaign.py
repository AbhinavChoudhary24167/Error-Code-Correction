#!/usr/bin/env python3
"""Run the pinned OpenRAM target in a fresh, isolated WSL evidence namespace.

The historical OpenRAM source, virtual environment, and PDK are mounted
read-only.  Only the new campaign namespace is writable.  A bounded timeout is
part of the experimental contract because the historical top-level Magic DRC
stage required more than fourteen hours on this host.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


IMAGE = "vlsida/openram-ubuntu@sha256:90ecae634f99fa9055a32e32f9d6af1acc9942b974916f114330e7b5b4b29f7c"
OPENRAM_COMMIT = "b6a6f12642df6b84facc24a77f9a6f67a0d62dab"
HISTORICAL_ROOT = Path("/var/lib/green-ecc-iscas-sustainability/gate3_openram_attempt02")
DEFAULT_EVIDENCE_ROOT = Path("/var/lib/green-ecc-v32-matched-openram-orfs-validation/openram_fresh")
CONTAINER_NAME = "green_v32_openram_fresh_20260908"
TARGET = "sky130_sram_1rw_72x256_green_v32_matched"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_role(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".gds"):
        return "gds"
    if name.endswith(".lef"):
        return "lef"
    if name.endswith(".lib"):
        return "liberty"
    if name.endswith((".sp", ".lvs")):
        return "spice"
    if name.endswith(".v"):
        return "verilog"
    if name.endswith(".html"):
        return "datasheet_html"
    if name.endswith(".py"):
        return "extended_config"
    if name.endswith(".log"):
        return "openram_log"
    return "supporting_output"


def inventory(evidence_root: Path) -> list[dict[str, Any]]:
    output = evidence_root / "output" / TARGET
    records: list[dict[str, Any]] = []
    if output.is_dir():
        for path in sorted(item for item in output.rglob("*") if item.is_file()):
            records.append({
                "role": artifact_role(path),
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    work = evidence_root / "work" / "openram_tmp_256x72"
    for suffix, role in ((".drc.out", "magic_drc_report"), (".lvs.report", "netgen_lvs_report"),
                         (".lvs.out", "netgen_lvs_output"), (".lvs.json", "netgen_lvs_json")):
        path = work / f"{TARGET}{suffix}"
        if path.is_file():
            records.append({"role": role, "path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)})
    return records


def last_int(pattern: str, text: str) -> int | None:
    matches = re.findall(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    return int(matches[-1]) if matches else None


def classify(exit_code: int | None, timed_out: bool, text: str, artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    roles = {item["role"] for item in artifacts}
    drc_errors = last_int(r"DRC Errors[^\n]*?([0-9]+)\s*$", text)
    lvs_mismatch = bool(re.search(r"LVS mismatch", text, flags=re.IGNORECASE))
    bl_failure = bool(re.search(r"Could not find bl net", text, flags=re.IGNORECASE))
    permission_failure = bool(re.search(r"PermissionError|Permission denied", text, flags=re.IGNORECASE))
    if drc_errors == 0:
        drc_state = "DRC_CLEAN"
    elif drc_errors is not None:
        drc_state = "DRC_VIOLATIONS_SCOPE_UNRESOLVED_NOT_WAIVED"
    elif timed_out:
        drc_state = "DRC_NOT_COMPLETED_BEFORE_RUNTIME_CUTOFF"
    else:
        drc_state = "DRC_UNAVAILABLE"
    if lvs_mismatch:
        lvs_state = "LVS_FAIL"
    elif re.search(r"LVS.*(?:match|correct)", text, flags=re.IGNORECASE):
        lvs_state = "LVS_PASS"
    elif timed_out:
        lvs_state = "LVS_NOT_COMPLETED_BEFORE_RUNTIME_CUTOFF"
    else:
        lvs_state = "LVS_UNAVAILABLE"
    required = {"gds", "lef", "liberty", "spice", "verilog"}
    pass_state = exit_code == 0 and required.issubset(roles) and drc_state == "DRC_CLEAN" and lvs_state == "LVS_PASS"
    if pass_state:
        classification = "FRESH_OPENRAM_GENERATION_AND_VERIFICATION_PASS"
        status = "PASS"
    elif timed_out:
        classification = "FRESH_OPENRAM_REGENERATION_PARTIAL_RUNTIME_CUTOFF"
        status = "TIMEOUT"
    elif drc_errors and lvs_mismatch and bl_failure:
        classification = "FRESH_OPENRAM_DRC_LVS_AND_CHARACTERIZATION_FAILURE"
        status = "FAIL"
    elif permission_failure:
        classification = "FRESH_OPENRAM_ENVIRONMENT_FILESYSTEM_PERMISSION_FAILURE"
        status = "FAIL"
    elif exit_code not in (0, None):
        classification = "FRESH_OPENRAM_TOOL_OR_CONFIGURATION_FAILURE"
        status = "FAIL"
    else:
        classification = "FRESH_OPENRAM_INCOMPLETE_OUTPUT"
        status = "FAIL"
    domains = []
    if drc_errors:
        domains.append("DRC")
    if lvs_mismatch:
        domains.append("LVS")
    if bl_failure:
        domains.append("CHARACTERIZATION")
    if timed_out:
        domains.append("CAMPAIGN_RUNTIME_CUTOFF")
    if permission_failure:
        domains.append("ENVIRONMENT_FILESYSTEM_PERMISSION")
    return {
        "status": status,
        "classification": classification,
        "drc_state": drc_state,
        "drc_error_count": drc_errors,
        "drc_scope_note": "No array-only waiver is inferred without a complete cell/layer classification.",
        "lvs_state": lvs_state,
        "characterization_state": "FAIL_MISSING_BL_TIMING_PATH" if bl_failure else ("NOT_COMPLETED" if timed_out else "UNKNOWN"),
        "failure_domains": domains,
    }


def finalize_record(campaign: Path, evidence_root: Path, result: dict[str, Any]) -> dict[str, Any]:
    """Refresh partial-artifact evidence after natural completion or a cutoff."""
    driver_log = evidence_root / "logs" / "openram_256x72_fresh.log"
    compiler_log = evidence_root / "output" / TARGET / f"{TARGET}.log"
    text = driver_log.read_text(encoding="utf-8", errors="replace") if driver_log.is_file() else ""
    if compiler_log.is_file():
        text += "\n" + compiler_log.read_text(encoding="utf-8", errors="replace")
    artifacts = inventory(evidence_root)
    result["fresh_artifacts"] = artifacts
    result.update(classify(result.get("process_exit_code"), bool(result.get("timed_out")), text, artifacts))
    sizes = re.findall(r"Size:\s*([0-9.]+)\s*x\s*([0-9.]+)", text)
    if sizes:
        width, height = (float(value) for value in sizes[0])
        result["macro_geometry"] = {
            "width_um": width,
            "height_um": height,
            "area_um2": width * height,
            "source": "OpenRAM hierarchy_layout get_bbox log record",
        }
    compact_dir = campaign / "logs" / "openram"
    compact_dir.mkdir(parents=True, exist_ok=True)
    for source, destination in (
        (driver_log, compact_dir / "openram_256x72_fresh_driver.log.gz"),
        (compiler_log, compact_dir / "openram_256x72_fresh_compiler.log.gz"),
    ):
        if not source.is_file():
            continue
        with source.open("rb") as input_stream, destination.open("wb") as compressed:
            with gzip.GzipFile(filename="", mode="wb", compresslevel=9, fileobj=compressed, mtime=0) as output_stream:
                shutil.copyfileobj(input_stream, output_stream)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    parser.add_argument("--timeout-seconds", type=int, default=10800,
                        help="Transparent wall-clock cutoff; default is three hours.")
    parser.add_argument("--reuse-completed", action="store_true",
                        help="Return the existing committed run record instead of starting another run.")
    args = parser.parse_args()
    repo = args.repo.resolve()
    campaign = repo / "campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation"
    record_path = campaign / "openram" / "OPENRAM_FRESH_RUN.json"
    if args.reuse_completed and record_path.is_file():
        existing = json.loads(record_path.read_text(encoding="utf-8"))
        root = Path(existing["external_evidence_root"])
        existing = finalize_record(campaign, root, existing)
        record_path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print(f"OPENRAM_FRESH_RUN_REFRESHED status={existing['status']} classification={existing['classification']}")
        return 0
    evidence_root = args.evidence_root.resolve()
    if evidence_root.exists() and any(evidence_root.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty fresh evidence root: {evidence_root}")
    for path in (evidence_root / "output", evidence_root / "work", evidence_root / "logs"):
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(0o777)
    config = campaign / "configs" / "openram_256x72_config.py"
    required_inputs = [
        HISTORICAL_ROOT / "source" / "OpenRAM" / "sram_compiler.py",
        HISTORICAL_ROOT / "venv" / "bin" / "activate",
        HISTORICAL_ROOT / "pdk" / "sky130A" / "libs.tech" / "magic" / "sky130A.tech",
        config,
    ]
    missing = [str(path) for path in required_inputs if not path.is_file()]
    if missing:
        raise SystemExit("Missing pinned OpenRAM input(s): " + ", ".join(missing))

    shell_command = (
        "set -euo pipefail; . /attempt/venv/bin/activate; "
        "export OPENRAM_HOME=/attempt/source/OpenRAM/compiler; "
        "export OPENRAM_TECH=/attempt/source/OpenRAM/technology; "
        "export PYTHONPATH=/attempt/source/OpenRAM/compiler:/attempt/source/OpenRAM/technology/sky130:/attempt/source/OpenRAM/technology/sky130/custom; "
        "export PDK_ROOT=/attempt/pdk; export VOLARE_HOME=/attempt/pdk/volare; "
        "export SPICE_MODEL_DIR=/attempt/pdk/sky130A/libs.tech/ngspice; "
        "export OPENRAM_TMP=/fresh/work/openram_tmp_256x72; "
        "python3 sram_compiler.py -v /fresh/config/openram_256x72_config.py"
    )
    command = [
        "docker", "run", "--rm", "--name", CONTAINER_NAME, "--platform", "linux/amd64",
        "--volume", f"{HISTORICAL_ROOT / 'source' / 'OpenRAM'}:/attempt/source/OpenRAM:ro",
        "--volume", f"{HISTORICAL_ROOT / 'venv'}:/attempt/venv:ro",
        "--volume", f"{HISTORICAL_ROOT / 'pdk'}:/attempt/pdk:ro",
        "--volume", f"{config}:/fresh/config/openram_256x72_config.py:ro",
        "--volume", f"{evidence_root}:/fresh",
        "--workdir", "/attempt/source/OpenRAM", "--entrypoint", "bash", IMAGE, "-lc", shell_command,
    ]
    log_path = evidence_root / "logs" / "openram_256x72_fresh.log"
    start = utc_now()
    timed_out = False
    exit_code: int | None = None
    with log_path.open("wb") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            exit_code = process.wait(timeout=args.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], stdout=log, stderr=subprocess.STDOUT, check=False)
            try:
                exit_code = process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                exit_code = process.wait()
    end = utc_now()
    result = {
        "schema_version": 1,
        "fresh_execution": True,
        "start_time_utc": start,
        "end_time_utc": end,
        "timeout_seconds": args.timeout_seconds,
        "timed_out": timed_out,
        "process_exit_code": exit_code,
        "external_evidence_root": str(evidence_root),
        "command": command,
        "container_image": IMAGE,
        "openram_commit": OPENRAM_COMMIT,
        "configuration": {
            "path": config.relative_to(repo).as_posix(),
            "sha256": sha256(config),
            "word_size": 72,
            "num_words": 256,
            "num_banks": 1,
            "num_rw_ports": 1,
            "words_per_row": 2,
            "process_corner": "TT",
            "voltage_v": 1.8,
            "temperature_c": 25,
        },
        "log": {"path": str(log_path), "bytes": log_path.stat().st_size, "sha256": sha256(log_path)},
        "fresh_artifacts": [],
    }
    result = finalize_record(campaign, evidence_root, result)
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"OPENRAM_FRESH_RUN_COMPLETE status={result['status']} classification={result['classification']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
