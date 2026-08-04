"""Reproduce the decisive fixed-Hsiao placement/policy negative study."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .ambiguity import build_support, support_document
from .certificates import canonical_hash
from .exact_policy import verify_exact_policy_certificate
from .faults import load_fault_distribution
from .gf2 import matrix_columns_as_ints
from .placement_policy import apply_data_column_placement, optimize_placement_and_policy
from .robust import decoder_actions, evaluate_actions, nominal_ml_actions
from .system_fit import derive_system_sdc_budget, project_system_sdc


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _placed_code(base: Mapping[str, Any], placement_id: str, placement_rows: list[dict[str, Any]]) -> dict[str, Any]:
    placement = next(
        row["placement"] for row in placement_rows if row["placement"]["placement_id"] == placement_id
    )
    return apply_data_column_placement(base, placement)


def run_decisive_study(*, repo_root: str | Path, config_path: str | Path, outdir: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    config_source = root / config_path
    config = _read(config_source)
    output = root / outdir
    output.mkdir(parents=True, exist_ok=True)

    code = _read(root / config["fixed_code"])
    nominal = load_fault_distribution(config["nominal_distribution"], repo_root=root)
    expansions = [load_fault_distribution(path, repo_root=root) for path in config["support_expansions"]]
    support = build_support(nominal, expansions)
    ambiguity = dict(config["ambiguity"])
    budgets = [derive_system_sdc_budget(item) for item in config["operating_points"]]
    budget_by_id = {item["system_target_id"]: item for item in budgets}
    primary_budget = budget_by_id[config["primary_system_target_id"]]
    sdc_limit = primary_budget["conditional_sdc_budget_modeled_support"]
    if sdc_limit is None:
        raise ValueError("primary target has no deployable modeled-support SDC budget")

    placement = optimize_placement_and_policy(
        code,
        support,
        ambiguity,
        sdc_limit=float(sdc_limit),
        placement_constraints=config["placement_constraints"],
    )
    policies = dict(placement.pop("selected_policies"))
    verification: dict[str, Any] = {}
    for name, certificate in policies.items():
        placement_id = placement["selected_placement_ids"][name]
        placed = _placed_code(code, placement_id, placement["candidate_table"])
        verification[name] = verify_exact_policy_certificate(
            placed, support, ambiguity, certificate
        )

    joint = policies["joint"]
    joint_wc = joint["metrics"]["worst_case"]
    policy_only_wc = placement["baselines"]["conventional_placement_optimized_policy"]["worst_case"]
    sequential_wc = placement["baselines"]["sequential_placement_then_policy"]["worst_case"]
    projected_by_target = {
        item["system_target_id"]: project_system_sdc(
            item, support_conditional_sdc=float(joint_wc["sdc"])
        )
        for item in budgets
    }

    joint_code = joint["compiled_code"]
    joint_actions = decoder_actions(joint_code)
    heldout = []
    oracle = []
    for path in config["heldout_synthetic_distributions"]:
        distribution = load_fault_distribution(path, repo_root=root)
        heldout_support = build_support(distribution)
        point_ambiguity = {
            "ambiguity_id": f"heldout-point-{distribution.distribution_id}",
            "type": "total_variation",
            "radius": 0.0,
        }
        report = evaluate_actions(
            joint_code, heldout_support, joint_actions, point_ambiguity, bit_width=int(code["n"])
        )
        heldout.append(
            {
                "distribution_id": distribution.distribution_id,
                "provenance_kind": distribution.provenance.get("kind"),
                "retuned": False,
                "metrics": report["nominal"],
                "outside_training_support_pattern_count": sum(
                    pattern.mask not in {item.mask for item in support} for pattern in heldout_support
                ),
            }
        )
        oracle_actions = nominal_ml_actions(joint_code, heldout_support)
        oracle_report = evaluate_actions(
            joint_code,
            heldout_support,
            oracle_actions,
            point_ambiguity,
            bit_width=int(code["n"]),
        )
        oracle.append(
            {
                "distribution_id": distribution.distribution_id,
                "deployable": False,
                "label": "test-distribution-specialized oracle",
                "metrics": oracle_report["nominal"],
            }
        )

    columns = matrix_columns_as_ints(code["H"])
    previous_mapping = _read(root / "reports/safeforge_64_study/code.json")
    code_audit = {
        "main_matrix_is_conventional_hsiao_secded": (
            all(value.bit_count() % 2 == 1 for value in columns[: int(code["k"])])
            and columns[int(code["k"]) :] == [1 << row for row in range(int(code["r"]))]
            and str(code.get("baseline_kind")) == "equal-redundancy odd-column SEC-DED"
        ),
        "fixed_code_id": code["code_id"],
        "algebraic_equivalence_policy": "column permutations preserve the fixed code and are not new codes",
        "previous_safeforge_mapping_column_multiset_equal": sorted(columns)
        == sorted(matrix_columns_as_ints(previous_mapping["H"])),
        "decoder_policy_improvement_separated_from_placement_improvement": True,
        "support": support_document(support, bit_width=int(code["n"])),
        "unmodeled_tail_discarded": False,
    }

    hardware = _read(root / "reports/safeforge_hardware_validation/nominal_robust_structural_comparison.json")
    hardware_evidence = {
        "existing_same_matrix_generic_synthesis": hardware,
        "applies_to_decisive_joint_placement": False,
        "characterized_library_available_in_completed_run": False,
        "opensta_or_openroad_completed": False,
        "physical_ppa_claim": None,
        "formal_or_exhaustive_behavioral_replay": _read(
            root / "reports/safeforge_hardware_validation/validation_summary.json"
        )["campaigns"],
        "interpretation": "Prior RTL replay is real tool execution, but the decisive interleaved policy lacks a characterized-library/P&R result; Stage 5 is not passed.",
    }

    fixed_due = float(policy_only_wc["due"])
    sequential_due = float(sequential_wc["due"])
    joint_due = float(joint_wc["due"])
    due_reduction = {
        "versus_policy_only_absolute": fixed_due - joint_due,
        "versus_policy_only_relative": (fixed_due - joint_due) / fixed_due if fixed_due else 0.0,
        "versus_sequential_absolute": sequential_due - joint_due,
        "versus_sequential_relative": (sequential_due - joint_due) / sequential_due if sequential_due else 0.0,
    }
    gate = {
        "overall_status": "failed_negative_result",
        "kill_criteria_triggered": [
            "practical 72-bit worst-case DUE remains close to one at the system-derived SDC target",
            "joint optimization does not beat the strong sequential placement-collision baseline",
            "no raw or measurement-derived held-out bit-exact dataset is available",
            "deployment depends on an unmeasured outside-support tail bound",
            "the decisive joint policy has no characterized-library or placed-and-routed cost result",
        ],
        "scientific_gate": {
            "nontrivial_availability_at_stringent_bound": False,
            "beats_policy_only": joint_due < fixed_due - 1e-12,
            "beats_strong_sequential": joint_due < sequential_due - 1e-12,
            "heldout_experimental_shift": False,
            "independent_certificates": all(
                item["verification_status"] == "passed" for item in verification.values()
            ),
            "tail_accounted": True,
            "tail_empirically_justified": False,
            "practical_physical_cost_quantified": False,
            "new_exact_formulation_present": True,
        },
    }

    evidence = _read(root / "data/fault_evidence/sources.json")
    result = {
        "schema_version": 1,
        "study_id": config["study_id"],
        "claim_status": "publication_grade_negative_result_candidate",
        "primary_system_target": primary_budget,
        "joint_metrics": {
            "policy_id": joint["policy_id"],
            "selected_correction_count": joint["selected_correction_count"],
            "nominal": joint["metrics"]["nominal"],
            "worst_case": joint["metrics"]["worst_case"],
            "a_posteriori_absolute_gap": joint["optimization"]["a_posteriori_absolute_gap"],
        },
        "due_reduction": due_reduction,
        "selected_placement_ids": placement["selected_placement_ids"],
        "placement_library_size": placement["placement_library_size"],
        "joint_library_optimality": placement["joint_optimality"],
        "projected_system_sdc": projected_by_target,
        "heldout_status": "synthetic_only_not_experimental_validation",
        "gate": gate,
    }

    _write(output / "system_budgets.json", budgets)
    _write(output / "placement_policy_study.json", placement)
    for name, certificate in policies.items():
        _write(output / "certificates" / f"{name}.json", certificate)
    _write(output / "certificate_verification.json", verification)
    _write(output / "heldout_synthetic.json", {"evaluated_without_retuning": heldout, "oracles": oracle})
    _write(output / "code_and_evidence_audit.json", {"code_audit": code_audit, "external_evidence": evidence})
    _write(output / "hardware_evidence.json", hardware_evidence)
    _write(output / "scientific_gate.json", gate)
    _write(output / "result_summary.json", result)

    risk_rows = []
    baseline_metrics = placement["baselines"]
    for name, baseline in baseline_metrics.items():
        if baseline is None:
            continue
        metrics = baseline["worst_case"]
        projection = project_system_sdc(
            primary_budget, support_conditional_sdc=float(metrics["sdc"])
        )
        risk_rows.append(
            {
                "strategy": name,
                "certified_worst_case_sdc": metrics["sdc"],
                "projected_system_sdc_fit_upper": projection["system_sdc_fit_upper"],
                "worst_case_due": metrics["due"],
                "meets_primary_target": projection["meets_system_target"],
            }
        )
    with (output / "risk_coverage.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(risk_rows[0]))
        writer.writeheader()
        writer.writerows(risk_rows)

    try:
        import matplotlib.pyplot as plt

        plt.rcParams["svg.hashsalt"] = "safeforge-decisive-72-v1"
        short_labels = {
            "conventional_fixed_placement_conventional_decoder": "fixed + conventional",
            "conventional_placement_optimized_policy": "fixed + exact policy",
            "interleaved_placement_conventional_decoder": "interleaved + conventional",
            "fault_aware_placement_conventional_decoder": "fault-aware + conventional",
            "sequential_placement_then_policy": "sequential",
            "joint_placement_and_policy": "joint",
        }
        grouped_points: dict[tuple[float, float], list[str]] = {}
        for row in risk_rows:
            key = (
                float(row["projected_system_sdc_fit_upper"]),
                float(row["worst_case_due"]),
            )
            grouped_points.setdefault(key, []).append(short_labels[row["strategy"]])
        figure, axis = plt.subplots(figsize=(8, 5))
        axis.scatter(
            [point[0] for point in grouped_points],
            [point[1] for point in grouped_points],
            s=55,
        )
        for (x_value, y_value), names in grouped_points.items():
            if set(names) == {"sequential", "joint"}:
                label = "sequential = joint"
            elif len(names) == 3 and all("conventional" in name for name in names):
                label = "conventional decoders (3 placements)"
            else:
                label = ", ".join(names)
            axis.annotate(
                label,
                (x_value, y_value),
                xytext=(-7 if x_value > 10 else 7, -12 if y_value > 0.95 else 6),
                textcoords="offset points",
                fontsize=8,
                va="top" if y_value > 0.95 else "bottom",
                ha="right" if x_value > 10 else "left",
            )
        axis.axvline(float(primary_budget["target"]["system_sdc_fit"]), color="black", linestyle="--", label="1 FIT target")
        axis.set_xlabel("Projected system SDC FIT upper bound")
        axis.set_ylabel("Certified worst-case DUE")
        axis.set_xscale("log")
        axis.set_xlim(0.005, 120)
        axis.set_ylim(0, 1.03)
        axis.grid(True, alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(output / "risk_coverage.svg", metadata={"Date": None})
        figure.savefig(output / "risk_coverage.png", dpi=160)
        plt.close(figure)
    except ImportError:
        pass

    artifact_paths = sorted(
        path for path in output.rglob("*") if path.is_file() and path.name != "manifest.json"
    )
    manifest = {
        "schema_version": 1,
        "study_id": config["study_id"],
        "reproduction_command": f"python scripts/run_safeforge_decisive_study.py --config {config_path} --outdir {outdir}",
        "config_sha256": _sha256(config_source),
        "artifacts": {
            str(path.relative_to(output)).replace("\\", "/"): _sha256(path) for path in artifact_paths
        },
    }
    manifest["manifest_sha256"] = canonical_hash(manifest)
    _write(output / "manifest.json", manifest)
    return result
