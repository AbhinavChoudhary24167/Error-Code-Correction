"""Artifact pipeline for exact single-code synthesis and external verification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import time
import copy
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from .artifacts import (
    render_cpp_reference,
    render_python_reference,
    render_systemverilog,
    render_testbench,
)
from .exact import synthesize_exact
from .faults import ErrorPattern, FaultDistribution, distribution_to_document, load_fault_distribution
from .gf2 import bit_string, matrix_columns_as_ints, systematic_matrices
from .hardware import structural_cost
from .scalable import synthesize_scalable
from .verify import verify_code_document


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return "unknown"


def _validate(payload: Mapping[str, Any], schema_path: Path) -> None:
    Draft202012Validator(_read_json(schema_path)).validate(payload)


def _baseline_code(config: Mapping[str, Any]) -> dict[str, Any]:
    k, r = int(config["k"]), int(config["r"])
    odd_nonbasis = [
        value
        for value in range(1, 1 << r)
        if value.bit_count() % 2 == 1 and value not in {1 << row for row in range(r)}
    ]
    if len(odd_nonbasis) < k:
        raise ValueError("the requested dimensions cannot form the small odd-column SEC-DED baseline")
    columns = odd_nonbasis[:k]
    h, g = systematic_matrices(columns, r)
    all_columns = matrix_columns_as_ints(h)
    entries = {
        syndrome_value: 1 << position for position, syndrome_value in enumerate(all_columns)
    }
    correction_entries = [
        {
            "syndrome": bit_string(syndrome_value, r),
            "positions": [position],
        }
        for position, syndrome_value in enumerate(all_columns)
    ]
    return {
        "schema_version": 1,
        "code_id": f"odd-column-secded-{k}-{k+r}",
        "code_class": "binary_systematic_linear_block",
        "baseline_kind": "equal-redundancy odd-column SEC-DED",
        "k": k,
        "r": r,
        "n": k + r,
        "systematic": True,
        "H": h,
        "G": g,
        "column_syndromes": [bit_string(value, r) for value in all_columns],
        "decoder": {
            "type": "hard_decision_syndrome_table",
            "correction_entries": correction_entries,
        },
        "constraints": {},
        "structural_hardware": structural_cost(
            h,
            g,
            entries,
            max_xor_fanin=int(config.get("hardware_model", {}).get("max_xor_fanin", 2)),
        ),
    }


def _uniformized_distribution(distribution: FaultDistribution) -> FaultDistribution:
    probability = 1.0 / len(distribution.patterns)
    return FaultDistribution(
        distribution_id=f"{distribution.distribution_id}-uniformized",
        bit_width=distribution.bit_width,
        patterns=tuple(
            ErrorPattern(
                pattern_id=pattern.pattern_id,
                positions=pattern.positions,
                probability=probability,
                family=pattern.family,
                metadata=pattern.metadata,
            )
            for pattern in distribution.patterns
        ),
        provenance={
            "kind": "synthetic",
            "description": "Uniformized ablation over the same finite error vectors.",
            "seed": distribution.provenance.get("seed"),
        },
        raw_fit=distribution.raw_fit,
    )


def verify_external_code(
    code_path: str | Path,
    fault_model_path: str | Path,
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root)
    code_source = Path(code_path)
    if not code_source.is_absolute():
        code_source = root / code_source
    code = _read_json(code_source)
    _validate(code, root / "schemas" / "linear-code.schema.json")
    distribution = load_fault_distribution(fault_model_path, repo_root=root)
    report = verify_code_document(code, distribution)
    _validate(report, root / "schemas" / "code-verification-report.schema.json")
    return report


def run_code_synthesis(
    config_path: str | Path,
    outdir: str | Path,
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config_source = Path(config_path)
    if not config_source.is_absolute():
        config_source = root / config_source
    output = Path(outdir)
    if not output.is_absolute():
        output = root / output
    output.mkdir(parents=True, exist_ok=True)
    config = _read_json(config_source)
    _validate(config, root / "schemas" / "code-synthesis-config.schema.json")
    distribution = load_fault_distribution(config["fault_distribution"], repo_root=root)
    started = time.perf_counter()
    if config["method"] == "exact_exhaustive":
        result = synthesize_exact(config, distribution)
    elif config["method"] == "deterministic_beam":
        result = synthesize_scalable(config, distribution)
    else:  # guarded by schema; retained for direct callers
        raise ValueError(f"unsupported synthesis method {config['method']!r}")
    _write_json(output / "search_report.json", result.search)
    if result.code is None:
        raise ValueError(f"code synthesis ended with status {result.search['status']}")
    code = result.code
    report = verify_code_document(code, distribution)
    _validate(code, root / "schemas" / "linear-code.schema.json")
    _validate(report, root / "schemas" / "code-verification-report.schema.json")
    if report["verification_status"] != "passed":
        raise ValueError("independent exhaustive verification rejected the synthesized code")

    baseline = _baseline_code(config)
    baseline_report = verify_code_document(baseline, distribution)
    _validate(baseline, root / "schemas" / "linear-code.schema.json")
    _validate(baseline_report, root / "schemas" / "code-verification-report.schema.json")

    _write_json(output / "code.json", code)
    _write_json(output / "fault_distribution.json", distribution_to_document(distribution))
    _write_json(output / "verification_report.json", report)
    _write_json(output / "baselines" / "odd_column_secded_code.json", baseline)
    _write_json(output / "baselines" / "odd_column_secded_verification.json", baseline_report)
    ablations: dict[str, Any] = {
        "uniform_vs_probability_weighted": {"status": "not_run_for_scalable_configuration"},
        "reliability_only_vs_hardware_aware": {"status": "not_run_for_scalable_configuration"},
        "sdc_constraint": {"status": "not_run_for_scalable_configuration"},
    }
    if config["method"] == "exact_exhaustive":
        uniform_distribution = _uniformized_distribution(distribution)
        uniform_config = copy.deepcopy(config)
        uniform_config["code_id"] = f"{config['code_id']}-uniform-ablation"
        uniform_result = synthesize_exact(uniform_config, uniform_distribution)
        if uniform_result.code is None:
            raise ValueError("uniform-probability ablation was infeasible")
        uniform_on_target = verify_code_document(uniform_result.code, distribution)

        reliability_config = copy.deepcopy(config)
        reliability_config["code_id"] = f"{config['code_id']}-reliability-only-ablation"
        reliability_config.setdefault("hardware_model", {})["hardware_aware"] = False
        reliability_result = synthesize_exact(reliability_config, distribution)
        if reliability_result.code is None:
            raise ValueError("reliability-only ablation was infeasible")
        reliability_report = verify_code_document(reliability_result.code, distribution)

        relaxed_config = copy.deepcopy(config)
        relaxed_config["code_id"] = f"{config['code_id']}-relaxed-sdc-ablation"
        relaxed_config["constraints"]["max_sdc_probability"] = 1.0
        relaxed_config["constraints"]["max_residual_fit"] = 1000.0
        relaxed_result = synthesize_exact(relaxed_config, distribution)
        if relaxed_result.code is None:
            raise ValueError("relaxed-SDC ablation was infeasible")
        relaxed_report = verify_code_document(relaxed_result.code, distribution)
        ablations = {
            "uniform_vs_probability_weighted": {
                "status": "completed",
                "weighted_synthesis": report["probability_mass"],
                "uniform_synthesis_evaluated_on_target": uniform_on_target["probability_mass"],
                "same_matrix": code["H"] == uniform_result.code["H"],
            },
            "reliability_only_vs_hardware_aware": {
                "status": "completed",
                "hardware_aware_probability_mass": report["probability_mass"],
                "reliability_only_probability_mass": reliability_report["probability_mass"],
                "hardware_aware_structural": code["structural_hardware"],
                "reliability_only_structural": reliability_result.code["structural_hardware"],
                "same_matrix": code["H"] == reliability_result.code["H"],
            },
            "sdc_constraint": {
                "status": "completed",
                "hard_zero_sdc": report["probability_mass"],
                "relaxed_sdc": relaxed_report["probability_mass"],
                "relaxed_matrix": relaxed_result.code["H"],
            },
        }
    _write_json(output / "ablations.json", ablations)
    certificate = {
        "schema_version": 1,
        "code_id": code["code_id"],
        "verification_status": report["verification_status"],
        "matrix_checks": report["matrix_checks"],
        "decoder_checks": report["decoder_checks"],
        "campaign": report["campaign"],
        "probability_mass": report["probability_mass"],
        "constraint_results": report["constraint_results"],
        "search": result.search,
        "certificate_scope": "all data words crossed with every supplied finite error vector",
    }
    _write_json(output / "certificate.json", certificate)

    reference_dir = output / "reference"
    reference_dir.mkdir(parents=True, exist_ok=True)
    (reference_dir / "reference_model.py").write_text(render_python_reference(code), encoding="utf-8")
    (reference_dir / "reference_model.cpp").write_text(render_cpp_reference(code), encoding="utf-8")
    rtl_dir = output / "rtl"
    rtl_dir.mkdir(parents=True, exist_ok=True)
    for name, content in render_systemverilog(code).items():
        (rtl_dir / name).write_text(content, encoding="utf-8")
    tb_name, tb_content = render_testbench(code, report["per_pattern"])
    (rtl_dir / tb_name).write_text(tb_content, encoding="utf-8")

    comparison = {
        "comparison_kind": "equal_redundancy",
        "k": int(config["k"]),
        "r": int(config["r"]),
        "generated": {
            "code_id": code["code_id"],
            "probability_mass": report["probability_mass"],
            "fit": report["fit"],
            "structural_hardware": code["structural_hardware"],
        },
        "baseline": {
            "code_id": baseline["code_id"],
            "probability_mass": baseline_report["probability_mass"],
            "fit": baseline_report["fit"],
            "structural_hardware": baseline["structural_hardware"],
        },
        "physical_ppa": None,
    }
    _write_json(output / "equal_redundancy_comparison.json", comparison)
    candidates_considered = result.search.get(
        "candidate_matrices_considered",
        result.search.get("candidate_matrices_evaluated", "not reported"),
    )
    candidate_space = result.search.get("theoretical_candidate_matrices", "not exhaustively enumerated")
    findings = f"""# Code-forging result

> The fault PMF is explicitly synthetic. Structural gate counts are not physical PPA.

- Search status: `{result.search['status']}`
- Optimality proven over configured systematic search space: `{str(result.search['optimality_proven']).lower()}`
- Candidate matrices considered: `{candidates_considered}` / `{candidate_space}`
- Exhaustive decoder cases: `{report['campaign']['decoder_cases']}`
- Generated corrected probability: `{report['probability_mass']['corrected']:.12g}`
- Generated DUE probability: `{report['probability_mass']['due']:.12g}`
- Generated SDC probability: `{report['probability_mass']['sdc']:.12g}`
- Generated residual FIT: `{report['fit']['residual_fit']}`
- Equal-redundancy SEC-DED corrected probability: `{baseline_report['probability_mass']['corrected']:.12g}`
- Equal-redundancy SEC-DED SDC probability: `{baseline_report['probability_mass']['sdc']:.12g}`

This result is a feasibility certificate for one small modeled distribution. It does not establish k=64 scaling, physical hardware improvement, synthesis-tool advantage, or distribution-shift robustness.
"""
    (output / "findings.md").write_text(findings, encoding="utf-8")

    manifest_exclusions = {"result_manifest.json"}
    files = {
        path.relative_to(output).as_posix(): _sha256(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name not in manifest_exclusions
    }
    sources = [
        root / "codeforge" / name
        for name in (
            "gf2.py",
            "faults.py",
            "verify.py",
            "hardware.py",
            "exact.py",
            "scalable.py",
            "artifacts.py",
            "pipeline.py",
        )
    ] + [
        config_source,
        root / str(config["fault_distribution"]),
        root / "schemas" / "fault-distribution.schema.json",
        root / "schemas" / "linear-code.schema.json",
        root / "schemas" / "code-synthesis-config.schema.json",
        root / "schemas" / "code-verification-report.schema.json",
    ]
    source_hashes = {path.relative_to(root).as_posix(): _sha256(path) for path in sources}
    source_tree_hash = hashlib.sha256(
        "".join(f"{path}:{digest}\n" for path, digest in sorted(source_hashes.items())).encode("utf-8")
    ).hexdigest()
    manifest = {
        "manifest_version": 1,
        "result_run_id": hashlib.sha256(
            (source_tree_hash + _sha256(config_source)).encode("ascii")
        ).hexdigest()[:16],
        "repository_commit": _git_commit(root),
        "repository_dirty": True,
        "input_config": str(config_source),
        "input_config_sha256": _sha256(config_source),
        "source_tree_sha256": source_tree_hash,
        "source_files": source_hashes,
        "files": files,
        "observed_runtime_seconds": time.perf_counter() - started,
        "reproduction_command": f"python eccsim.py forge-code --config {config_source} --outdir {output}",
    }
    _write_json(output / "result_manifest.json", manifest)
    return {
        "code_id": code["code_id"],
        "status": result.search["status"],
        "optimality_proven": result.search["optimality_proven"],
        "verification_status": report["verification_status"],
        "corrected_probability": report["probability_mass"]["corrected"],
        "due_probability": report["probability_mass"]["due"],
        "sdc_probability": report["probability_mass"]["sdc"],
        "residual_fit": report["fit"]["residual_fit"],
        "baseline_corrected_probability": baseline_report["probability_mass"]["corrected"],
        "output_directory": str(output),
        "run_id": manifest["result_run_id"],
    }
