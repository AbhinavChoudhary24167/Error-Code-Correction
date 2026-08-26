#!/usr/bin/env python3
"""Fail-closed checks for the result-blind Gate 04 freeze."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/date2027/rigour_gate_04"
AUTH = Path.home() / ".codex/attachments/2b1b4341-4f44-4f84-988c-e3d41cbf7945/pasted-text.txt"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str, checks: list[dict[str, object]]) -> None:
    checks.append({"check": message, "status": "PASS" if condition else "FAIL"})
    if not condition:
        raise SystemExit(f"PREFLOW FAIL: {message}")


def main() -> int:
    checks: list[dict[str, object]] = []
    contract = json.loads((ROOT / "scripts/gate04/contract_v1.json").read_text(encoding="utf-8"))
    catalog = json.loads((ROOT / "scripts/gate04/candidate_catalog_v1.json").read_text(encoding="utf-8"))
    eligible = json.loads((ROOT / "docs/date2027/rigour_gate_03/ELIGIBLE_IMPLEMENTATION_FREEZE.json").read_text(encoding="utf-8"))
    with (OUT / "ASIC_CANDIDATE_MATRIX.csv").open(encoding="utf-8", newline="") as stream:
        candidates = list(csv.DictReader(stream))
    with (OUT / "FLOW_RUN_MATRIX.csv").open(encoding="utf-8", newline="") as stream:
        flows = list(csv.DictReader(stream))

    require(AUTH.is_file(), "explicit superseding authorization exists", checks)
    authorization = AUTH.read_text(encoding="utf-8")
    require("Begin Gate 04 now" in authorization, "authorization directs Gate 04 to begin", checks)
    require("SCIENTIFIC_ENVIRONMENT_READY_FORMAL_GATE_FAILED" in authorization, "authorization basis is exact", checks)
    require("Do not spend additional time constructing environment-adjudication gates" in authorization, "no further environment gate", checks)
    require((ROOT / "docs/date2027/rigour_gate_03er/GATE_03ER_VERDICT.txt").read_text().strip() == "ENVIRONMENT_ENABLEMENT_FAILED", "Gate 03E-R formal failure preserved", checks)
    require((ROOT / "docs/date2027/rigour_gate_03es/GATE_03ES_VERDICT.txt").read_text().strip() == "ENVIRONMENT_ENABLEMENT_FAILED", "Gate 03E-S formal failure preserved", checks)
    require((ROOT / "docs/date2027/rigour_gate_03es/GATE_03ES_ADJUDICATION_VERDICT.txt").read_text().strip() == "SCIENTIFIC_ENVIRONMENT_READY_FORMAL_GATE_FAILED", "read-only adjudication verdict preserved", checks)

    eligible_rows = [item for item in eligible["records"] if item["eligibility"] == "ELIGIBLE"]
    require(len(eligible_rows) == len(eligible["eligible_implementation_ids"]) == 14, "exactly 14 Gate-02 eligible implementations", checks)
    require(len(candidates) == 18, "matrix contains 14 eligible, two exact overlays, and two references", checks)
    require({item["implementation_id"] for item in eligible_rows}.issubset({row["implementation_id"] for row in candidates}), "all 14 eligible IDs reconciled", checks)
    mandatory = set(contract["physical_experiment"]["candidate_ids"])
    mandatory_rows = {row["implementation_id"]: row for row in candidates if row["implementation_id"] in mandatory}
    require(set(mandatory_rows) == mandatory, "all four mandatory physical candidates reconciled", checks)
    require(all(row["full_flow_eligibility"] == "eligible" for row in mandatory_rows.values()), "all mandatory candidates full-flow eligible", checks)
    require(all(row["encoder_available"] == "True" and row["decoder_available"] == "True" for row in mandatory_rows.values()), "all mandatory candidates have encoder and decoder", checks)

    identities = {item["implementation_id"]: item["canonical_identity_hash"] for item in eligible_rows}
    require(mandatory_rows["secded-rtl-combinational-72-64-v1"]["canonical_identity_hash"] == identities["secded-rtl-combinational-72-64-v1"], "combinational SECDED exact identity bound", checks)
    require(mandatory_rows["secded-rtl-pipelined-72-64-v1"]["canonical_identity_hash"] == identities["secded-rtl-combinational-72-64-v1"], "pipelined SECDED same-code identity bound", checks)
    require(mandatory_rows["hsiao-generated-combinational-72-64-v1"]["canonical_identity_hash"] == identities["hsiao-generated-combinational-72-64-v1"], "Hsiao exact identity bound", checks)
    require(mandatory_rows["shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1"]["canonical_identity_hash"] == identities["shortened-bch-78-64-t2-v1-reference-decoder"], "BCH RTL exact reference identity bound", checks)

    require(len(flows) == 60, "complete 60-flow candidate-plus-reference matrix", checks)
    require(sum(row["kind"] == "candidate" for row in flows) == 40, "at least 40 and exactly 40 mandatory candidate flows", checks)
    require(sum(row["kind"] == "reference" for row in flows) == 20, "20 paired boundary-reference flows", checks)
    require(len({row["run_id"] for row in flows}) == 60 and len({row["run_directory"] for row in flows}) == 60, "run IDs and directories unique", checks)
    require({float(row["clock_period_ns"]) for row in flows} == {5.0, 10.0}, "two frozen clocks", checks)
    require({int(row["physical_seed"]) for row in flows} == {11, 29, 47, 71, 101}, "five frozen paired seeds", checks)
    require(all(row["physical_seed"] == row["gpl_random_seed"] == row["grt_seed"] == row["or_seed"] for row in flows), "all effective seed controls bind to matrix seed", checks)
    require(all(row["status"] == "PLANNED" and row["attempt"] == "1" for row in flows), "result-blind status and no retry", checks)

    wrapper = (ROOT / "scripts/gate04/rtl/gate04_boundaries.sv").read_text(encoding="utf-8")
    require("fault_i" not in wrapper and "fault_mask" not in wrapper and "inject_i" not in wrapper, "no synthesizable fault-injection interface or logic", checks)
    require("backpressure" not in wrapper.lower() and "ready_i" not in wrapper, "no backpressure interface", checks)
    require(wrapper.count("module gate04_") == 6, "four candidate and two reference top modules", checks)
    require("secded_pipelined_72_64_v1_encoder" in wrapper and "secded_pipelined_72_64_v1_decoder" in wrapper, "same-code internal pipeline retained in wrapper", checks)

    protected_diff = subprocess.check_output(
        ["git", "diff", "--", "asic/rtl", "green_ecc_physical_simulation/registry", "green_ecc_physical_simulation/rtl", "ecc_selector.py", "architecture/selection.py"],
        cwd=ROOT,
    )
    require(not protected_diff, "production RTL, registries, and selectors have no tracked diff", checks)
    identity_manifest = json.loads((OUT / "PRE_FLOW_IDENTITY_MANIFEST.json").read_text(encoding="utf-8"))
    require(all(sha256(ROOT / record["path"]) == record["sha256"] for record in identity_manifest["files"]), "pre-flow raw source hashes validate", checks)
    require(contract["activity"]["payload_operations_per_trace"] >= 100000, "at least 100,000 useful operations per activity trace", checks)
    require(contract["activity"]["trace_classes"] == ["no_error", "single_error", "double_error"], "three separate activity conditions", checks)
    require(contract["statistics"]["bootstrap_resamples"] == 20000 and contract["statistics"]["material_fraction"] == 0.05, "bootstrap and materiality rules frozen", checks)

    result = {
        "schema_version": 1,
        "status": "PASS",
        "authorization_sha256": sha256(AUTH),
        "candidate_rows": len(candidates),
        "gate02_eligible_rows": len(eligible_rows),
        "candidate_flows": sum(row["kind"] == "candidate" for row in flows),
        "reference_flows": sum(row["kind"] == "reference" for row in flows),
        "checks": checks,
    }
    (OUT / "PREFLOW_VALIDATION.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"GATE04_PREFLOW_PASS checks={len(checks)} candidate_flows=40 reference_flows=20")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
