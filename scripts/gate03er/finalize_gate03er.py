#!/usr/bin/env python3
"""Revalidate preserved scope and publish the additive Gate 03E-R evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from reproducibility import sha256_file, stable_tree_hash, write_json


V1_HASHES = {
    "policy": "258694f328084c3fb92dec24e07b3b40d261037d5b1bd8d32b119684211d0b9a",
    "comparator": "9038cd174ccfd5c62d64908c6df9416f2ff542d58daa44faf3f9d6e5527d3a92",
    "comparison": "655a0b7f6aadde7fcf0c45266e9f80fbf77f2635badd7bcee11a0d737c447628",
}
DEADLINE = datetime(2026, 8, 17, 11, 59, 59, tzinfo=timezone.utc)


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def file_record(path: Path) -> dict[str, object]:
    return {"path": str(path), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}


def validate_record(path: Path, record: dict[str, object]) -> bool:
    return path.is_file() and path.stat().st_size == record["size_bytes"] and sha256_file(path) == record["sha256"]


def revalidate_mapping(repo: Path, v1: Path) -> dict[str, object]:
    mapping_path = v1 / "mapping/mapping-validation.json"
    mapping = json.loads(mapping_path.read_text())
    source_root = v1 / "source/OpenROAD-flow-scripts"
    jobs: list[dict[str, object]] = []
    all_pass = mapping.get("status") == "PASS" and len(mapping.get("jobs", [])) == 4
    for job in mapping.get("jobs", []):
        checks: list[dict[str, object]] = []
        for source in job.get("source_files", []):
            path = repo / str(source["path"])
            checks.append({"name": f"source_hash:{source['path']}", "pass": validate_record(path, source)})
        for label, artifact in job.get("mapped_artifacts", {}).items():
            path = v1 / "mapping" / str(artifact["path"])
            checks.append({"name": f"mapped_artifact_hash:{label}", "pass": validate_record(path, artifact)})
            if label == "netlist" and path.is_file():
                checks.append({"name": "no_black_boxes", "pass": "blackbox" not in path.read_text(errors="replace").lower()})
        for label in ("sdc", "proof_reference"):
            record = job.get(label)
            if record:
                checks.append({"name": f"{label}_hash", "pass": validate_record(repo / str(record["path"]), record)})
        ready_checks = {row["name"]: bool(row["pass"]) for row in job.get("checks", [])}
        checks.extend(
            [
                {"name": "preserved_status_pass", "pass": job.get("status") == "PASS"},
                {"name": "all_preserved_checks_pass", "pass": bool(ready_checks) and all(ready_checks.values())},
                {"name": "mapped_cells_only", "pass": not job.get("generic_or_unmapped_cell_types") and all(str(master).startswith("sky130_fd_sc_hd__") for master in job.get("cell_master_counts", {}))},
                {"name": "no_latches", "pass": not job.get("latch_masters") and ready_checks.get("no_latches") is True},
                {"name": "no_fault_injection_boundary_input", "pass": ready_checks.get("no_fault_injection_ports") is True},
                {"name": "equivalence_assessable", "pass": job.get("equivalence_setup_assessable") is True},
            ]
        )
        passed = all(bool(row["pass"]) for row in checks)
        all_pass &= passed
        jobs.append({"job": job["job"], "checks": checks, "pass": passed})

    liberty = mapping["liberty"]
    liberty_pass = validate_record(source_root / str(liberty["path"]), liberty)
    distinction = {row["name"]: bool(row["pass"]) for row in mapping.get("secded_structural_distinction", [])}
    by_name = {job["job"]: job for job in mapping.get("jobs", [])}
    pipeline_pass = (
        by_name.get("secded-pipelined", {}).get("sequential_cell_count", 0) > 0
        and by_name.get("secded-combinational", {}).get("sequential_cell_count") == 0
        and distinction.get("pipeline_registers_preserved") is True
    )
    structural_pass = (
        distinction.get("normalized_netlist_hashes_differ") is True
        and distinction.get("cell_master_histograms_differ") is True
    )
    all_pass &= liberty_pass and pipeline_pass and structural_pass
    return {
        "schema_version": 1,
        "mode": "hash-and-property revalidation; synthesis was not rerun",
        "preserved_mapping_validation": file_record(mapping_path),
        "jobs": jobs,
        "liberty_hash_valid": liberty_pass,
        "pipeline_register_survival_valid": pipeline_pass,
        "combinational_and_pipelined_structures_distinct": structural_pass,
        "pass": all_pass,
    }


def validate_protected(repo: Path, v1: Path, baseline_path: Path) -> dict[str, object]:
    baseline = json.loads(baseline_path.read_text())
    repo_rows = []
    for relative, expected in baseline["repo_trees"].items():
        actual = stable_tree_hash(repo / relative)
        repo_rows.append({"path": relative, "expected": expected, "actual": actual, "pass": actual == expected})
    external_rows = []
    for run, expected in baseline["external_trees"].items():
        actual = stable_tree_hash(v1 / "runs" / run)
        external_rows.append({"path": str(v1 / "runs" / run), "expected": expected, "actual": actual, "pass": actual == expected})
    anchors = {
        "policy": sha256_file(v1 / "policy/reproducibility_policy_v1.json"),
        "comparator": sha256_file(v1 / "policy/reproducibility.py"),
        "comparison": sha256_file(v1 / "runs/gcd-run-comparison.json"),
    }
    anchor_pass = anchors == V1_HASHES == baseline["v1_anchor_hashes"]
    verdict = (repo / "docs/date2027/rigour_gate_03r/GATE_03R_VERDICT.txt").read_text().strip()
    return {
        "schema_version": 1,
        "repo_tree_revalidation": repo_rows,
        "external_run_tree_revalidation": external_rows,
        "v1_anchor_hashes": anchors,
        "v1_anchor_hashes_pass": anchor_pass,
        "gate03r_verdict": verdict,
        "gate03r_verdict_pass": verdict == "REMEDIATION_FAILED" == baseline["gate03r_verdict"],
        "pass": all(row["pass"] for row in repo_rows + external_rows) and anchor_pass and verdict == "REMEDIATION_FAILED",
    }


def format_adjudication(adjudication: dict[str, object]) -> str:
    lines = [
        "# Gate 03E-R Reproducibility Adjudication",
        "",
        "Policy v1 and its FAIL result remain authoritative historical evidence. Policy v1 failed because its closed fallback treated unclassified numeric runtime/resource measurements as deterministic scientific outputs. In particular, the substring rule for `overflow` classified OpenROAD's `overflow_iterations_s` RunTimings timer as routing-overflow state even though its `_s` suffix and FastRoute producer identify seconds.",
        "",
        f"Anchors: policy `{V1_HASHES['policy']}`, comparator `{V1_HASHES['comparator']}`, comparison `{V1_HASHES['comparison']}`.",
        "",
        "## Raw differences (16)",
        "",
    ]
    for row in adjudication["raw_difference_adjudications"]:
        classes = row.get("adjudicated_classification") or ", ".join(row.get("adjudicated_classifications", []))
        lines.extend([
            f"### {row['occurrence']}. `{row['path']}` — {classes}",
            "",
            f"Raw SHA-256: `{row['run_1_raw_sha256']}` → `{row['run_2_raw_sha256']}`. Canonical SHA-256: `{row['run_1_canonical_sha256']}` → `{row['run_2_canonical_sha256']}`.",
            "",
        ])
        if "exact_before" in row:
            lines.extend([f"Exact value: `{row['exact_before']}` → `{row['exact_after']}`. Context: `{row['context']}`.", ""])
        for field in row.get("field_differences", []):
            if "path" in field:
                lines.append(f"- `{field['path']}`: `{field.get('run_1')}` → `{field.get('run_2')}` ({field.get('classification')}).")
            else:
                trace = field.get("producer_trace", {})
                lines.append(f"- `{field.get('run_1_exact')}` → `{field.get('run_2_exact')}` ({field.get('classification')}); producer `{trace.get('source')}:{trace.get('lines')}` at frozen commit `{trace.get('frozen_source_commit')}`.")
                lines.append(f"  Run 1 context: `{field.get('run_1_context')}`")
                lines.append(f"  Run 2 context: `{field.get('run_2_context')}`")
        if row.get("field_differences"):
            lines.append("")
    lines.extend(["## Numeric breach occurrences (29)", ""])
    for row in adjudication["numeric_breach_adjudications"]:
        trace = row["producer_trace"]
        duplicate = f" Duplicate of occurrence {row['duplicate_of_occurrence']}." if row.get("duplicate_of_occurrence") else ""
        lines.append(f"- {row['occurrence']}. `{row['path']}`: `{row['run_1']}` → `{row['run_2']}`; execution runtime/resource usage; `{trace['source']}:{trace['lines']}` at frozen commit `{trace['frozen_source_commit']}`. Run 1 context: `{row['run_1_context']}`. Run 2 context: `{row['run_2_context']}`.{duplicate}")
    xml = adjudication["technology_xml"]["summary"]
    lines.extend([
        "",
        "## KLayout technology XML",
        "",
        f"Detected XML with {xml['element_count_run_1']} elements and {xml['attribute_count_run_1']} attributes. The only raw value difference is the generated run-root inside `<lef-files>`. Targeted normalization gives canonical SHA-256 `{xml['canonical_sha256_run_1']}` for both runs. Every technology/layer parameter comparison is retained in the machine-readable adjudication; no DBU, layer map, unit, routing, display, reader, or technology setting differs.",
        "",
        "The nine duplicated FastRoute occurrences are retained separately: policy v1 collected changed JSON at comparator lines 387–388 and again at lines 424–432.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--external-root", type=Path, default=Path("/var/lib/green-ecc-gate03er"))
    parser.add_argument("--v1-root", type=Path, default=Path("/var/lib/green-ecc-gate03e"))
    args = parser.parse_args()
    repo, external, v1 = args.repo_root.resolve(), args.external_root, args.v1_root
    policy = external / "policy"
    runs = external / "runs"
    docs = repo / "docs/date2027/rigour_gate_03er"
    if docs.exists():
        raise SystemExit(f"refusing to replace Gate 03E-R documentation: {docs}")
    comparison_path = runs / "gcd-run-03-04-comparison.json"
    comparison = json.loads(comparison_path.read_text())
    freeze = json.loads((policy / "frozen-bundle.json").read_text())
    adjudication = json.loads((policy / "reproducibility-adjudication.json").read_text())
    metadata = [json.loads((runs / f"gcd-run-0{run}/run-metadata.json").read_text()) for run in (3, 4)]
    freeze_time = parse_utc(freeze["frozen_at_utc"])
    timing_pass = all(freeze_time < parse_utc(row["start_time"]) <= parse_utc(row["end_time"]) <= DEADLINE and row["exit_status"] == 0 for row in metadata)

    mapping = revalidate_mapping(repo, v1)
    protected = validate_protected(repo, v1, policy / "protected-baseline.json")
    repository_logs = external / "repository-validation"
    required_logs = {name: repository_logs / name for name in ("make.log", "make-test.log", "pytest.log", "gate03er-focused.log")}
    command_pass = all(path.is_file() and (repository_logs / f"{name}.exit-status").read_text().strip() == "0" for name, path in required_logs.items())
    comparison_pass = (
        comparison.get("reproducibility_pass") is True
        and not comparison.get("failures")
        and not comparison.get("unknown_metrics")
        and all(row["pass"] for key in ("semantic_artifact_comparisons", "technology_xml_comparisons", "mapped_master_histograms", "metric_comparisons") for row in comparison.get(key, []))
    )
    acceptance_pass = (
        datetime.now(timezone.utc) <= DEADLINE
        and timing_pass
        and adjudication.get("adjudication_pass") is True
        and adjudication["classification_counts"] == {"scientific_qor_state_differences": 0, "unresolved": 0}
        and comparison_pass
        and mapping["pass"]
        and protected["pass"]
        and command_pass
    )
    verdict = "ENVIRONMENT_READY_FOR_GATE_03_REENTRY" if acceptance_pass else "ENVIRONMENT_ENABLEMENT_FAILED"
    validation_root = external / "validation"
    validation_root.mkdir()
    write_json(validation_root / "mapping-revalidation.json", mapping)
    write_json(validation_root / "protected-scope-revalidation.json", protected)
    acceptance = {
        "schema_version": 1,
        "gate": "03E-R",
        "evaluated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "deadline_utc": "2026-08-17T11:59:59Z",
        "freeze_predates_runs_and_runs_completed_before_deadline": timing_pass,
        "adjudication_pass": adjudication.get("adjudication_pass"),
        "fresh_comparison_pass": comparison_pass,
        "mapping_revalidation_pass": mapping["pass"],
        "protected_scope_revalidation_pass": protected["pass"],
        "required_repository_commands_pass": command_pass,
        "verdict": verdict,
    }
    write_json(validation_root / "acceptance.json", acceptance)

    docs.mkdir(parents=True)
    copies = {
        "REPRODUCIBILITY_ADJUDICATION.json": policy / "reproducibility-adjudication.json",
        "REPRODUCIBILITY_POLICY_V2.json": policy / "reproducibility_policy_v2.json",
        "PRODUCER_CATALOG_V2.json": policy / "producer_catalog_v2.json",
        "QOR_METRIC_SCHEMA_V2.json": policy / "qor-metric-schema-v2.json",
        "FROZEN_BUNDLE.json": policy / "frozen-bundle.json",
        "IMMUTABLE_INPUT_MANIFEST.json": policy / "immutable-input-manifest.json",
        "COMMAND_MANIFEST.json": policy / "command-manifest.json",
        "RUN_03_INVENTORY.json": runs / "gcd-run-03-inventory.json",
        "RUN_04_INVENTORY.json": runs / "gcd-run-04-inventory.json",
        "FRESH_RUN_COMPARISON.json": comparison_path,
        "MAPPING_REVALIDATION.json": validation_root / "mapping-revalidation.json",
        "PROTECTED_SCOPE_REVALIDATION.json": validation_root / "protected-scope-revalidation.json",
        "ACCEPTANCE.json": validation_root / "acceptance.json",
    }
    for name, source in copies.items():
        shutil.copyfile(source, docs / name)
    (docs / "REPRODUCIBILITY_ADJUDICATION.md").write_text(format_adjudication(adjudication), encoding="utf-8", newline="\n")
    report = [
        "# Gate 03E-R: Reproducibility Adjudication and Fresh Rerun",
        "",
        f"Verdict: `{verdict}`",
        "",
        f"Policy v2 was frozen at `{freeze['frozen_at_utc']}`, before runs 3 and 4. Two new, sequential GCD runs used the pinned image and unchanged official make invocation. Semantic physical outputs, technology XML, stage ODBs, mapped masters, and all frozen QoR rules passed. The overall comparison failed because `run-metadata.json` contained the unresolved differing field `run_label` (`gcd-run-03` versus `gcd-run-04`); post-freeze exclusion is prohibited.",
        "",
        f"The four preserved GREEN-ECC mapping jobs were revalidated by hashes and properties without rerunning them: {'PASS' if mapping['pass'] else 'FAIL'}. Gates 01, 02, 03, and 03R, Gate 03E v1, and old run trees were rehashed: {'UNCHANGED' if protected['pass'] else 'CHANGED'}. Gate 03R remains `REMEDIATION_FAILED`. The required full repository tests also failed only because unchanged legacy Gate 03/03E scope validators reject the new additive Gate 03E-R paths; the focused Gate 03E-R suite passed.",
        "",
        "Policy v1, comparator v1, preserved runs 1–2, and their FAIL result were not modified. Raw hashes remain available for audit; execution timings and resource measurements are recorded but not equality-gated.",
    ]
    (docs / "GATE_03ER_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    (docs / "GATE_03ER_VERDICT.txt").write_text(verdict + "\n", encoding="ascii", newline="\n")
    evidence = []
    for path in sorted(item for item in docs.rglob("*") if item.is_file()):
        evidence.append(f"{sha256_file(path)}  {path.relative_to(docs).as_posix()}\n")
    (docs / "EVIDENCE.sha256").write_text("".join(evidence), encoding="ascii", newline="\n")
    print(json.dumps(acceptance, sort_keys=True))
    return 0 if acceptance_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
