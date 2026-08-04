"""Authoritative five-strategy SafeForge study and vector-figure generator."""

from __future__ import annotations

import itertools
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from .ambiguity import build_support, certified_safety_radius, solve_worst_case, support_document
from .equivalence import classify_code
from .experiments import attach_experiment_identity, comparison_table, make_experiment_identity
from .faults import load_fault_distribution
from .gf2 import matrix_columns_as_ints, systematic_matrices
from .hardware import hardware_key, structural_cost
from .robust import (
    compile_safe_decoder,
    decoder_actions,
    evaluate_actions,
    nominal_ml_actions,
)
from .robust_synthesis import cosynthesize_exact_small, universally_safe_actions


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _code_with_matrix(base: Mapping[str, Any], data_columns: Sequence[int], code_id: str) -> dict[str, Any]:
    code = dict(base)
    h, g = systematic_matrices(data_columns, int(base["r"]))
    code.update({"code_id": code_id, "H": h, "G": g, "decoder": {"type": "hard_decision_syndrome_table", "correction_entries": []}})
    return code


def _optimized_known_mapping(
    base: Mapping[str, Any], support: Sequence[Any], ambiguity: Mapping[str, Any]
) -> dict[str, Any]:
    k = int(base["k"])
    columns = matrix_columns_as_ints(base["H"])[:k]
    best = None
    for permutation in itertools.permutations(columns):
        code = _code_with_matrix(base, permutation, "known-hsiao-optimized-physical-mapping")
        actions = universally_safe_actions(code, support)
        report = evaluate_actions(code, support, actions, ambiguity, bit_width=int(code["n"]))
        cost = structural_cost(code["H"], code["G"], actions, max_xor_fanin=2)
        key = (report["worst_case"]["due"], report["nominal"]["due"], hardware_key(cost), tuple(permutation))
        if report["worst_case"]["sdc"] <= 1e-14 and (best is None or key < best[0]):
            best = (key, code, actions, report, cost, permutation)
    if best is None:
        raise ValueError("no zero-SDC physical mapping of the known code was found")
    return {
        "code": best[1],
        "actions": best[2],
        "evaluation": best[3],
        "hardware": best[4],
        "data_column_permutation": list(best[5]),
        "optimality": "all data-column permutations exhaustively evaluated",
    }


def _record(
    strategy_id: str,
    label: str,
    code: Mapping[str, Any],
    actions: Mapping[int, int],
    evaluation: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    cost = structural_cost(code["H"], code["G"], actions, max_xor_fanin=2)
    return attach_experiment_identity(
        {
            "strategy_id": strategy_id,
            "label": label,
            "code_id": code["code_id"],
            "nominal": dict(evaluation["nominal"]),
            "worst_case": dict(evaluation["worst_case"]),
            "decoder_correction_entries": len(actions),
            "decoder_abstain_entries": (1 << int(code["r"])) - 1 - len(actions),
            "structural_hardware": cost,
            "physical_ppa": None,
        },
        identity,
    )


def _heldout_metrics(code: Mapping[str, Any], actions: Mapping[int, int], heldout_support: Sequence[Any]) -> dict[str, Any]:
    return evaluate_actions(
        code,
        heldout_support,
        actions,
        {"type": "total_variation", "radius": 0.0},
        bit_width=int(code["n"]),
    )["nominal"]


def _tv_distance(nominal: Any, shifted: Any) -> float:
    n = nominal.bit_width
    left = {item.mask(n): item.probability for item in nominal.patterns}
    right = {item.mask(n): item.probability for item in shifted.patterns}
    return 0.5 * sum(abs(left.get(mask, 0.0) - right.get(mask, 0.0)) for mask in set(left) | set(right))


def _plot_study(
    output: Path,
    records: Sequence[Mapping[str, Any]],
    curves: Mapping[str, Any],
    heldout: Mapping[str, Any],
    radii: Mapping[str, float],
    scheduler: Mapping[str, Any],
) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure_dir = output / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    labels = [record["label"] for record in records]
    short = [str(index + 1) for index in range(len(labels))]
    colors = ["#4d4d4d", "#d95f02", "#1b9e77", "#7570b3", "#006d2c"]
    saved: list[str] = []

    def save(name: str) -> None:
        plt.tight_layout()
        path = figure_dir / f"{name}.svg"
        plt.savefig(
            path,
            format="svg",
            bbox_inches="tight",
            metadata={"Creator": "GREEN-ECC SafeForge", "Date": None},
        )
        plt.close()
        saved.append(path.relative_to(output).as_posix())

    plt.figure(figsize=(6.4, 4.2))
    for index, record in enumerate(records):
        point = heldout[record["strategy_id"]]
        plt.scatter(record["nominal"]["corrected"], point["sdc"], s=65, color=colors[index])
        plt.annotate(short[index], (record["nominal"]["corrected"], point["sdc"]), xytext=(5, 5), textcoords="offset points")
    plt.xlabel("Nominal corrected probability")
    plt.ylabel("Held-out shifted SDC probability")
    plt.title("Nominal coverage can conceal shift-induced silent corruption")
    plt.grid(alpha=.2)
    save("01_nominal_gain_vs_shift_sdc")

    plt.figure(figsize=(6.4, 4.2))
    for index, record in enumerate(records):
        data = curves[record["strategy_id"]]
        plt.plot(data["radius"], data["sdc"], label=short[index] + " " + record["label"], color=colors[index])
    plt.xlabel("TV ambiguity radius δ")
    plt.ylabel("Worst-case SDC")
    plt.title("Certified decoder keeps SDC bounded under modeled shift")
    plt.legend(fontsize=7)
    plt.grid(alpha=.2)
    save("02_worst_case_sdc_vs_radius")

    plt.figure(figsize=(6.4, 4.2))
    for index, record in enumerate(records):
        data = curves[record["strategy_id"]]
        plt.plot(data["radius"], data["due"], label=short[index], color=colors[index])
    plt.xlabel("TV ambiguity radius δ")
    plt.ylabel("Worst-case DUE")
    plt.title("Declared failure cost is reported, not hidden")
    plt.legend(title="Strategy", ncol=3)
    plt.grid(alpha=.2)
    save("03_worst_case_due_vs_radius")

    plt.figure(figsize=(6.4, 4.2))
    plt.bar(short, [radii[item["strategy_id"]] for item in records], color=colors)
    plt.xlabel("Strategy (see comparison table)")
    plt.ylabel("Certified TV safety radius δ*")
    plt.title("Tolerance to fault-PMF shift at zero SDC")
    save("04_certified_safety_radius")

    selected = [records[1], records[2]]
    x = [0, 1]
    plt.figure(figsize=(5.6, 4.2))
    plt.bar([value - .18 for value in x], [item["nominal"]["corrected"] for item in selected], width=.36, label="Corrected")
    plt.bar([value + .18 for value in x], [item["worst_case"]["due"] for item in selected], width=.36, label="Worst DUE")
    plt.xticks(x, ["Nominal ML", "Robust abstain"])
    plt.ylabel("Probability")
    plt.title("Abstention trades nominal coverage for certified safety")
    plt.legend()
    save("05_nominal_ml_vs_robust_abstain")

    selected = [records[2], records[4]]
    x = [0, 1]
    plt.figure(figsize=(5.6, 4.2))
    plt.bar([value - .18 for value in x], [item["nominal"]["corrected"] for item in selected], width=.36, label="Nominal corrected")
    plt.bar([value + .18 for value in x], [item["worst_case"]["due"] for item in selected], width=.36, label="Worst DUE")
    plt.xticks(x, ["Known Hsiao", "Co-synthesized H"])
    plt.ylabel("Probability")
    plt.title("Known matrix versus robust matrix-policy co-synthesis")
    plt.legend()
    save("06_known_vs_synthesized_matrix")

    plt.figure(figsize=(6.4, 4.2))
    plt.bar(short, [item["nominal"]["corrected"] for item in records], color=colors)
    plt.ylabel("Nominal corrected probability")
    plt.xlabel("Decoder/mapping/matrix strategy")
    plt.title("Contribution ablation under one experiment identity")
    save("07_policy_mapping_matrix_ablation")

    plt.figure(figsize=(6.4, 4.2))
    plt.bar(short, [item["structural_hardware"]["matrix_xor_gates"] for item in records], color=colors, label="Matrix XOR proxy")
    plt.plot(short, [item["decoder_correction_entries"] for item in records], "ko--", label="Correction entries")
    plt.ylabel("Technology-independent structural count")
    plt.title("Certification hardware overhead (not physical PPA)")
    plt.legend()
    save("08_hardware_overhead")

    plt.figure(figsize=(6.4, 3.8))
    x = [item["observed_radius"] for item in scheduler["decisions"]]
    y = [1 if item["selected_mode"] == "specialized-safe" else 0 for item in scheduler["decisions"]]
    colors_scheduler = ["#1b9e77" if item["support_contained"] else "#d95f02" for item in scheduler["decisions"]]
    plt.scatter(x, y, color=colors_scheduler, s=70)
    plt.yticks([0, 1], ["Safe fallback", "Specialized safe"])
    plt.xlabel("Current confidence-region TV radius")
    plt.title("Scheduler requires radius and support containment")
    plt.grid(axis="x", alpha=.2)
    save("09_scheduler_envelope_gate")
    return saved


def run_authoritative_study(*, repo_root: str | Path, outdir: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    output = Path(outdir)
    if not output.is_absolute():
        output = root / output
    output.mkdir(parents=True, exist_ok=True)
    baseline = _read(root / "reports" / "code_synthesis" / "baselines" / "odd_column_secded_code.json")
    synthesized = _read(root / "reports" / "code_synthesis" / "code.json")
    nominal = load_fault_distribution("configs/fault_distributions/small_hotspot_8bit.json", repo_root=root)
    shifted = load_fault_distribution("configs/fault_distributions/small_shifted_8bit.json", repo_root=root)
    support = build_support(nominal, [shifted])
    heldout_support = build_support(shifted)
    ambiguity = _read(root / "configs" / "ambiguity" / "tv_small_example.json")
    identity = make_experiment_identity(
        k=4,
        r=4,
        distribution=nominal,
        error_universe_document=support_document(support, bit_width=8),
        ambiguity=ambiguity,
    )

    conventional_actions = decoder_actions(baseline)
    nominal_fixed_actions = nominal_ml_actions(baseline, support)
    robust_fixed = compile_safe_decoder(
        baseline, support, ambiguity, sdc_limit=0.0, raw_fit=nominal.raw_fit
    )
    nominal_synthesized_actions = nominal_ml_actions(synthesized, support)
    robust_cosynthesis = cosynthesize_exact_small(
        k=4,
        r=4,
        support=support,
        ambiguity=ambiguity,
        code_id="safeforge-robust-8-4-v1",
        sdc_limit=0.0,
        raw_fit=nominal.raw_fit,
    )
    robust_code = robust_cosynthesis["code"]
    robust_actions = decoder_actions(robust_code)
    candidates = [
        ("conventional_min_weight_fixed", "Conventional SECDED", baseline, conventional_actions),
        ("nominal_ml_fixed", "Nominal ML / fixed Hsiao", baseline, nominal_fixed_actions),
        ("robust_abstain_fixed", "Robust abstain / fixed Hsiao", baseline, decoder_actions(robust_fixed["compiled_code"])),
        ("nominal_synthesized", "Nominal synthesized H + ML", synthesized, nominal_synthesized_actions),
        ("robust_cosynthesized", "Robust H + abstain", robust_code, robust_actions),
    ]
    records = []
    evaluations: dict[str, Any] = {}
    heldout: dict[str, Any] = {}
    action_catalogue: dict[str, dict[int, int]] = {}
    code_catalogue: dict[str, Mapping[str, Any]] = {}
    for strategy_id, label, code, actions in candidates:
        evaluation = evaluate_actions(code, support, actions, ambiguity, bit_width=8)
        evaluations[strategy_id] = evaluation
        heldout[strategy_id] = _heldout_metrics(code, actions, heldout_support)
        action_catalogue[strategy_id] = dict(actions)
        code_catalogue[strategy_id] = code
        records.append(_record(strategy_id, label, code, actions, evaluation, identity))
    comparison = comparison_table(records)

    mapped = _optimized_known_mapping(baseline, support, ambiguity)
    mapping_ablation = {
        "unmapped_known_matrix": records[2],
        "optimized_physical_mapping": _record(
            "robust_known_optimized_mapping",
            "Robust known Hsiao + optimized mapping",
            mapped["code"],
            mapped["actions"],
            mapped["evaluation"],
            identity,
        ),
        "data_column_permutation": mapped["data_column_permutation"],
        "optimality": mapped["optimality"],
    }
    comparison_table([mapping_ablation["unmapped_known_matrix"], mapping_ablation["optimized_physical_mapping"]])

    curve_radii = [index / 100 for index in range(0, 101, 4)]
    curves: dict[str, Any] = {}
    safety_radii: dict[str, float] = {}
    for record in records:
        strategy_id = record["strategy_id"]
        code, actions = code_catalogue[strategy_id], action_catalogue[strategy_id]
        executed = evaluate_actions(code, support, actions, {"type": "total_variation", "radius": 0}, bit_width=8)
        sdc_loss = executed["loss_vectors"]["sdc"]
        due_loss = executed["loss_vectors"]["due"]
        curves[strategy_id] = {
            "radius": curve_radii,
            "sdc": [solve_worst_case(support, sdc_loss, ambiguity, bit_width=8, radius=value)["worst_case_risk"] for value in curve_radii],
            "due": [solve_worst_case(support, due_loss, ambiguity, bit_width=8, radius=value)["worst_case_risk"] for value in curve_radii],
        }
        safety_radii[strategy_id] = certified_safety_radius(
            support,
            sdc_loss,
            ambiguity,
            bit_width=8,
            risk_limit=0.0,
            maximum_radius=1.0,
        )["certified_radius"]
    shifted_distance = _tv_distance(nominal, shifted)
    robust_radius = safety_radii["robust_cosynthesized"]
    scheduler = {
        "gate": "current confidence region must be contained in the selected mode certificate",
        "specialized_certificate_radius": robust_radius,
        "heldout_shift_tv_distance": shifted_distance,
        "heldout_inside_envelope": shifted_distance <= robust_radius + 1e-12,
        "decisions": [
            {
                "observed_radius": value,
                "support_contained": support_contained,
                "selected_mode": "specialized-safe" if value <= robust_radius + 1e-12 and support_contained else "detect-only-safe-fallback",
                "reason": (
                    "certificate_contains_confidence_region"
                    if value <= robust_radius + 1e-12 and support_contained
                    else "undeclared_error_support"
                    if not support_contained
                    else "radius_outside_certificate_envelope"
                ),
            }
            for value, support_contained in [
                (0.0, True),
                (0.1, True),
                (shifted_distance, True),
                (robust_radius, True),
                (shifted_distance, False),
            ]
        ],
        "no_uncertified_selection": True,
    }
    audits = {
        "existing_exact_vs_known_baseline": classify_code(
            synthesized, reference_code=baseline, geometry={"rows": 2, "columns": 4}
        ),
        "robust_cosynthesized_vs_known_baseline": classify_code(
            robust_code, reference_code=baseline, geometry={"rows": 2, "columns": 4}
        ),
    }
    reconcile = {
        "status": "not_comparable_rejected",
        "scalable_single_regime": {
            "value": 0.016084921904981064,
            "meaning": "residual conditional probability for one spatial-hotspot PMF",
            "config": "configs/code_synthesis_64.example.json",
            "experiment_scope": "one code, one PMF, 20 beam iterations, beam width 4",
        },
        "portfolio_weighted": {
            "value": 0.40076616432862155,
            "meaning": "0.55*spatial residual 0.3114362399 + 0.45*geometry residual 0.5099471831",
            "config": "configs/portfolio_cosynthesis.example.json",
            "experiment_scope": "two PMFs, two specialized modes, 3 co-synthesis iterations, beam width 2",
        },
        "general_portfolio_baseline": {
            "value": 0.5105282172559964,
            "meaning": "same two-regime weights applied to one general generated code",
            "experiment_scope": "portfolio experiment baseline, not the single-regime 0.016 code",
        },
        "reason": "The 0.016 run and portfolio runs have different PMF universes/objectives/search budgets; only records with one experiment_id enter the authoritative table.",
    }
    figures = _plot_study(output, records, curves, heldout, safety_radii, scheduler)
    _write(output / "comparison.json", comparison)
    _write(
        output / "strategy_risk_certificates.json",
        {
            strategy_id: {
                "sdc": report["certificates"]["sdc"],
                "due": report["certificates"]["due"],
                "residual": report["certificates"]["residual"],
            }
            for strategy_id, report in evaluations.items()
        },
    )
    _write(
        output / "adversarial_sdc_summary.json",
        {
            strategy_id: {
                "worst_case_sdc": report["certificates"]["sdc"]["worst_case_risk"],
                "adversarial_pmf": report["certificates"]["sdc"]["adversarial_pmf"],
                "patterns_receiving_probability": report["certificates"]["sdc"]["patterns_receiving_probability"],
                "certificate_sha256": report["certificates"]["sdc"]["certificate_sha256"],
            }
            for strategy_id, report in evaluations.items()
        },
    )
    _write(output / "mapping_ablation.json", mapping_ablation)
    _write(output / "heldout_shift.json", {"tv_distance": shifted_distance, "strategies": heldout})
    _write(output / "risk_curves.json", curves)
    _write(output / "safety_radii.json", safety_radii)
    _write(output / "scheduler_gate.json", scheduler)
    _write(output / "equivalence_audits.json", audits)
    _write(output / "robust_cosynthesis.json", robust_cosynthesis)
    _write(output / "robust_cosynthesized_code.json", robust_code)
    _write(output / "comparison_reconciliation.json", reconcile)
    _write(output / "support.json", support_document(support, bit_width=8))
    _write(output / "figure_manifest.json", {"format": "SVG vector", "figures": figures})
    source_paths = [
        root / "codeforge" / name
        for name in (
            "ambiguity.py",
            "equivalence.py",
            "experiments.py",
            "robust.py",
            "robust_synthesis.py",
            "safeforge_study.py",
        )
    ] + [
        root / "scripts" / "run_safeforge_study.py",
        root / "configs" / "ambiguity" / "tv_small_example.json",
        root / "configs" / "fault_distributions" / "small_hotspot_8bit.json",
        root / "configs" / "fault_distributions" / "small_shifted_8bit.json",
        root / "reports" / "code_synthesis" / "code.json",
        root / "reports" / "code_synthesis" / "baselines" / "odd_column_secded_code.json",
    ]
    source_hashes = {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source_paths
    }
    source_tree_hash = hashlib.sha256(
        "".join(f"{path}:{digest}\n" for path, digest in sorted(source_hashes.items())).encode()
    ).hexdigest()
    files = {
        path.relative_to(output).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "result_manifest.json"
    }
    _write(
        output / "result_manifest.json",
        {
            "manifest_version": 1,
            "experiment_id": identity["experiment_id"],
            "source_tree_sha256": source_tree_hash,
            "source_files": source_hashes,
            "files": files,
            "reproduction_command": "python scripts/run_safeforge_study.py",
        },
    )
    return {
        "experiment_id": identity["experiment_id"],
        "strategies": records,
        "safety_radii": safety_radii,
        "heldout_shift_tv_distance": shifted_distance,
        "scheduler": scheduler,
        "equivalence": audits,
        "figures": figures,
        "output_directory": str(output),
    }
