#!/usr/bin/env python3
"""Run fresh RTL mask regressions and SRAM-model integration smoke tests."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


CAMPAIGN_REL = Path("campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation")
MACRO_REL = Path(
    "campaigns/iscas_sustainability_extension/memory_compiler/"
    "gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def run_one(command: list[str], cwd: Path, log_path: Path) -> int:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    text = completed.stdout + completed.stderr
    log_path.write_text(text, encoding="utf-8", newline="\n")
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    repo = args.repo.resolve()
    campaign = repo / CAMPAIGN_REL
    logs = campaign / "logs/functional"
    work = campaign / "logs/functional_work"
    logs.mkdir(parents=True, exist_ok=True)
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    iverilog = shutil.which("iverilog")
    vvp = shutil.which("vvp")
    if not iverilog or not vvp:
        raise SystemExit("iverilog and vvp are required for fresh RTL validation")

    common_memory = [
        MACRO_REL / "source_checkout/sram22_256x64m4w8/sram22_256x64m4w8.v",
        MACRO_REL / "source_checkout/sram22_256x8m8w1/sram22_256x8m8w1.v",
        CAMPAIGN_REL / "validation/rtl/matched_memory_tops.sv",
        CAMPAIGN_REL / "validation/tb/tb_memory_smoke.sv",
    ]
    records = [
        {
            "architecture_id": "U0",
            "define": "TEST_U0",
            "sources": [],
            "codec_tb": None,
            "declared_checks": {"memory_round_trips": 4},
            "scope_limit": "Four deterministic no-error SRAM-model round trips; no protection capability is claimed for U0.",
            "classification_on_pass": "REGRESSION_VALIDATED",
        },
        {
            "architecture_id": "SECDED",
            "define": "TEST_SECDED",
            "sources": [Path("scripts/gate03r/rtl/secded_characterization_tops.sv")],
            "codec_tb": CAMPAIGN_REL / "validation/tb/tb_secded_exhaustive_masks.sv",
            "codec_top": "tb_secded_exhaustive_masks",
            "declared_checks": {"payloads": 4, "single_masks": 288, "double_masks": 10224, "memory_round_trips": 4},
            "scope_limit": "All weight-1 correction and weight-2 detection masks are enumerated over four deterministic payloads; frozen exact evidence supplies the unrestricted linear-code result.",
            "classification_on_pass": "REGRESSION_VALIDATED",
        },
        {
            "architecture_id": "HSIAO_SECDED",
            "define": "TEST_HSIAO",
            "sources": [
                Path("green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_encoder.sv"),
                Path("green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_syndrome.sv"),
                Path("green_ecc_physical_simulation/rtl/hsiao_secded_72_64/hsiao_secded_72_64_v1_decoder.sv"),
            ],
            "codec_tb": CAMPAIGN_REL / "validation/tb/tb_hsiao_exhaustive_masks.sv",
            "codec_top": "tb_hsiao_exhaustive_masks",
            "declared_checks": {"payloads": 4, "single_masks": 288, "double_masks": 10224, "memory_round_trips": 4},
            "scope_limit": "All weight-1 correction and weight-2 detection masks are enumerated over four deterministic payloads; this fresh run is not relabelled as an unrestricted proof.",
            "classification_on_pass": "REGRESSION_VALIDATED",
        },
        {
            "architecture_id": "SEC_DAEC",
            "define": "TEST_SECDAEC",
            "sources": [
                Path("asic/include/ecc_pkg.sv"),
                Path("asic/rtl/secded/secded_codec.sv"),
                Path("asic/rtl/secdaec/secdaec_codec.sv"),
            ],
            "codec_tb": CAMPAIGN_REL / "validation/tb/tb_secdaec_supported_masks.sv",
            "codec_top": "tb_secdaec_supported_masks",
            "declared_checks": {"payloads": 4, "single_masks": 288, "adjacent_double_masks": 252, "memory_round_trips": 4},
            "scope_limit": "The declared data-adjacent pair class is tested over four payloads and contains a preserved counterexample; the candidate is excluded.",
            "classification_on_pass": "REGRESSION_VALIDATED",
        },
        {
            "architecture_id": "BCH_78_64_T2",
            "define": "TEST_BCH",
            "sources": [Path("asic/rtl/bch/bch_78_64_t2_v1.sv")],
            "codec_tb": CAMPAIGN_REL / "validation/tb/tb_bch_t2_exhaustive_masks.sv",
            "codec_top": "tb_bch_t2_exhaustive_masks",
            "declared_checks": {"payloads": 4, "single_masks": 312, "double_masks": 12012, "memory_round_trips": 4},
            "scope_limit": "All declared weight-1/2 correction masks are enumerated over four payloads; weight-3 behavior is outside the correction guarantee and remains inherited observation-only evidence.",
            "classification_on_pass": "REGRESSION_VALIDATED",
        },
    ]

    all_pass = True
    pass_count = 0
    for record in records:
        arch = record["architecture_id"]
        source_paths = [repo / path for path in record["sources"]]
        commands: list[list[str]] = []
        log_paths: list[Path] = []
        statuses: list[int] = []

        if record["codec_tb"] is not None:
            codec_exe = work / f"{arch.lower()}_codec.vvp"
            compile_log = logs / f"{arch.lower()}_codec_compile.log"
            run_log = logs / f"{arch.lower()}_codec_run.log"
            compile_command = [
                iverilog, "-g2012", "-Wall", "-I", str(repo / "asic/include"),
                "-s", str(record["codec_top"]), "-o", str(codec_exe),
                *[str(path) for path in source_paths], str(repo / record["codec_tb"]),
            ]
            commands.append(compile_command)
            status = run_one(compile_command, repo, compile_log)
            statuses.append(status)
            log_paths.append(compile_log)
            if status == 0:
                run_command = [vvp, str(codec_exe)]
                commands.append(run_command)
                statuses.append(run_one(run_command, repo, run_log))
                log_paths.append(run_log)

        memory_exe = work / f"{arch.lower()}_memory.vvp"
        memory_compile_log = logs / f"{arch.lower()}_memory_compile.log"
        memory_run_log = logs / f"{arch.lower()}_memory_run.log"
        memory_sources = [repo / path for path in [*record["sources"], *common_memory]]
        memory_command = [
            iverilog, "-g2012", "-Wall", "-I", str(repo / "asic/include"),
            f"-D{record['define']}", "-s", "tb_memory_smoke", "-o", str(memory_exe),
            *[str(path) for path in memory_sources],
        ]
        commands.append(memory_command)
        status = run_one(memory_command, repo, memory_compile_log)
        statuses.append(status)
        log_paths.append(memory_compile_log)
        if status == 0:
            memory_run_command = [vvp, str(memory_exe)]
            commands.append(memory_run_command)
            statuses.append(run_one(memory_run_command, repo, memory_run_log))
            log_paths.append(memory_run_log)

        passed = all(status == 0 for status in statuses)
        all_pass = all_pass and passed
        pass_count += int(passed)
        source_hashes = {path.relative_to(repo).as_posix(): sha256(path) for path in source_paths}
        source_hashes[(CAMPAIGN_REL / "validation/rtl/matched_memory_tops.sv").as_posix()] = sha256(
            repo / CAMPAIGN_REL / "validation/rtl/matched_memory_tops.sv"
        )
        payload = {
            "schema_version": 1,
            "architecture_id": arch,
            "status": record["classification_on_pass"] if passed else "FAILED",
            "fresh_execution": True,
            "tool": {"iverilog": subprocess.check_output([iverilog, "-V"], text=True, stderr=subprocess.STDOUT).splitlines()[0]},
            "declared_check_counts": record["declared_checks"],
            "scope_limit": record["scope_limit"],
            "commands": commands,
            "source_sha256": source_hashes,
            "log_sha256": {path.relative_to(campaign).as_posix(): sha256(path) for path in log_paths},
            "process_exit_codes": statuses,
        }
        write_json(campaign / f"FUNCTIONAL_VALIDATION_{arch}.json", payload)

    shutil.rmtree(work)
    print(f"FUNCTIONAL_VALIDATION_COMPLETE architectures={len(records)} passed={pass_count}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
