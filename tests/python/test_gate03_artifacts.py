from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gate03.constants import (
    ELIGIBLE_IMPLEMENTATIONS,
    EVIDENCE_ENUMS,
    EVIDENCE_HEADER,
    EXCLUDED_IMPLEMENTATIONS,
    PPA_HEADER,
    RAW_REPORT_HEADER,
    RTL_MATRIX_HEADER,
    SENTINEL_HEADER,
    SENTINELS,
    STAGES,
    WORKLOADS,
)
from scripts.gate03.validate_artifacts import validate


OUT = ROOT / "docs" / "date2027" / "rigour_gate_03"


def _csv(name: str):
    with (OUT / name).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def test_gate03_standalone_validator_passes():
    assert validate() == []


def test_required_artifacts_and_exact_headers():
    required = {
        "GATE_03_REPORT.md", "ELIGIBLE_IMPLEMENTATION_FREEZE.json",
        "TOOLCHAIN_AND_COLLATERAL_INVENTORY.json", "RTL_TO_IMPLEMENTATION_MATRIX.csv",
        "FAIRNESS_AND_CONSTRAINT_CONTRACT.md", "PPA_FEASIBILITY_MATRIX.csv",
        "SENTINEL_RUNS.csv", "RAW_REPORT_INDEX.csv", "EVIDENCE_CLASSIFICATION.csv",
        "CLAIM_SCOPE_DECISION.md", "GATE_04_EXECUTION_PLAN.md", "BINARY_NO_GO_DECISION.md",
        "baseline/environment_manifest.json", "baseline/command_manifest.json",
    }
    assert all((OUT / name).is_file() for name in required)
    assert _csv("RTL_TO_IMPLEMENTATION_MATRIX.csv")[0] == list(RTL_MATRIX_HEADER)
    assert _csv("PPA_FEASIBILITY_MATRIX.csv")[0] == list(PPA_HEADER)
    assert _csv("SENTINEL_RUNS.csv")[0] == list(SENTINEL_HEADER)
    assert _csv("RAW_REPORT_INDEX.csv")[0] == list(RAW_REPORT_HEADER)
    assert _csv("EVIDENCE_CLASSIFICATION.csv")[0] == list(EVIDENCE_HEADER)


def test_population_and_gate02_identity_are_exact():
    _, rows = _csv("RTL_TO_IMPLEMENTATION_MATRIX.csv")
    eligible = {row["implementation_id"] for row in rows if row["eligibility"] == "ELIGIBLE"}
    excluded = {row["implementation_id"] for row in rows if row["eligibility"] == "EXCLUDED"}
    assert eligible == set(ELIGIBLE_IMPLEMENTATIONS)
    assert excluded == set(EXCLUDED_IMPLEMENTATIONS)
    assert len(rows) == len({row["implementation_id"] for row in rows}) == 17
    with (ROOT / "docs/date2027/rigour_gate_02/CODE_IDENTITY_MATRIX.csv").open(encoding="utf-8", newline="") as handle:
        gate02 = {row["implementation_id"]: row for row in csv.DictReader(handle)}
    assert all(row["mathematical_code_id"] == gate02[row["implementation_id"]]["code_id"] for row in rows)


def test_h2_requires_identical_identity_and_distinct_structures():
    _, rows = _csv("PPA_FEASIBILITY_MATRIX.csv")
    by_id = {row["implementation_id"]: row for row in rows}
    conventional = by_id["secded-rtl-combinational-72-64-v1"]
    hsiao = by_id["hsiao-generated-combinational-72-64-v1"]
    assert conventional["mathematical_code_id"] == "extended-hamming-secded-72-64-v1"
    assert hsiao["mathematical_code_id"] == "hsiao-secded-72-64-v1"
    assert conventional["canonical_identity_hash"] == "40bc866e1a85aa0d8597f49fa6e97bc29a5e64d75631e13ba90ec2befcd3f749"
    assert hsiao["canonical_identity_hash"] == "1cc658a0e86f0911d0d26def91d61c2b4dc146daaea531a5a923aabf0ca387a7"
    assert conventional["hardware_structure_id"] != hsiao["hardware_structure_id"]
    assert conventional["h2_status"] == hsiao["h2_status"] == "UNTESTABLE_IDENTITY_MISMATCH"


def test_workload_separation_and_primary_power_guard():
    assert WORKLOADS["verification-stress-v1"]["eligible_for_primary_power"] is False
    assert WORKLOADS["normal-clean-random-v1"]["eligible_for_primary_power"] is True
    assert WORKLOADS["conditional-single-v1"]["purpose"] == "conditional_power_only"
    assert WORKLOADS["conditional-double-v1"]["purpose"] == "conditional_power_only"
    contract = json.loads((OUT / "baseline/workload_contract.json").read_text(encoding="utf-8"))
    assert contract["seed"] == "0x475245454E454343"
    assert contract["warmup_cycles"] == 256 and contract["measured_cycles"] == 8192
    assert contract["verification_stress_may_populate_primary_power"] is False
    _, ppa = _csv("PPA_FEASIBILITY_MATRIX.csv")
    assert all(row["primary_activity_id"] == "normal-clean-random-v1" for row in ppa)
    _, evidence = _csv("EVIDENCE_CLASSIFICATION.csv")
    stress = [row for row in evidence if row["workload_id"] == "verification-stress-v1"]
    assert stress and all("prohibited" in row["limitations"] for row in stress)


def test_synthesized_wrappers_have_no_injection_logic():
    wrapper_paths = sorted((ROOT / "scripts/gate03/rtl").glob("*.sv"))
    wrapper = "\n".join(path.read_text(encoding="utf-8") for path in wrapper_paths)
    assert "error_mask_i" not in wrapper
    assert "fault_mask" not in wrapper
    assert "testbench_mask" not in wrapper
    assert not re.search(r"assign\s+\w+\s*=.*\^", wrapper)
    verification = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "scripts/gate03/verification").glob("*.sv"))
    assert "testbench_mask" in verification or "fault_mask" in verification
    assert "^" in verification


def test_bch_requires_complete_exact_proof_and_all_stages_are_blocked():
    audit = json.loads((OUT / "baseline/bch_rtl_acceptance_audit.json").read_text(encoding="utf-8"))
    assert audit["target_mathematical_code_id"] == "shortened-bch-78-64-t2-v1"
    assert audit["encoder_acceptance"]["required_payload_cases"] == 65
    assert audit["decoder_acceptance"]["required_mask_cases"] == 3082
    assert audit["probe_only_equivalence_is_complete"] is False
    assert audit["accepted_rtl"] == []
    _, sentinel = _csv("SENTINEL_RUNS.csv")
    bch = [row for row in sentinel if row["implementation_id"] == "shortened-bch-78-64-t2-v1-reference-decoder"]
    assert len(bch) == 2 * len(STAGES)
    assert all(row["status"] in {"BLOCKED_MISSING_VALID_RTL", "PASS_FROZEN_IDENTITY_COPIED_EXACTLY"} for row in bch)


def test_two_runs_cover_every_stage_and_local_functional_repeats_pass():
    _, rows = _csv("SENTINEL_RUNS.csv")
    assert len(rows) == 2 * len(SENTINELS) * len(STAGES)
    for repeat in (1, 2):
        for identifier in SENTINELS:
            subset = [row for row in rows if row["repeat_index"] == str(repeat) and row["implementation_id"] == identifier]
            assert {row["stage"] for row in subset} == set(STAGES)
    for identifier in ("secded-rtl-combinational-72-64-v1", "hsiao-generated-combinational-72-64-v1"):
        local = [row for row in rows if row["implementation_id"] == identifier and row["stage"] in {"rtl_elaboration", "functional_simulation"}]
        assert len(local) == 4 and all(row["status"] == "PASS" for row in local)
    for slug in ("secded", "hsiao"):
        first = json.loads((OUT / f"baseline/run-01/{slug}/source_snapshot.json").read_text(encoding="utf-8"))
        second = json.loads((OUT / f"baseline/run-02/{slug}/source_snapshot.json").read_text(encoding="utf-8"))
        assert first["rtl_sha256"] == second["rtl_sha256"]


def test_evidence_enums_raw_hashes_and_no_fake_physical_numbers():
    _, evidence = _csv("EVIDENCE_CLASSIFICATION.csv")
    assert all(row["classification"] in EVIDENCE_ENUMS for row in evidence)
    _, reports = _csv("RAW_REPORT_INDEX.csv")
    assert len(reports) == len({row["raw_report_id"] for row in reports})
    for row in reports:
        if row["retained_in_git"] == "true":
            path = ROOT / row["path"]
            assert path.is_file()
            assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
    _, ppa = _csv("PPA_FEASIBILITY_MATRIX.csv")
    numeric_physical = PPA_HEADER[24:40]
    assert all(not row[field] for row in ppa for field in numeric_physical)


def test_gate01_gate02_immutable_authorized_scope_and_binary_verdict():
    environment = json.loads((OUT / "baseline/environment_manifest.json").read_text(encoding="utf-8"))
    assert environment["gate01"]["byte_identical"] is True
    assert environment["gate02"]["byte_identical"] is True
    for gate in ("rigour_gate_01", "rigour_gate_02"):
        assert subprocess.run(["git", "diff", "--quiet", "HEAD", "--", f"docs/date2027/{gate}"], cwd=ROOT).returncode == 0
    # Validate the candidate change set. Other tests may create ignored or
    # untracked runtime fixtures while the isolated regression is in flight.
    staged = subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT, text=True)
    candidate_paths = staged.splitlines()
    if not candidate_paths:  # Main workspace keeps additions intentionally unstaged.
        candidate_paths = [
            line[3:] for line in subprocess.check_output(
                ["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT, text=True
            ).splitlines()
        ]
    gate03r_paths = (
        "asic/rtl/bch/bch_78_64_t2_v1.sv",
        "asic/rtl/secded/secded_pipelined_72_64_v1.sv",
        "docs/date2027/rigour_gate_03r/",
        "green_ecc_physical_simulation/registry/implementations/secded-rtl-pipelined-72-64-v1.json",
        "green_ecc_physical_simulation/registry/implementations/shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1.json",
        "green_ecc_physical_simulation/registry/registry_gate03r.json",
        "scripts/gate03r/",
        "tests/python/test_gate03r_artifacts.py",
    )
    runtime_paths = (
        "PracticalSRAMSimulator.exe",
        "drift.json",
        "tests/fixtures/runtime_ml_feature_pack/",
    )
    for path in candidate_paths:
        path = path.replace("\\", "/")
        assert path.startswith(
            ("docs/date2027/rigour_gate_03/", "scripts/gate03/", "tests/python/test_gate03_")
            + gate03r_paths
            + runtime_paths
        )
    decision = (OUT / "BINARY_NO_GO_DECISION.md").read_text(encoding="utf-8")
    assert re.findall(r"(?m)^(?:GO_TO_GATE_04|NO_GO_FOR_DATE_2027_REGULAR_PAPER_CORE)$", decision) == [
        "NO_GO_FOR_DATE_2027_REGULAR_PAPER_CORE"
    ]
    assert "Gate 03R" in (OUT / "GATE_04_EXECUTION_PLAN.md").read_text(encoding="utf-8")


def test_revised_terminology_guards():
    corpus = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in OUT.rglob("*") if path.is_file())
    assert "expected verdict" not in corpus.lower()
    assert "currently known blocker" in corpus.lower() or "mechanical blockers" in corpus.lower()
    assert "critical_path_limited_frequency_mhz" in (OUT / "PPA_FEASIBILITY_MATRIX.csv").read_text(encoding="utf-8")
    assert "fmax" not in _csv("PPA_FEASIBILITY_MATRIX.csv")[0]
    assert "not called Fmax" in corpus
    assert "20% fault rate" not in corpus
