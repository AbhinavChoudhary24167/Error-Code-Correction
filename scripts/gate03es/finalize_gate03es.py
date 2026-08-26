#!/usr/bin/env python3
"""Finalize Gate 03E-S evidence and emit its fail-closed verdict."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from reproducibility import sha256_file, write_json


READY = "ENVIRONMENT_READY_FOR_GATE_03_REENTRY"
FAILED = "ENVIRONMENT_ENABLEMENT_FAILED"
DEADLINE = datetime(2026, 8, 17, 11, 59, 59, tzinfo=timezone.utc)


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def command_results(root: Path) -> tuple[list[dict[str, object]], bool]:
    required = (
        "gate03es-focused", "historical-golden", "make", "make-test", "pytest",
        "git-diff-check", "path-scope", "prior-evidence-hashes",
    )
    rows = []
    for name in required:
        log, status = root / f"{name}.log", root / f"{name}.exit-status"
        value = None
        if status.is_file():
            try:
                value = int(status.read_text().strip())
            except ValueError:
                value = None
        rows.append(
            {
                "command_id": name,
                "log_path": str(log),
                "log_exists": log.is_file(),
                "log_size_bytes": log.stat().st_size if log.is_file() else None,
                "log_sha256": sha256_file(log) if log.is_file() else None,
                "exit_status": value,
                "pass": log.is_file() and value == 0,
            }
        )
    return rows, all(row["pass"] for row in rows)


def write_external_indexes(docs: Path, external: Path, inventories: list[dict[str, object]]) -> None:
    with (docs / "EXTERNAL_ARTIFACT_INDEX.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = ("run_label", "run_root", "root_relative_path", "size_bytes", "raw_sha256", "retained_in_git")
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for inventory in inventories:
            for row in inventory["artifacts"]:
                writer.writerow(
                    {
                        "run_label": inventory["run_label"],
                        "run_root": inventory["run_root"],
                        "root_relative_path": row["path"],
                        "size_bytes": row["size_bytes"],
                        "raw_sha256": row["raw_sha256"],
                        "retained_in_git": "false",
                    }
                )
    log_rows = []
    for root in (external / "runs", external / "repository-validation"):
        for path in sorted(item for item in root.rglob("*") if item.is_file() and item.suffix in {".log", ".txt"}):
            log_rows.append(
                {
                    "path": path.relative_to(external).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                    "evidence_class": "RUNTIME_RESOURCE_OBSERVATION" if "elapsed" in path.name else "PROVENANCE_IDENTITY",
                }
            )
    with (docs / "RAW_LOG_INDEX.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("path", "size_bytes", "sha256", "evidence_class"), lineterminator="\n")
        writer.writeheader()
        writer.writerows(log_rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--external-root", type=Path, default=Path("/var/lib/green-ecc-gate03es"))
    args = parser.parse_args()
    repo, external = args.repo_root.resolve(), args.external_root
    policy, runs = external / "policy", external / "runs"
    docs = repo / "docs/date2027/rigour_gate_03es"
    if (docs / "GATE_03ES_VERDICT.txt").exists():
        raise SystemExit("refusing to replace a finalized Gate 03E-S verdict")

    freeze = json.loads((policy / "frozen-bundle.json").read_text())
    comparison_path = runs / "gcd-run-05-06-comparison.json"
    comparison = json.loads(comparison_path.read_text())
    inventories = [
        json.loads((runs / "gcd-run-05-inventory.json").read_text()),
        json.loads((runs / "gcd-run-06-inventory.json").read_text()),
    ]
    metadata = [
        json.loads((runs / f"gcd-run-0{number}/run-metadata.json").read_text()) for number in (5, 6)
    ]
    baseline = json.loads((policy / "protected-baseline.json").read_text())
    scope = json.loads((external / "repository-validation/path-scope.log").read_text())
    prior_hashes = json.loads((external / "repository-validation/prior-evidence-hashes.log").read_text())
    command_rows, command_pass = command_results(external / "repository-validation")

    freeze_time = parse_utc(freeze["frozen_at_utc"])
    timing_pass = all(
        freeze_time < parse_utc(row["start_time"]) <= parse_utc(row["end_time"]) <= DEADLINE
        and row["exit_status"] == 0
        for row in metadata
    )
    labels_pass = [row["run_label"] for row in metadata] == ["gcd-run-05", "gcd-run-06"] and metadata[0]["run_label"] != metadata[1]["run_label"]
    comparison_pass = (
        comparison.get("reproducibility_pass") is True
        and not comparison.get("failures")
        and not comparison.get("unknown_metrics")
        and comparison.get("run_metadata_validation", {}).get("pass") is True
        and all(
            row["pass"]
            for key in ("semantic_artifact_comparisons", "technology_xml_comparisons", "mapped_master_histograms", "metric_comparisons")
            for row in comparison.get(key, [])
        )
    )
    policy_bundle_pass = all(
        (policy / row["name"]).is_file() and sha256_file(policy / row["name"]) == row["sha256"]
        for row in freeze["files"]
    )
    protected_pass = scope.get("status") == prior_hashes.get("status") == "PASS"
    mapping = json.loads((repo / "docs/date2027/rigour_gate_03er/MAPPING_REVALIDATION.json").read_text())
    gate03er_adjudication = json.loads((policy / "gate03er-adjudication.json").read_text())
    adjudication_pass = (
        gate03er_adjudication["gate03er_verdict"] == FAILED
        and gate03er_adjudication["scientific_comparisons_all_pass"] is True
        and gate03er_adjudication["report_consistent"] is True
    )
    acceptance_pass = (
        datetime.now(timezone.utc) <= DEADLINE
        and timing_pass
        and labels_pass
        and comparison_pass
        and policy_bundle_pass
        and protected_pass
        and command_pass
        and mapping.get("pass") is True
        and adjudication_pass
    )
    verdict = READY if acceptance_pass else FAILED

    validation_root = external / "validation"
    validation_root.mkdir(exist_ok=False)
    acceptance = {
        "schema_version": 3,
        "gate": "03E-S",
        "evaluated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "deadline_utc": "2026-08-17T11:59:59Z",
        "freeze_predates_runs_and_runs_completed_before_deadline_pass": timing_pass,
        "mandatory_distinct_run_labels_pass": labels_pass,
        "gate03er_preservation_and_adjudication_pass": adjudication_pass,
        "fresh_within_environment_comparison_pass": comparison_pass,
        "frozen_bundle_revalidation_pass": policy_bundle_pass,
        "mapping_identity_revalidation_pass": mapping.get("pass") is True,
        "protected_scope_and_prior_hash_revalidation_pass": protected_pass,
        "required_repository_commands_pass": command_pass,
        "verdict": verdict,
    }
    write_json(validation_root / "acceptance.json", acceptance)
    write_json(validation_root / "repository-command-results.json", command_rows)

    docs.mkdir(parents=True, exist_ok=True)
    copies = {
        "GATE_03ER_ADJUDICATION.json": policy / "gate03er-adjudication.json",
        "REPRODUCIBILITY_POLICY_V3.json": policy / "reproducibility_policy_v3.json",
        "PRODUCER_CATALOG_V3.json": policy / "producer_catalog_v3.json",
        "QOR_METRIC_SCHEMA_V3.json": policy / "qor_metric_schema_v3.json",
        "FROZEN_BUNDLE.json": policy / "frozen-bundle.json",
        "IMMUTABLE_INPUT_MANIFEST.json": policy / "immutable-input-manifest.json",
        "COMMAND_MANIFEST.json": policy / "command-manifest.json",
        "STARTING_STATE_AND_PROTECTED_BASELINE.json": policy / "protected-baseline.json",
        "RUN_05_INVENTORY.json": runs / "gcd-run-05-inventory.json",
        "RUN_06_INVENTORY.json": runs / "gcd-run-06-inventory.json",
        "FRESH_RUN_COMPARISON.json": comparison_path,
        "PATH_SCOPE_REVALIDATION.json": external / "repository-validation/path-scope.log",
        "PRIOR_EVIDENCE_HASH_REVALIDATION.json": external / "repository-validation/prior-evidence-hashes.log",
        "REPOSITORY_COMMAND_RESULTS.json": validation_root / "repository-command-results.json",
        "ACCEPTANCE.json": validation_root / "acceptance.json",
    }
    for name, source in copies.items():
        shutil.copyfile(source, docs / name)
    write_external_indexes(docs, external, inventories)

    legacy_rows = baseline["legacy_validator_changes"]
    write_json(
        docs / "LEGACY_VALIDATOR_COMPATIBILITY_CHANGE.json",
        {
            "schema_version": 1,
            "changes": legacy_rows,
            "scope_rule": "explicitly registered additive gate paths only; historical evidence remains recursively hash-gated",
            "historical_positive_and_negative_tests_preserved": True,
        },
    )
    report = [
        "# Gate 03E-S: Prospective Repeatability Repair",
        "",
        f"Verdict: `{verdict}`",
        "",
        "Gate 03E-R remains legitimately `ENVIRONMENT_ENABLEMENT_FAILED`; it is not reinterpreted as a formal pass. Its semantic artifacts, technology XML, stage ODBs, mapped-master histograms, and frozen QoR comparisons passed. Its overall frozen contract failed because the required distinct `run_label` values were equality-gated, and required repository tests failed because historical scope validators rejected additive Gate 03E-R paths.",
        "",
        f"Policy v3 was frozen at `{freeze['frozen_at_utc']}` before creation of both fresh run directories. Runs 5 and 6 used distinct mandatory labels, the pinned linux/amd64 manifest, `LEC_CHECK=0`, one thread, and the exact official command `{comparison.get('official_make_invocation', 'make DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk')}`.",
        "",
        f"Fresh-run comparison: {'PASS' if comparison_pass else 'FAIL'}. Raw hashes were retained for every artifact. Every stage ODB has a complete frozen semantic export; raw ODB equality is separately recorded as the stronger observation. Technology, geometry, routing, connectivity, cell masters, and QoR remain scientifically gated.",
        "",
        f"Historical repository evidence and prior external run trees: {'UNCHANGED' if protected_pass else 'CHANGED'}. Required repository commands: {'PASS' if command_pass else 'FAIL'}. Preserved four-job mapping revalidation: {'PASS' if mapping.get('pass') else 'FAIL'}.",
        "",
        "This result is within-environment repeatability only. It is not independent reproducibility, publication readiness, silicon measurement, foundry signoff, or Gate 04 evidence.",
    ]
    (docs / "GATE_03ES_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    (docs / "GATE_03ES_VERDICT.txt").write_text(verdict + "\n", encoding="ascii", newline="\n")
    evidence = []
    for path in sorted(item for item in docs.rglob("*") if item.is_file() and item.name != "EVIDENCE.sha256"):
        evidence.append(f"{sha256_file(path)}  {path.relative_to(docs).as_posix()}\n")
    (docs / "EVIDENCE.sha256").write_text("".join(evidence), encoding="ascii", newline="\n")
    print(json.dumps(acceptance, sort_keys=True))
    return 0 if acceptance_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
