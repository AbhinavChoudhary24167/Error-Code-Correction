"""Reproducible portfolio co-synthesis report pipeline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import time
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from .faults import load_fault_distribution
from .portfolio import co_synthesize_portfolio
from .portfolio_artifacts import render_portfolio_testbench, render_shared_portfolio_rtl
from .portfolio_figures import generate_portfolio_figures


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _validate(payload: Mapping[str, Any], schema: Path) -> None:
    Draft202012Validator(_read_json(schema)).validate(payload)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _commit(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def run_portfolio_cosynthesis(
    config_path: str | Path,
    outdir: str | Path,
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    source = Path(config_path)
    if not source.is_absolute():
        source = root / source
    output = Path(outdir)
    if not output.is_absolute():
        output = root / output
    output.mkdir(parents=True, exist_ok=True)
    config = _read_json(source)
    _validate(config, root / "schemas" / "portfolio-cosynthesis-config.schema.json")
    started = time.perf_counter()
    regimes = [
        (
            str(item["regime_id"]),
            float(item["probability"]),
            load_fault_distribution(item["fault_distribution"], repo_root=root),
        )
        for item in config["regimes"]
    ]
    validation = [
        load_fault_distribution(path, repo_root=root)
        for path in config.get("validation_distributions", [])
    ]
    shifted = [
        load_fault_distribution(path, repo_root=root)
        for path in config.get("shifted_distributions", [])
    ]
    portfolio = co_synthesize_portfolio(
        config,
        regimes,
        validation,
        shifted,
        repo_root=root,
    )
    _validate(portfolio, root / "schemas" / "ecc-portfolio.schema.json")
    _validate(portfolio["shared_graph"], root / "schemas" / "shared-xor-graph.schema.json")
    for code in portfolio["modes"]:
        _validate(code, root / "schemas" / "linear-code.schema.json")
    for report in portfolio["certificates"].values():
        _validate(report, root / "schemas" / "code-verification-report.schema.json")

    _write_json(output / "portfolio.json", portfolio)
    _write_json(output / "shared_xor_graph.json", portfolio["shared_graph"])
    _write_json(output / "distribution_shift.json", portfolio["distribution_shift"])
    _write_json(output / "safety_policy.json", portfolio["safety_policy"])
    _write_json(output / "baselines.json", portfolio["baselines"])
    _write_json(
        output / "synthesis_tool_comparison.json",
        portfolio["baselines"]["ordinary_combined_synthesis"],
    )
    scheduler_integration = {
        "schema_version": 1,
        "portfolio_id": portfolio["portfolio_id"],
        "status": portfolio["scheduler_integration_status"],
        "reason": "The scheduler requires physical per-access, leakage, latency, embodied, configuration, and migration costs. Only structural XOR proxies are available.",
        "generated_mode_ids": [code["code_id"] for code in portfolio["modes"]],
        "required_characterization": [
            "per-mode encoder/decoder energy",
            "shared-fabric leakage",
            "critical path latency",
            "configuration storage and integrity cost",
            "re-encoding energy and duration",
            "synthesis-tool separate-versus-shared baseline",
        ],
        "technology_specific_net_benefit": None,
    }
    _write_json(output / "scheduler_integration.json", scheduler_integration)
    for code in portfolio["modes"]:
        _write_json(output / "codes" / f"{code['code_id']}.json", code)
    for regime_id, report in portfolio["certificates"].items():
        _write_json(output / "certificates" / f"{regime_id}.json", report)
    rtl_dir = output / "rtl"
    rtl_dir.mkdir(parents=True, exist_ok=True)
    for name, content in render_shared_portfolio_rtl(portfolio).items():
        (rtl_dir / name).write_text(content, encoding="utf-8")
    tb_name, tb = render_portfolio_testbench(portfolio)
    (rtl_dir / tb_name).write_text(tb, encoding="utf-8")
    figure_takeaways = generate_portfolio_figures(portfolio, output / "figures")
    _write_json(output / "figure_takeaways.json", figure_takeaways)

    graph = portfolio["shared_graph"]
    separate = portfolio["baselines"]["separate_engines_plus_muxes"]
    independent_graph = portfolio["baselines"]["independent_hardware_aware"]["shared_graph_after_generation"]
    general_residual = portfolio["baselines"]["one_general_generated_code"]["weighted_residual_probability"]
    synth = portfolio["baselines"]["ordinary_combined_synthesis"]
    findings = f"""# Portfolio co-synthesis findings

> All fault distributions are modeled synthetic PMFs. XOR counts are structural proxies, not physical area, energy, leakage, or delay.

- Modes: `{len(portfolio['modes'])}` at common `({portfolio['n']},{portfolio['k']})` dimensions.
- Weighted modeled residual probability: `{portfolio['objective_metrics']['weighted_residual_probability']:.12g}`.
- One general generated code weighted residual probability: `{general_residual:.12g}`.
- Joint shared-graph XOR proxy: `{graph['total_xor_gates']}`.
- Independent hardware-aware codes followed by shared-graph optimization: `{independent_graph['total_xor_gates']}` XOR proxy gates.
- Naive per-equation XOR proxy: `{graph['naive_total_xor_gates']}`.
- Separately optimized engine XOR proxy: `{separate['engine_xor_gates']}` plus `{separate['selection_mux_2to1_proxy']}` output-MUX proxy units.
- Accepted matrix changes during alternating co-synthesis: `{portfolio['search']['matrix_changes_accepted']}`.
- Ordinary Yosys/ABC baseline: `{synth['status']}`.
- Physical shared-hardware claim: `{portfolio['hardware_claim_status']}`.
- Scheduler integration: `{portfolio['scheduler_integration_status']}`.

The shared graph is algebraically reconstructed and checked against every matrix row. The joint search is a reliability/hardware Pareto trade-off and did not reduce the XOR proxy relative to independent hardware-aware generation in this run. This is not evidence of PPA improvement: the mandatory ordinary-synthesis baseline and characterized library are absent. Unsafe distribution IDs activate SEC-DED only when that fallback is itself certified; otherwise deployment is rejected.
"""
    (output / "findings.md").write_text(findings, encoding="utf-8")

    files = {
        path.relative_to(output).as_posix(): _sha(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "result_manifest.json"
    }
    source_paths = [
        root / "codeforge" / name
        for name in (
            "gf2.py",
            "faults.py",
            "verify.py",
            "hardware.py",
            "scalable.py",
            "shared_graph.py",
            "portfolio.py",
            "portfolio_artifacts.py",
            "portfolio_figures.py",
            "portfolio_pipeline.py",
        )
    ] + [source, root / "schemas" / "portfolio-cosynthesis-config.schema.json", root / "schemas" / "ecc-portfolio.schema.json", root / "schemas" / "shared-xor-graph.schema.json"]
    source_hashes = {path.relative_to(root).as_posix(): _sha(path) for path in source_paths}
    tree = hashlib.sha256(
        "".join(f"{path}:{digest}\n" for path, digest in sorted(source_hashes.items())).encode("utf-8")
    ).hexdigest()
    manifest = {
        "manifest_version": 1,
        "result_run_id": hashlib.sha256((tree + _sha(source)).encode("ascii")).hexdigest()[:16],
        "repository_commit": _commit(root),
        "repository_dirty": True,
        "input_config": str(source),
        "input_config_sha256": _sha(source),
        "source_tree_sha256": tree,
        "source_files": source_hashes,
        "files": files,
        "observed_runtime_seconds": time.perf_counter() - started,
        "reproduction_command": f"python eccsim.py forge-portfolio --config {source} --outdir {output}",
    }
    _write_json(output / "result_manifest.json", manifest)
    return {
        "portfolio_id": portfolio["portfolio_id"],
        "mode_count": len(portfolio["modes"]),
        "weighted_residual_probability": portfolio["objective_metrics"]["weighted_residual_probability"],
        "shared_xor_gates": graph["total_xor_gates"],
        "separate_engine_xor_gates": separate["engine_xor_gates"],
        "matrix_changes_accepted": portfolio["search"]["matrix_changes_accepted"],
        "hardware_claim_status": portfolio["hardware_claim_status"],
        "scheduler_integration_status": portfolio["scheduler_integration_status"],
        "output_directory": str(output),
        "run_id": manifest["result_run_id"],
    }
