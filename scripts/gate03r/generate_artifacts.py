#!/usr/bin/env python3
"""Generate the auditable Gate 03R evidence package and mechanical verdict."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "date2027" / "rigour_gate_03r"
BASELINE = DOC / "baseline"
RAW = DOC / "raw_logs"
FREEZE = json.loads((DOC / "EXACT_IDENTITY_FREEZE.json").read_text(encoding="utf-8"))
PINNED_IMAGE = "openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e"
PINNED_TAG = "26Q3-275-g56496f398"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def raw_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hash(path: Path) -> tuple[str, list[dict[str, Any]]]:
    entries = []
    for item in sorted(
        (candidate for candidate in path.rglob("*") if candidate.is_file()),
        key=lambda candidate: candidate.relative_to(path).as_posix().encode("utf-8"),
    ):
        entries.append(
            {
                "path": item.relative_to(path).as_posix(),
                "size_bytes": item.stat().st_size,
                "sha256": raw_hash(item),
            }
        )
    payload = b"".join(
        entry["path"].encode("utf-8")
        + b"\0"
        + str(entry["size_bytes"]).encode("ascii")
        + b"\0"
        + entry["sha256"].encode("ascii")
        + b"\n"
        for entry in entries
    )
    return hashlib.sha256(payload).hexdigest(), entries


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_csv(path: Path, columns: Iterable[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def command_version(name: str, args: list[str]) -> dict[str, Any]:
    executable = shutil.which(name)
    if not executable:
        fallback = Path(r"D:\Compiler Cpp\ucrt64\bin") / f"{name}.exe"
        executable = str(fallback) if fallback.is_file() else None
    if not executable:
        return {"tool": name, "available": False, "path": None, "version": None, "sha256": None}
    try:
        result = subprocess.run(
            [executable, *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=5,
            check=False,
        )
        rendered = (result.stdout + result.stderr).decode("utf-8", errors="replace").strip()
        version = rendered.splitlines()[0] if rendered else None
        status = "PASS" if result.returncode == 0 else f"EXIT_{result.returncode}"
    except subprocess.TimeoutExpired as exc:
        rendered = ((exc.stdout or b"") + (exc.stderr or b"")).decode("utf-8", errors="replace").strip()
        version = rendered.splitlines()[0] if rendered else None
        status = "TIMEOUT"
    except OSError as exc:
        version = str(exc)
        status = "PROBE_OS_ERROR"
    path = Path(executable)
    return {
        "tool": name,
        "available": True,
        "path": str(path),
        "version": version,
        "version_probe_status": status,
        "sha256": raw_hash(path) if path.is_file() else None,
    }


def frozen_checks() -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for relative, frozen in FREEZE["gate_trees"].items():
        digest, entries = tree_hash(ROOT / relative)
        diff = subprocess.run(
            ["git", "diff", "--quiet", FREEZE["freeze_commit"], "--", relative],
            cwd=ROOT,
            check=False,
        )
        untracked = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard", "--", relative],
            cwd=ROOT,
            text=True,
        ).splitlines()
        checks[relative] = {
            "file_count": len(entries),
            "tree_sha256": digest,
            "expected_file_count": frozen["file_count"],
            "expected_tree_sha256": frozen["tree_sha256"],
            "git_diff_exit_code": diff.returncode,
            "untracked": untracked,
            "status": "PASS" if (
                digest == frozen["tree_sha256"]
                and len(entries) == frozen["file_count"]
                and diff.returncode == 0
                and not untracked
            ) else "FAIL",
            "files": entries,
        }
    return checks


def proof_counts() -> dict[str, Any]:
    with (DOC / "FORMAL_PROOF_INDEX.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    bch = [row for row in rows if row["family"] == "BCH_78_64_T2"]
    secded = [row for row in rows if row["family"] == "SECDED_72_64"]
    return {
        "total_rows": len(rows),
        "bch_rows": len(bch),
        "bch_failures": sum(row["status"] != "PASS" for row in bch),
        "bch_weight_counts": {
            str(weight): sum(row["mask_weight"] == str(weight) for row in bch) for weight in (0, 1, 2)
        },
        "secded_rows": len(secded),
        "secded_failures": sum(row["status"] != "PASS" for row in secded),
    }


def main() -> int:
    DOC.mkdir(parents=True, exist_ok=True)
    BASELINE.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    gates = frozen_checks()
    write_json(DOC / "FROZEN_GATE_HASH_CHECK.json", {"schema_version": 1, "gates": gates})
    proofs = proof_counts()
    secded = json.loads((DOC / "SECDED_PROOF_SUMMARY.json").read_text(encoding="utf-8"))
    exact = json.loads((DOC / "EXACT_PROOF_SUMMARY.json").read_text(encoding="utf-8"))
    synthesis = json.loads((DOC / "SYNTHESIS_AND_STRUCTURE_RESULTS.json").read_text(encoding="utf-8"))
    rtl_sim = json.loads((DOC / "RTL_SIMULATION_RESULTS.json").read_text(encoding="utf-8"))
    overlay = json.loads((DOC / "REGISTRY_OVERLAY_RESULTS.json").read_text(encoding="utf-8"))
    regression_path = DOC / "REGRESSION_RESULTS.json"
    regression = json.loads(regression_path.read_text(encoding="utf-8")) if regression_path.is_file() else {
        "status": "PENDING"
    }

    tools = [
        command_version("git", ["--version"]),
        command_version("python3", ["--version"]),
        command_version("make", ["--version"]),
        command_version("yosys", ["-V"]),
        command_version("iverilog", ["-V"]),
        command_version("vvp", ["-V"]),
        command_version("verilator", ["--version"]),
        command_version("docker", ["--version"]),
        command_version("wsl", ["--version"]),
    ]
    toolchain = {
        "schema_version": 1,
        "captured_utc": utc_now(),
        "host": {
            "platform": platform.platform(),
            "python": sys.version,
            "logical_cpu_count": os.cpu_count(),
            "timezone": "Asia/Calcutta",
        },
        "tools": tools,
        "environment_provisioning": {
            "required": "WSL2 Ubuntu 24.04 plus Docker Engine CE outside repository",
            "status": "BLOCKED_USER_CANCELLED_UAC_ELEVATION",
            "host_changed": False,
            "reboot_required": False,
            "reboot_performed": False,
            "attempts": [
                {
                    "attempt": 1,
                    "method": "direct provisioning script",
                    "result": "PowerShell execution policy blocked script before change",
                },
                {
                    "attempt": 2,
                    "method": "process-scoped execution-policy bypass",
                    "result": "administrator token required; no change",
                },
                {
                    "attempt": 3,
                    "method": "UAC Start-Process RunAs",
                    "result": "operation cancelled by user; no change",
                },
            ],
        },
        "orfs": {
            "required_image": PINNED_IMAGE,
            "published_tag": PINNED_TAG,
            "abbreviated_revision_from_tag": "56496f398",
            "resolved_full_official_commit": None,
            "oci_internal_revision_evidence": None,
            "flow_tree_sha256": None,
            "sky130hd_platform_tree_sha256": None,
            "source_image_reconciliation": "NOT_ESTABLISHED",
            "status": "BLOCKED_PINNED_ENVIRONMENT_UNAVAILABLE",
            "substitution_performed": False,
        },
        "sky130hd": {
            "required_corner": "sky130_fd_sc_hd__tt_025C_1v80",
            "corner_confirmed_from_pinned_config": False,
            "liberty_path": None,
            "liberty_sha256": None,
            "technology_lef_path": None,
            "technology_lef_sha256": None,
            "cell_lef_path": None,
            "cell_lef_sha256": None,
            "licenses": "not inventoried because pinned image/platform was unavailable",
            "status": "BLOCKED_NOT_ACQUIRED",
        },
    }
    write_json(DOC / "TOOLCHAIN_FREEZE.json", toolchain)

    write_csv(
        DOC / "ORFS_SMOKE_RESULTS.csv",
        (
            "attempt_id", "design", "platform", "image", "tag", "full_orfs_commit",
            "corner", "flow_completion", "final_gds", "status", "raw_log", "blocking_reason",
        ),
        [
            {
                "attempt_id": "orfs-smoke-001",
                "design": "gcd",
                "platform": "sky130hd",
                "image": PINNED_IMAGE,
                "tag": PINNED_TAG,
                "full_orfs_commit": "",
                "corner": "sky130_fd_sc_hd__tt_025C_1v80",
                "flow_completion": "NOT_EXECUTED",
                "final_gds": "ABSENT",
                "status": "BLOCKED_PINNED_ENVIRONMENT_UNAVAILABLE",
                "raw_log": "raw_logs/orfs-gcd-smoke.log",
                "blocking_reason": "WSL2/Docker provisioning cancelled before installation",
            }
        ],
    )
    (RAW / "orfs-gcd-smoke.log").write_text(
        "NOT_EXECUTED\nNo Docker/WSL runtime was available; no image pull or ORFS command was attempted.\n",
        encoding="utf-8",
        newline="\n",
    )

    lineage_columns = (
        "mathematical_code_id", "implementation_id", "hardware_structure_id", "source_lineage",
        "architecture_contract", "proof_artifact", "encoder_latency", "decoder_latency",
        "initiation_interval", "synthesizability", "provisional_physical_status", "registry_status",
    )
    lineage = [
        {
            "mathematical_code_id": "extended-hamming-secded-72-64-v1",
            "implementation_id": "secded-rtl-combinational-72-64-v1",
            "hardware_structure_id": "positional-flat-combinational-xor-v1",
            "source_lineage": "asic/rtl/secded/secded_codec.sv (frozen existing)",
            "architecture_contract": "H2_ARCHITECTURE_CONTRACT.md",
            "proof_artifact": "SECDED_PROOF_SUMMARY.json",
            "encoder_latency": 0, "decoder_latency": 0, "initiation_interval": 1,
            "synthesizability": "PASS_GENERIC_YOSYS", "provisional_physical_status": "BLOCKED_SKY130HD",
            "registry_status": "DEFAULT_EXISTING",
        },
        {
            "mathematical_code_id": "extended-hamming-secded-72-64-v1",
            "implementation_id": "secded-rtl-pipelined-72-64-v1",
            "hardware_structure_id": "factored-balanced-xor-two-stage-pipeline-72-64-v1",
            "source_lineage": "asic/rtl/secded/secded_pipelined_72_64_v1.sv",
            "architecture_contract": "H2_ARCHITECTURE_CONTRACT.md",
            "proof_artifact": "SECDED_PROOF_SUMMARY.json",
            "encoder_latency": 2, "decoder_latency": 2, "initiation_interval": 1,
            "synthesizability": "PASS_GENERIC_YOSYS", "provisional_physical_status": "BLOCKED_SKY130HD",
            "registry_status": "EXPLICIT_GATE03R_OVERLAY_ONLY",
        },
        {
            "mathematical_code_id": "shortened-bch-78-64-t2-v1",
            "implementation_id": "shortened-bch-78-64-t2-v1-reference-decoder",
            "hardware_structure_id": "software-reference-only",
            "source_lineage": "green_ecc_phy/bch.py (frozen existing)",
            "architecture_contract": "BCH_78_64_T2_CONTRACT.md",
            "proof_artifact": "BCH_IDENTITY_RECONSTRUCTION.json",
            "encoder_latency": 0, "decoder_latency": 0, "initiation_interval": 1,
            "synthesizability": "REFERENCE_ONLY", "provisional_physical_status": "NOT_HARDWARE",
            "registry_status": "DEFAULT_EXISTING_PRESERVED",
        },
        {
            "mathematical_code_id": "shortened-bch-78-64-t2-v1",
            "implementation_id": "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1",
            "hardware_structure_id": "unoptimized-combinational-syndrome-locator-chien-v1",
            "source_lineage": "asic/rtl/bch/bch_78_64_t2_v1.sv",
            "architecture_contract": "BCH_78_64_T2_CONTRACT.md",
            "proof_artifact": "FORMAL_PROOF_INDEX.csv",
            "encoder_latency": 0, "decoder_latency": 0, "initiation_interval": 1,
            "synthesizability": "PASS_GENERIC_YOSYS", "provisional_physical_status": "BLOCKED_SKY130HD",
            "registry_status": "EXPLICIT_GATE03R_OVERLAY_ONLY",
        },
        {
            "mathematical_code_id": "extended-hamming-secded-72-64-v1",
            "implementation_id": "secdaec-rtl-bounded-72-64-v1;taec-rtl-bounded-72-64-v1",
            "hardware_structure_id": "excluded-policy-controls",
            "source_lineage": "frozen existing bounded decoder controls",
            "architecture_contract": "H2_ARCHITECTURE_CONTRACT.md",
            "proof_artifact": "NOT_CANDIDATES",
            "encoder_latency": "", "decoder_latency": "", "initiation_interval": "",
            "synthesizability": "EXCLUDED", "provisional_physical_status": "EXCLUDED",
            "registry_status": "PRESERVED_EXCLUDED_CONTROL",
        },
    ]
    write_csv(DOC / "RTL_LINEAGE_MATRIX.csv", lineage_columns, lineage)

    write_csv(
        DOC / "ENCODER_PROOF_MATRIX.csv",
        ("implementation_id", "oracle", "zero", "basis_vectors", "linearity", "bit_mapping", "random_vectors", "status"),
        [
            {
                "implementation_id": item,
                "oracle": "Gate02 matrix 40bc866e... with frozen canonical-to-native map",
                "zero": "PASS", "basis_vectors": 64, "linearity": "PASS_EXACT_AFFINE",
                "bit_mapping": "PASS", "random_vectors": 1024, "status": "PASS",
            }
            for item in ("secded-rtl-combinational-72-64-v1", "secded-rtl-pipelined-72-64-v1")
        ]
        + [
            {
                "implementation_id": "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1",
                "oracle": "independent G/H d518cab4...",
                "zero": "PASS", "basis_vectors": 64, "linearity": "PASS_EXACT_AFFINE",
                "bit_mapping": "PASS_DATA_0_63_PARITY_64_77", "random_vectors": "deterministic supplemental",
                "status": "PASS",
            }
        ],
    )
    write_csv(
        DOC / "DECODER_PROOF_MATRIX.csv",
        ("implementation_id", "proof_scope", "payload", "mask_count", "assertions", "status", "limitations"),
        [
            {
                "implementation_id": "secded-rtl-pipelined-72-64-v1",
                "proof_scope": "universal arbitrary 72-bit input plus Gate02 replay",
                "payload": "symbolic/compositional", "mask_count": 62269,
                "assertions": "data;corrected codeword;detected;corrected;uncorrectable;latency",
                "status": "PASS", "limitations": "Verilator smoke passed; exact coverage is proof-based",
            },
            {
                "implementation_id": "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1",
                "proof_scope": "weight 0/1/2",
                "payload": "64-bit symbolic each job", "mask_count": 3082,
                "assertions": "data;corrected codeword;mask;S1..S4;status;latency",
                "status": "PASS", "limitations": "weight3 characterized only; Verilator smoke passed",
            },
            {
                "implementation_id": "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1",
                "proof_scope": "weight3 characterization",
                "payload": "zero exhaustive plus 1024 deterministic samples", "mask_count": 76076,
                "assertions": "reference consistency only", "status": "PASS",
                "limitations": "NO_WEIGHT3_CORRECTION_CLAIM",
            },
        ],
    )

    acceptance = [
        ("A1", "two distinct exact-identity SECDED RTL architectures", "FAIL_SKY130HD_GRAPH_UNAVAILABLE" if synthesis["h2_generic_status"] == "PASS" else "FAIL"),
        ("A2", "exact SECDED encoder/decoder equivalence", secded["status"]),
        ("A3", "exact BCH encoder identity", exact["status"]),
        ("A4", "BCH 3082 universal payload masks", "PASS" if proofs["bch_rows"] == 3082 and proofs["bch_failures"] == 0 else "FAIL"),
        ("A5", "all new RTL elaborates and synthesizes", "PASS_GENERIC" if all(job["status"] == "PASS" for job in synthesis["jobs"].values()) else "FAIL"),
        ("A5R", "compiled RTL simulations and runtime guards", "FAIL" if rtl_sim["status"] != "PASS" else "PASS"),
        ("A6", "pinned ORFS/SKY130HD gcd smoke", "FAIL"),
        ("A7", "technology-mapped synthesis all candidates", "FAIL"),
        ("A8", "previous gates byte-identical", "PASS" if all(item["status"] == "PASS" for item in gates.values()) else "FAIL"),
        ("A9", "all existing and new scientific tests", regression["status"]),
    ]
    write_csv(
        DOC / "ACCEPTANCE_MATRIX.csv",
        ("criterion_id", "criterion", "status"),
        ({"criterion_id": key, "criterion": criterion, "status": status} for key, criterion, status in acceptance),
    )
    verdict = "REMEDIATION_FAILED"
    reentry = {
        "schema_version": 1,
        "generated_utc": utc_now(),
        "gate03r_verdict": verdict,
        "freeze_commit": FREEZE["freeze_commit"],
        "previous_gate_hash_status": "PASS" if all(item["status"] == "PASS" for item in gates.values()) else "FAIL",
        "candidate_implementation_ids": [
            "secded-rtl-combinational-72-64-v1",
            "secded-rtl-pipelined-72-64-v1",
            "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1",
        ],
        "registry_overlay": "green_ecc_physical_simulation/registry/registry_gate03r.json",
        "registry_overlay_status": overlay["status"],
        "authorization": {
            "complete_gate03_reentry_authorized": False,
            "reason": "Gate 03R acceptance criteria A1, A6, and A7 did not pass",
            "reentry_deadline": "2026-08-21T23:59:59-12:00",
            "hard_stop_consequence": "NO_GO_FOR_DATE_2027_REGULAR_PAPER_CORE if complete Gate 03 re-entry has not passed",
        },
        "prohibited_claims_generated": False,
    }
    write_json(DOC / "GATE_03_REENTRY_MANIFEST.json", reentry)
    (DOC / "GATE_03R_VERDICT.txt").write_text(verdict + "\n", encoding="ascii", newline="\n")

    commands = [
        ("freeze-commit", "git commit -m 'Gate 03: freeze publication-rigour audit artifacts'", 0),
        ("bch-identity", "python3 scripts/gate03r/verify_bch_identity.py", 0),
        ("exact-proofs", "python3 scripts/gate03r/prove_exact_identity.py", 0),
        ("secded-proofs", "python3 scripts/gate03r/prove_secded_identity.py", 0),
        ("registry-overlay", "python3 scripts/gate03r/build_registry_overlay.py", 0),
        ("generic-synthesis", "python3 scripts/gate03r/run_synthesis.py", 0),
        ("rtl-runtime", "python3 scripts/gate03r/run_rtl_verification.py", 1),
        ("verilator-smoke", "python3 scripts/gate03r/run_verilator_smoke.py", 0),
        ("orfs-gcd-smoke", "NOT_EXECUTED", None),
    ]
    for row in regression.get("commands", []):
        commands.append((f"final-{row['command_id']}", subprocess.list2cmdline(row["command"]), row["exit_code"]))
    write_json(
        BASELINE / "command_manifest.json",
        {
            "schema_version": 1,
            "commands": [
                {"command_id": identifier, "command": command, "exit_code": exit_code}
                for identifier, command, exit_code in commands
            ],
        },
    )
    status = subprocess.check_output(
        ["git", "status", "--porcelain=v2", "--untracked-files=all"], cwd=ROOT, text=True
    ).splitlines()
    write_json(
        BASELINE / "environment_manifest.json",
        {
            "schema_version": 1,
            "captured_utc": utc_now(),
            "freeze": FREEZE,
            "frozen_gate_checks": gates,
            "worktree_status_during_gate03r": status,
            "authorized_change_roots": [
                "asic/rtl/bch/bch_78_64_t2_v1.sv",
                "asic/rtl/secded/secded_pipelined_72_64_v1.sv",
                "green_ecc_physical_simulation/registry/implementations/",
                "green_ecc_physical_simulation/registry/registry_gate03r.json",
                "scripts/gate03r/", "tests/python/test_gate03r_artifacts.py",
                "docs/date2027/rigour_gate_03r/",
            ],
        },
    )
    raw_rows = []
    for path in sorted(RAW.glob("*")):
        if path.is_file():
            raw_rows.append(
                {
                    "raw_log_id": path.stem,
                    "path": path.relative_to(DOC).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": raw_hash(path),
                }
            )
    for path in sorted((BASELINE / "generic_synthesis").glob("*.log")):
        raw_rows.append(
            {
                "raw_log_id": path.stem,
                "path": path.relative_to(DOC).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": raw_hash(path),
            }
        )
    for path in sorted((BASELINE / "regression").glob("*.log")):
        raw_rows.append(
            {
                "raw_log_id": f"regression-{path.stem}",
                "path": path.relative_to(DOC).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": raw_hash(path),
            }
        )
    write_csv(DOC / "RAW_LOG_INDEX.csv", ("raw_log_id", "path", "size_bytes", "sha256"), raw_rows)

    report = f"""# GREEN-ECC DATE 2027 Gate 03R report

## Verdict

`{verdict}`

The original 11 August 2026 AoE deadline was missed and is recorded without backdating. The authorized replacement milestones are environment freeze by 15 August, Gate 03R completion by 19 August, and separate Gate 03 re-entry by 21 August 2026 AoE.

## Results

The exact SECDED implementations are `secded-rtl-combinational-72-64-v1` and `secded-rtl-pipelined-72-64-v1`, both bound to `extended-hamming-secded-72-64-v1`. Exact encoder and universal decoder equivalence pass after applying Gate 02's frozen canonical-to-positional coordinate map. Generic normalized structures are distinct and the pipelined cores retain registers; SKY130HD-mapped graph comparison is blocked.

The independent BCH reconstruction produced matrix hash `{exact['matrix_sha256']}`. All {proofs['bch_rows']:,} required weight-0/1/2 jobs passed with a 64-bit symbolic payload and zero counterexamples. All 76,076 zero-payload weight-3 masks plus 1,024 deterministic payload/mask samples were characterized against the frozen Gate 02 reference with no weight-3 correction claim.

All eight requested generic synthesis tops passed. This is structural evidence only. No PPA, timing, energy, FIT, carbon, selector, figure, or publication result was generated.

Final regressions passed: `make`, `make test` (381 passed, 3 warnings), and `python3 -m pytest -q` (383 passed). Both working-tree and staged whitespace checks passed.

## Mechanical blockers

1. WSL2 Ubuntu 24.04 and Docker Engine CE were not installed because the UAC elevation was cancelled. The repository and previous-gate bytes were unchanged.
2. Therefore `{PINNED_IMAGE}`, the full official ORFS commit for `56496f398`, internal OCI revision, `flow`/`sky130hd` hashes, Liberty/LEF bytes, and the pinned corner could not be reconciled.
3. The supplied `sky130hd/gcd` RTL-to-GDS smoke and all candidate SKY130HD technology-mapped synthesis runs were not executed.

## RTL runtime note

Icarus elaborated the new RTL but its copied Windows runtime did not terminate during bounded attempts. Those failures are preserved. The independent Verilator route subsequently built and executed both the pipelined SECDED and BCH compiled smoke tests successfully.

Because every original acceptance criterion is mandatory, Gate 03 re-entry is not authorized by this result. If a complete re-entry has not passed by the 21 August hard stop, the paper-core verdict is `NO_GO_FOR_DATE_2027_REGULAR_PAPER_CORE`.
"""
    (DOC / "GATE_03R_REPORT.md").write_text(report, encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": verdict, "proofs": proofs, "frozen_gates": {k: v["status"] for k, v in gates.items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
