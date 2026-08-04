#!/usr/bin/env python3
"""Regenerate ICCAD #1723 architecture-aware evidence from one config."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from architecture.pipeline import run_architecture_dse


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "architecture_dse.example.json",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=ROOT / "reports" / "revision" / "iccad1723",
    )
    args = parser.parse_args()

    result = run_architecture_dse(args.config, args.outdir, repo_root=ROOT)
    reports = json.loads((args.outdir / "data" / "scenario_reports.json").read_text(encoding="utf-8"))
    topology = json.loads((args.outdir / "data" / "topology_comparison.json").read_text(encoding="utf-8"))
    polar = json.loads((args.outdir / "data" / "polar_ablation.json").read_text(encoding="utf-8"))
    differences = json.loads((args.outdir / "data" / "baseline_counterfactuals.json").read_text(encoding="utf-8"))
    score_diagnostics = json.loads(
        (args.outdir / "data" / "score_diagnostics.json").read_text(encoding="utf-8")
    )
    optimizer = json.loads(
        (args.outdir / "data" / "optimizer_validation.json").read_text(encoding="utf-8")
    )

    first_detail = next(iter(reports[0]["candidate_details"].values())) if reports else {}
    lines = [
        "# Reproducible ICCAD #1723 Revision Findings",
        "",
        f"- Operating scenarios: {result['summary']['scenario_count']}",
        f"- ECC families: {result['summary']['ecc_family_count']}",
        f"- ECC configurations: {result['summary']['ecc_configuration_count']}",
        f"- Candidate-scenario evaluations: {result['summary']['candidate_scenario_evaluations']}",
        f"- GREEN-ECC versus lookup differences: {len(differences)}",
        f"- Polar Pareto memberships: {sum(bool(item['pareto_member']) for item in polar)}",
        f"- Exact/legacy first-front agreement: {optimizer.get('agreement')}",
        "",
        "## Selection fabric",
        "",
        f"- Fixed physical container: {first_detail.get('layout', {}).get('container_bits', 'unavailable')} bits",
        f"- Configured topology MUX count: {first_detail.get('fabric', {}).get('mux_2to1_count_total', 'unavailable')} 2:1 cells",
        f"- Physical PPA characterized: {first_detail.get('fabric', {}).get('physical_metrics_characterized', False)}",
        "",
        "| Topology | Engines | 2:1 MUX cells | Max depth | Protected metadata bits | PPA status |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for item in topology:
        lines.append(
            f"| {item['topology']} | {item['engine_instances']} | {item['mux_2to1_count']} | "
            f"{item['mux_max_depth']} | {item['metadata_bits']} | {item['physical_ppa_status']} |"
        )
    lines.extend(["", "## Counterfactual selections", ""])
    if differences:
        for item in differences:
            lines.append(
                f"- `{item['scenario_id']}`: lookup `{item['fault_regime_lookup']}` -> GREEN-ECC "
                f"`{item['green_ecc']}`. {item['reason']}"
            )
    else:
        lines.append("- No differences were observed; no favorable case is asserted.")
    lines.extend(
        [
            "",
            "## Score conclusion",
            "",
        ]
    )
    for scenario_id, item in score_diagnostics.items():
        lines.append(
            f"- `{scenario_id}`: winners={item.get('argmax_by_score')}; "
            f"all-same={item.get('all_scores_same_winner')}; "
            f"component-wise winner={item.get('componentwise_dominant_candidate')}; "
            f"rank correlations={item.get('rank_correlations')}."
        )
    lines.extend(
        [
            "",
            "## Polar ablation",
            "",
        ]
    )
    for item in polar:
        lines.append(
            f"- `{item['scenario_id']}` / `{item['config_id']}`: Pareto={item['pareto_member']}; "
            f"FIT={item['fit']:.6g}; projected carbon={item['carbon_kg']:.6g} kg; "
            f"projected latency={item['latency_ns']:.6g} ns; "
            f"dominated by={item['dominated_by_on_legacy_fit_carbon_latency']}."
        )
    lines.extend(
        [
            "",
            "## Validation boundary",
            "",
            "The repository contains no Liberty file, synthesis report, STA report, SPICE deck, or measured MUX data. "
            "Accordingly, physical adaptive PPA and lifecycle-carbon advantages are not claimed.",
            "",
        ]
    )
    findings_path = args.outdir / "findings.md"
    findings_path.write_text("\n".join(lines), encoding="utf-8")
    manifest_path = args.outdir / "result_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"]["findings.md"] = hashlib.sha256(findings_path.read_bytes()).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
