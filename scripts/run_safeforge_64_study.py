#!/usr/bin/env python3
"""Run the deterministic k=64 mapping heuristic and retain its full-support proof."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codeforge.ambiguity import build_support, support_document
from codeforge.faults import load_fault_distribution
from codeforge.robust_synthesis import cosynthesize_scalable_verified_heuristic
from codeforge.robust_synthesis import universally_safe_actions
from codeforge.robust import evaluate_actions


def main() -> None:
    base = json.loads(
        (ROOT / "reports/code_synthesis_64/baselines/odd_column_secded_code.json").read_text(
            encoding="utf-8"
        )
    )
    nominal = load_fault_distribution(
        "configs/fault_distributions/benchmarks/spatial_hot_spots.json", repo_root=ROOT
    )
    expansions = [
        load_fault_distribution(path, repo_root=ROOT)
        for path in (
            "configs/fault_distributions/benchmarks/distribution_shift.json",
            "configs/fault_distributions/benchmarks/voltage_sensitive.json",
            "configs/fault_distributions/benchmarks/mixed_sbu_dbu_mbu.json",
        )
    ]
    support = build_support(nominal, expansions)
    ambiguity = json.loads(
        (ROOT / "configs/ambiguity/tv_72bit_example.json").read_text(encoding="utf-8")
    )
    result = cosynthesize_scalable_verified_heuristic(
        base,
        support,
        ambiguity,
        code_id="safeforge-robust-72-64-mapping-v1",
        raw_fit=nominal.raw_fit,
    )
    output = ROOT / "reports/safeforge_64_study"
    output.mkdir(parents=True, exist_ok=True)
    (output / "heuristic_search.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "code.json").write_text(
        json.dumps(result["code"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "support.json").write_text(
        json.dumps(support_document(support, bit_width=72), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    base_evaluation = evaluate_actions(
        base,
        support,
        universally_safe_actions(base, support),
        ambiguity,
        bit_width=72,
    )
    (output / "mapping_comparison.json").write_text(
        json.dumps(
            {
                "experiment_scope": "same dimensions, expanded support, PMF, action semantics, and TV radius",
                "original_known_matrix_mapping": {
                    "nominal": base_evaluation["nominal"],
                    "worst_case": base_evaluation["worst_case"],
                },
                "verified_heuristic_mapping": {
                    "nominal": result["verification"]["nominal"],
                    "worst_case": result["verification"]["worst_case"],
                },
                "physical_ppa": None,
                "conclusion": "mapping heuristic result only; no global k=64 matrix optimality claim",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    source_paths = [
        ROOT / "codeforge/ambiguity.py",
        ROOT / "codeforge/robust.py",
        ROOT / "codeforge/robust_synthesis.py",
        ROOT / "scripts/run_safeforge_64_study.py",
        ROOT / "configs/ambiguity/tv_72bit_example.json",
        ROOT / "reports/code_synthesis_64/baselines/odd_column_secded_code.json",
        ROOT / "configs/fault_distributions/benchmarks/spatial_hot_spots.json",
        ROOT / "configs/fault_distributions/benchmarks/distribution_shift.json",
        ROOT / "configs/fault_distributions/benchmarks/voltage_sensitive.json",
        ROOT / "configs/fault_distributions/benchmarks/mixed_sbu_dbu_mbu.json",
    ]
    source_hashes = {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source_paths
    }
    files = {
        path.relative_to(output).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "result_manifest.json"
    }
    (output / "result_manifest.json").write_text(
        json.dumps(
            {
                "manifest_version": 1,
                "source_files": source_hashes,
                "source_tree_sha256": hashlib.sha256(
                    "".join(
                        f"{path}:{digest}\n" for path, digest in sorted(source_hashes.items())
                    ).encode()
                ).hexdigest(),
                "files": files,
                "reproduction_command": "python scripts/run_safeforge_64_study.py",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "candidate_mappings_evaluated": result["candidate_mappings_evaluated"],
                "base_matrix_changed": result["base_matrix_changed"],
                "nominal": result["verification"]["nominal"],
                "worst_case": result["verification"]["worst_case"],
                "output": str(output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
