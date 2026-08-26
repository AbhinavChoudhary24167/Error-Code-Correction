#!/usr/bin/env python3
"""Prepare the immutable, result-blind Gate 04 experiment freeze."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "docs" / "date2027" / "rigour_gate_04"
AUTHORIZATION = Path.home() / ".codex" / "attachments" / "2b1b4341-4f44-4f84-988c-e3d41cbf7945" / "pasted-text.txt"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_json(relative: str) -> object:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def source_hashes(paths: list[str]) -> str:
    return ";".join(f"{path}={sha256(ROOT / path)}" for path in paths)


def physical_status(implementation_id: str) -> tuple[str, str, str]:
    if implementation_id in {
        "secded-rtl-combinational-72-64-v1",
        "hsiao-generated-combinational-72-64-v1",
    }:
        return "MANDATORY_PHYSICAL_CANDIDATE", "eligible", "direct exact synthesizable encoder and decoder"
    if implementation_id == "shortened-bch-78-64-t2-v1-reference-decoder":
        return (
            "REPRESENTED_BY_EXACT_RTL_OVERLAY",
            "eligible_via_overlay",
            "reference decoder is not RTL; exact Gate-03R RTL overlay is a mandatory physical candidate",
        )
    reasons = {
        "forge-hotspot-8-4-v1-archived-table-decoder": "not a 64-bit payload implementation and no eligible synthesizable encoder/decoder pair",
        "forge-spatial-hotspot-72-64-v1-archived-table-decoder": "archived table decoder has no eligible synthesizable encoder/decoder pair",
        "forge-sram-portfolio-72-64-v1-geometry-filtered-joint-archived-table-decoder": "archived table decoder has no eligible synthesizable encoder/decoder pair",
        "forge-sram-portfolio-72-64-v1-spatial-hotspot-joint-archived-table-decoder": "archived table decoder has no eligible synthesizable encoder/decoder pair",
        "odd-column-secded-4-8-archived-table-decoder": "not a 64-bit payload implementation and no eligible synthesizable encoder/decoder pair",
        "odd-column-secded-64-72-archived-table-decoder": "archived table decoder has no eligible synthesizable encoder/decoder pair",
        "primitive-bch-63-51-t2-v1-reference-decoder": "not a 64-bit payload implementation and reference decoder has no eligible synthesizable RTL pair",
        "safeforge-robust-72-64-mapping-v1-archived-table-decoder": "archived table decoder has no eligible synthesizable encoder/decoder pair",
        "safeforge-robust-8-4-v1-archived-table-decoder": "not a 64-bit payload implementation and no eligible synthesizable encoder/decoder pair",
        "shortened-bch-71-64-t1-v1-reference-decoder": "reference decoder has no Gate-03R exact synthesizable RTL overlay",
        "shortened-bch-85-64-t3-v1-reference-decoder": "reference decoder has no Gate-03R exact synthesizable RTL overlay",
    }
    return "EXCLUDED_FROM_GATE04_PHYSICAL", "ineligible_physical", reasons[implementation_id]


def candidate_matrix(eligible: dict[str, object], catalog: dict[str, object]) -> list[dict[str, object]]:
    catalog_by_id = {record["implementation_id"]: record for record in catalog["candidates"]}
    rows: list[dict[str, object]] = []
    for record in (item for item in eligible["records"] if item["eligibility"] == "ELIGIBLE"):
        implementation_id = record["implementation_id"]
        status, flow_eligibility, reason = physical_status(implementation_id)
        physical = catalog_by_id.get(implementation_id)
        rows.append(
            {
                "mathematical_code_id": record["mathematical_code_id"],
                "implementation_id": implementation_id,
                "architecture_id": record["hardware_structure_id"],
                "n": record["n"], "k": record["k"], "r": record["r"],
                "canonical_identity_hash": record["canonical_identity_hash"],
                "exact_rtl_hashes": source_hashes(physical["rtl"]) if physical else "UNAVAILABLE",
                "rtl_paths": ";".join(physical["rtl"]) if physical else "UNAVAILABLE",
                "encoder_available": bool(physical and physical["encoder"]),
                "decoder_available": bool(physical and physical["decoder"]),
                "interface_contract": "independent encoder/decoder; 64 useful bits; II=1" if physical else "UNAVAILABLE",
                "latency_cycles": physical["latency_cycles"] if physical else "UNAVAILABLE",
                "initiation_interval": physical["initiation_interval"] if physical else "UNAVAILABLE",
                "exact_verification": physical["exact_verification"] if physical else "Gate-02 mathematical eligibility only",
                "synthesis_eligibility": flow_eligibility,
                "full_flow_eligibility": flow_eligibility,
                "exclusion_or_binding_reason": reason,
                "evidence_class": "SIMULATED" if physical else "DERIVED",
                "gate02_eligibility": record["eligibility"],
                "gate04_status": status,
            }
        )

    for implementation_id in (
        "secded-rtl-pipelined-72-64-v1",
        "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1",
    ):
        record = catalog_by_id[implementation_id]
        rows.append(
            {
                "mathematical_code_id": record["mathematical_code_id"],
                "implementation_id": implementation_id,
                "architecture_id": record["architecture_id"],
                "n": record["n"], "k": record["k"], "r": record["r"],
                "canonical_identity_hash": record["canonical_identity_hash"],
                "exact_rtl_hashes": source_hashes(record["rtl"]),
                "rtl_paths": ";".join(record["rtl"]),
                "encoder_available": True, "decoder_available": True,
                "interface_contract": "independent encoder/decoder; 64 useful bits; II=1",
                "latency_cycles": record["latency_cycles"],
                "initiation_interval": record["initiation_interval"],
                "exact_verification": record["exact_verification"],
                "synthesis_eligibility": "eligible", "full_flow_eligibility": "eligible",
                "exclusion_or_binding_reason": record["supplemental_lineage"],
                "evidence_class": "SIMULATED", "gate02_eligibility": "SUPPLEMENTAL_EXACT_PHYSICAL_OVERLAY",
                "gate04_status": "MANDATORY_PHYSICAL_CANDIDATE",
            }
        )

    for implementation_id in ("boundary-reference-72-64-v1", "boundary-reference-78-64-v1"):
        record = catalog_by_id[implementation_id]
        rows.append(
            {
                "mathematical_code_id": record["mathematical_code_id"],
                "implementation_id": implementation_id,
                "architecture_id": record["architecture_id"],
                "n": record["n"], "k": record["k"], "r": record["r"],
                "canonical_identity_hash": "NOT_APPLICABLE",
                "exact_rtl_hashes": source_hashes(record["rtl"]),
                "rtl_paths": ";".join(record["rtl"]),
                "encoder_available": False, "decoder_available": False,
                "interface_contract": "same registered ports; boundary-only pass mapping; II=1",
                "latency_cycles": 1, "initiation_interval": 1,
                "exact_verification": "structural boundary reference",
                "synthesis_eligibility": "eligible", "full_flow_eligibility": "eligible",
                "exclusion_or_binding_reason": "width-matched common-boundary de-embedding reference",
                "evidence_class": "SYNTHESIZED", "gate02_eligibility": "NOT_APPLICABLE",
                "gate04_status": "BOUNDARY_REFERENCE",
            }
        )
    return rows


def flow_matrix(contract: dict[str, object], catalog: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    candidate_order = contract["physical_experiment"]["candidate_ids"] + contract["physical_experiment"]["reference_ids"]
    by_id = {item["implementation_id"]: item for item in catalog["candidates"]}
    for implementation_id in candidate_order:
        item = by_id[implementation_id]
        short = {
            "secded-rtl-combinational-72-64-v1": "secded-comb",
            "secded-rtl-pipelined-72-64-v1": "secded-pipe",
            "hsiao-generated-combinational-72-64-v1": "hsiao",
            "shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1": "bch78",
            "boundary-reference-72-64-v1": "boundary72",
            "boundary-reference-78-64-v1": "boundary78",
        }[implementation_id]
        for clock in contract["physical_experiment"]["clock_periods_ns"]:
            clock_label = f"{int(clock)}ns"
            for seed in contract["physical_experiment"]["physical_seeds"]:
                run_id = f"{short}-{clock_label}-seed{seed}-attempt1"
                rows.append(
                    {
                        "run_id": run_id,
                        "implementation_id": implementation_id,
                        "kind": item["kind"],
                        "design_top": item["top"],
                        "config": item["config"],
                        "n": item["n"], "k": item["k"],
                        "clock_period_ns": f"{clock:.1f}",
                        "physical_seed": seed,
                        "gpl_random_seed": seed, "grt_seed": seed, "or_seed": seed,
                        "attempt": 1,
                        "run_directory": f"/var/lib/green-ecc-gate04/runs/{run_id}",
                        "expected_stages": "synth;floorplan;place;cts;route;extraction;postroute_sta;gds;def;netlist;sdc;spef",
                        "activity_traces": "no_error;single_error;double_error",
                        "status": "PLANNED",
                        "exit_status": "UNAVAILABLE",
                        "start_time_utc": "UNAVAILABLE",
                        "end_time_utc": "UNAVAILABLE",
                        "failure_reason": "",
                    }
                )
    return rows


def protected_manifest() -> dict[str, object]:
    roots = [
        "docs/date2027/rigour_gate_03", "docs/date2027/rigour_gate_03e",
        "docs/date2027/rigour_gate_03er", "docs/date2027/rigour_gate_03es",
        "docs/date2027/rigour_gate_03r", "asic/rtl",
        "green_ecc_physical_simulation/registry", "green_ecc_physical_simulation/rtl",
    ]
    paths: list[Path] = []
    for relative in roots:
        paths.extend(path for path in (ROOT / relative).rglob("*") if path.is_file())
    paths.extend(ROOT / item for item in ("ecc_selector.py", "architecture/selection.py"))
    records = [
        {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in sorted(set(paths))
    ]
    return {"schema_version": 1, "algorithm": "sha256-raw-bytes", "file_count": len(records), "files": records}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    contract = load_json("scripts/gate04/contract_v1.json")
    catalog = load_json("scripts/gate04/candidate_catalog_v1.json")
    eligible = load_json("docs/date2027/rigour_gate_03/ELIGIBLE_IMPLEMENTATION_FREEZE.json")
    eligible_records = [item for item in eligible["records"] if item["eligibility"] == "ELIGIBLE"]
    if len(eligible["eligible_implementation_ids"]) != 14 or len(eligible_records) != 14:
        raise SystemExit("Gate-02 eligible freeze does not contain exactly 14 records")
    if not AUTHORIZATION.is_file():
        raise SystemExit(f"authorization missing: {AUTHORIZATION}")

    candidate_rows = candidate_matrix(eligible, catalog)
    candidate_fields = list(candidate_rows[0])
    write_csv(out / "ASIC_CANDIDATE_MATRIX.csv", candidate_fields, candidate_rows)

    flow_rows = flow_matrix(contract, catalog)
    if sum(row["kind"] == "candidate" for row in flow_rows) != 40 or len(flow_rows) != 60:
        raise SystemExit("flow matrix is not 40 candidate plus 20 reference flows")
    write_csv(out / "FLOW_RUN_MATRIX.csv", list(flow_rows[0]), flow_rows)

    gate04_sources = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "scripts/gate04").rglob("*")
        if path.is_file()
    }
    gate04_sources.add("tests/python/test_gate04_contract.py")
    input_paths = sorted(
        {
            *gate04_sources,
            "docs/date2027/rigour_gate_03/ELIGIBLE_IMPLEMENTATION_FREEZE.json",
            *[f"scripts/gate04/configs/{item['config']}" for item in catalog["candidates"]],
            *[path for item in catalog["candidates"] for path in item["rtl"]],
            *[item["exact_verification"] for item in catalog["candidates"] if item["exact_verification"] != "NOT_APPLICABLE"],
        }
    )
    missing = [path for path in input_paths if not (ROOT / path).is_file()]
    if missing:
        raise SystemExit(f"freeze input files missing: {missing}")
    identity_manifest = {
        "schema_version": 1,
        "algorithm": "sha256-raw-bytes",
        "files": [
            {"path": path, "bytes": (ROOT / path).stat().st_size, "sha256": sha256(ROOT / path)}
            for path in input_paths
        ],
    }
    write_json(out / "PRE_FLOW_IDENTITY_MANIFEST.json", identity_manifest)
    write_json(out / "STARTING_PROTECTED_BYTE_MANIFEST.json", protected_manifest())

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    write_json(
        out / "environment_manifest.json",
        {
            "schema_version": 1,
            "repository_head": head,
            "authorization_path": str(AUTHORIZATION),
            "authorization_sha256": sha256(AUTHORIZATION),
            "authorization_basis": contract["authorization_basis"],
            "prior_formal_verdicts": contract["formal_prior_gate_verdicts"],
            "orfs_git_commit": contract["technology"]["orfs_git_commit"],
            "container_image": contract["technology"]["container_image"],
            "platform": contract["technology"]["platform"],
            "corner": contract["technology"]["corner"],
            "operating_system_scope": "Ubuntu WSL2 Docker execution; Windows repository mounted read-only only at external freeze",
            "evidence_class": "DERIVED",
        },
    )
    write_json(
        out / "command_manifest.json",
        {
            "schema_version": 1,
            "preflow": [
                "python3 scripts/gate04/prepare_freeze.py",
                "python3 scripts/gate04/validate_preflow.py",
                "sudo bash scripts/gate04/freeze_gate04.sh",
            ],
            "per_flow": "sudo bash /var/lib/green-ecc-gate04/policy/repo_snapshot/scripts/gate04/run_flow.sh RUN_ID IMPLEMENTATION_ID CONFIG CLOCK_NS SEED TOP N K KIND",
            "matrix": "sudo bash /var/lib/green-ecc-gate04/policy/repo_snapshot/scripts/gate04/run_matrix.sh",
            "prohibited": ["GCD runs 7-8", "commit", "push", "production RTL edits", "same-directory retry"],
        },
    )

    experiment_md = f"""# GREEN-ECC Gate 04 experiment freeze

Status: **RESULT-BLIND FREEZE PREPARED**

Authorization basis: `{contract['authorization_basis']}`. Gate 03E-R and Gate 03E-S remain formal failures; this freeze neither edits nor reinterprets them.

## Mandatory physical matrix

- Candidates: {', '.join(f'`{item}`' for item in contract['physical_experiment']['candidate_ids'])}
- Periods: 10.0 ns and 5.0 ns.
- Paired physical seeds: 11, 29, 47, 71, 101.
- Candidate flows: 40; width-matched boundary references: 20; total planned full flows: 60.
- Physical seed control: `GPL_RANDOM_SEED`, `GRT_SEED`, and `OR_SEED` are all assigned the matrix seed. The pinned-source proof is captured by the external freeze.
- Full official flow: synthesis, floorplan, placement, CTS, routing, extraction, post-route STA, final ODB/GDS/DEF/netlist/SDC/SPEF.

## Activity and power

Each no-error, single-error, and double-error trace uses the same frozen SplitMix64 sequence of exactly 100,000 useful 64-bit operations. Fault positions use the frozen width-normalized mapping in `contract_v1.json`. Post-route OpenSTA reads primary-input VCD activity, propagates it through the extracted design, reports direct annotation coverage and unannotated pins, and reports tool-estimated power. No field-rate average, silicon measurement, SRAM-macro energy, or total-system-energy claim is permitted.

## Statistics and hypotheses

All seed values, median, IQR, extrema, paired differences, effect sizes, and paired percentile-bootstrap 95% intervals are required. Bootstrap seed is 474104 with 20,000 resamples. The 5% materiality threshold and H1-H4 tests are frozen verbatim in `contract_v1.json` before any candidate flow.

## Result-blindness

The candidate matrix, flow matrix, wrapper/latency/fairness rules, scenario factors, evidence vocabulary, calculation rules, seed controls, hypotheses, and source-byte hashes are frozen before flow execution. A flow is never silently retried; another attempt requires a new directory and visible row. A missing mandatory candidate, seed mechanism, full stage, activity result, equivalence check, or provenance link fails closed.
"""
    (out / "EXPERIMENT_FREEZE.md").write_text(experiment_md, encoding="utf-8", newline="\n")

    fairness_md = """# Gate 04 fairness contract

All candidates carry 64 useful bits per accepted operation at initiation interval one. Encoder and decoder channels are independent, share the same registered boundary policy, receive identical useful schedules, use the same fractional I/O delays and output load, and expose no backpressure, test mux, or synthesizable fault-injection port. A common registered codeword-echo output keeps every decoder input-boundary bit physically observable in candidates and references; it is wrapper overhead, not codec functionality. Reset is a synchronous active-low boundary reset asserted for six clocks; invalid pipeline contents are ignored until valid emerges.

Combinational SECDED, Hsiao, exact BCH, and width-matched references have one boundary cycle. The pipelined same-code SECDED retains its two internal encoder/decoder stages and has three total boundary-to-boundary cycles. It must not be retimed into the combinational architecture.

The 72-bit and 78-bit boundary-only references are separately placed and routed at every clock and paired seed. Codec-only estimates may be derived by explicit reference subtraction, with negative or unsupported decompositions reported unresolved. Pipeline registers, parity/storage bits, wrapper overhead, and codec logic remain separate. Memory macro, controller, metadata, scrub, and migration costs are unresolved unless independent common evidence exists.

All power is post-route OpenSTA tool estimation from identical input activity traces. Direct VCD annotation and unannotated pin counts are retained; propagation is not mislabeled as measured internal switching. Physical adjacency, Qcrit, fault probabilities, scrub intervals, and workload distributions are assumptions.
"""
    (out / "FAIRNESS_CONTRACT.md").write_text(fairness_md, encoding="utf-8", newline="\n")
    print(f"GATE04_PREPARED candidates={len(candidate_rows)} planned_flows={len(flow_rows)} out={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
