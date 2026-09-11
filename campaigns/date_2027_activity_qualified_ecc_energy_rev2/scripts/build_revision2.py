#!/usr/bin/env python3
"""Build the additive DATE 2027 Rev. 2 controls, ledgers, and manifests."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
BASE_BUILDER = ROOT / "scripts/build_artifacts.py"
REV2_EVID = REPO / "docs/date2027/revision2/results/REV2_MANUSCRIPT_EVIDENCE.json"
SECDED_FORMAL = REPO / "docs/date2027/rigour_gate_03r/SECDED_PROOF_SUMMARY.json"
SECDED_CONTRACT = REPO / "docs/date2027/rigour_gate_03r/H2_ARCHITECTURE_CONTRACT.md"
STRUCTURAL = REPO / "campaigns/date_2027_breadth_remediation/analysis/A_structural_pair_summary.json"
STRUCTURAL_FORMAL = REPO / "campaigns/date_2027_breadth_remediation/formal/results/A_formal_qualification.json"
CONDITION = REPO / "campaigns/date_2027_breadth_remediation/analysis/C_5ns_summary.json"
SYNTHESIS = REPO / "campaigns/date_2027_breadth_remediation/synthesis/A_synthesis_structural_comparison.json"
CURRENT_INPUT = REPO / "campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5/E5_MATCHED_SEED_DELTAS.csv"
SEEDS = [11, 13, 17, 19, 23]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_csv(path: Path, fields: list[str], records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def effect(payload: dict, key: str) -> dict:
    return payload[key]["percent_effect"]


def temporal_effect(payload: dict, key: str) -> dict:
    return payload["secded_paired"]["effects"][key]["summary"]


def run_activity_builder() -> None:
    spec = importlib.util.spec_from_file_location("date2027_activity_builder", BASE_BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load activity builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()


def build_control_data() -> dict:
    rev2 = load_json(REV2_EVIDENCE := REV2_EVIDENCE_PATH())
    structural = load_json(STRUCTURAL)
    condition = load_json(CONDITION)
    sec_formal = load_json(SECDED_FORMAL)
    hs_formal = load_json(STRUCTURAL_FORMAL)

    data = {
        "schema_version": 1,
        "delta_conventions": {
            "temporal": "pipelined minus combinational, divided by combinational, percent",
            "structural": "hierarchical minus flat, divided by flat, percent",
            "activity": "Hsiao minus conventional",
        },
        "seed_set": SEEDS,
        "temporal_secded_10ns": {
            "standard_cell_area_percent": temporal_effect(rev2, "area_percent"),
            "signed_slack_frequency_metric_percent": temporal_effect(rev2, "slack_derived_frequency_percent"),
            "energy_per_operation_percent": temporal_effect(rev2, "achievable_energy_percent"),
            "direction_preserved_count": 5,
            "request_latency_cycles": {"combinational": 1, "pipelined": 3},
            "initiation_interval_cycles": {"combinational": 1, "pipelined": 1},
        },
        "temporal_secded_5ns": {
            "standard_cell_area_percent": effect(condition["within_5ns_paired_effects"], "standard_cell_instance_area_um2"),
            "signed_slack_frequency_metric_percent": effect(condition["within_5ns_paired_effects"], "slack_derived_frequency_mhz"),
            "energy_per_operation_percent": effect(condition["within_5ns_paired_effects"], "energy_per_op_pj"),
            "direction_preserved_count": 5,
            "request_latency_cycles": {"combinational": 1, "pipelined": 3},
            "initiation_interval_cycles": {"combinational": 1, "pipelined": 1},
        },
        "structural_hsiao_10ns": {
            "standard_cell_area_percent": effect(structural["paired_effects"], "standard_cell_instance_area_um2"),
            "detailed_wire_percent": effect(structural["paired_effects"], "detailed_route_wirelength_um"),
            "via_count_percent": effect(structural["paired_effects"], "via_count"),
            "signed_slack_frequency_metric_percent": effect(structural["paired_effects"], "slack_derived_frequency_mhz"),
            "energy_per_operation_percent": effect(structural["paired_effects"], "energy_per_op_pj"),
            "request_latency_cycles": 1,
            "initiation_interval_cycles": 1,
        },
        "bch_feasibility_10ns": {
            "realization": "shortened BCH(78,64,t=2) syndrome/Chien RTL",
            "timing_feasible_count": 0,
            "attempt_count": 5,
        },
        "formal_status": {
            "temporal_secded": sec_formal["status"],
            "structural_hsiao": hs_formal["formal_status"],
        },
        "source_hashes": {
            str(path.relative_to(REPO)).replace("\\", "/"): sha256(path)
            for path in (REV2_EVIDENCE, SECDED_FORMAL, SECDED_CONTRACT, STRUCTURAL, STRUCTURAL_FORMAL, CONDITION, SYNTHESIS, CURRENT_INPUT)
        },
    }
    (ROOT / "data/controlled_implementation_statistics.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )
    return data


def REV2_EVIDENCE_PATH() -> Path:
    return REV2_EVID


def append_macros(data: dict) -> None:
    temporal10 = data["temporal_secded_10ns"]
    temporal5 = data["temporal_secded_5ns"]
    hsiao = data["structural_hsiao_10ns"]
    with (ROOT / "data/derived_statistics.json").open(encoding="utf-8") as stream:
        activity = json.load(stream)
    comp_rows = list(csv.DictReader((ROOT / "data/component_power_deltas.csv").open(newline="", encoding="utf-8")))
    groups: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in comp_rows:
        groups[(row["operation"], row["component"])].append(float(row["power_delta_uW"]))

    def avg(op: str, component: str) -> float:
        values = groups[(op, component)]
        return sum(values) / len(values)

    energy = {row["operation"]: row for row in activity["operation_statistics"]}
    macro_values = {
        "TemporalTenArea": temporal10["standard_cell_area_percent"]["mean"],
        "TemporalTenTiming": temporal10["signed_slack_frequency_metric_percent"]["mean"],
        "TemporalTenEnergy": temporal10["energy_per_operation_percent"]["mean"],
        "TemporalFiveArea": temporal5["standard_cell_area_percent"]["mean"],
        "TemporalFiveTiming": temporal5["signed_slack_frequency_metric_percent"]["mean"],
        "TemporalFiveEnergy": temporal5["energy_per_operation_percent"]["mean"],
        "StructuralArea": hsiao["standard_cell_area_percent"]["mean"],
        "StructuralWire": hsiao["detailed_wire_percent"]["mean"],
        "StructuralVias": hsiao["via_count_percent"]["mean"],
        "StructuralTiming": hsiao["signed_slack_frequency_metric_percent"]["mean"],
        "StructuralEnergy": hsiao["energy_per_operation_percent"]["mean"],
        "ReadInternal": avg("clean_read", "internal"),
        "ReadSwitching": avg("clean_read", "switching"),
        "ReadDynamic": avg("clean_read", "internal") + avg("clean_read", "switching"),
        "ReadLeakage": avg("clean_read", "leakage"),
        "CorrectInternal": avg("correction", "internal"),
        "CorrectSwitching": avg("correction", "switching"),
        "CorrectDynamic": avg("correction", "internal") + avg("correction", "switching"),
        "CorrectLeakage": avg("correction", "leakage"),
        "DetectInternal": avg("detection", "internal"),
        "DetectSwitching": avg("detection", "switching"),
        "DetectDynamic": avg("detection", "internal") + avg("detection", "switching"),
        "DetectLeakage": avg("detection", "leakage"),
        "ReadEnergy": energy["clean_read"]["mean_delta_pJ"],
        "WriteEnergy": energy["clean_write"]["mean_delta_pJ"],
        "CorrectEnergy": energy["correction"]["mean_delta_pJ"],
        "DetectEnergy": energy["detection"]["mean_delta_pJ"],
        "IdleEnergy": energy["idle"]["mean_delta_pJ"],
        "ReadWriteCrossover": energy["clean_write"]["mean_delta_pJ"] / (
            energy["clean_write"]["mean_delta_pJ"] - energy["clean_read"]["mean_delta_pJ"]
        ) * 100.0,
    }
    macro_path = ROOT / "tables/generated_macros.tex"
    with macro_path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write("% Rev. 2 control and component macros\n")
        for name, value in macro_values.items():
            digits = 3 if name.startswith("Structural") else (4 if name.endswith("Energy") or name.endswith("Crossover") else 2)
            stream.write(f"\\newcommand{{\\{name}}}{{{value:.{digits}f}}}\n")

    component_summary = []
    for op in ("idle", "clean_write", "clean_read", "correction", "detection"):
        internal = avg(op, "internal")
        switching = avg(op, "switching")
        leakage = avg(op, "leakage")
        component_summary.append({
            "operation": op,
            "matched_seed_count": energy[op]["n"],
            "mean_internal_delta_uW": f"{internal:.9f}",
            "mean_switching_delta_uW": f"{switching:.9f}",
            "mean_dynamic_delta_uW": f"{internal + switching:.9f}",
            "mean_leakage_delta_uW": f"{leakage:.9f}",
            "mean_total_energy_delta_pJ_per_operation": f"{energy[op]['mean_delta_pJ']:.9f}",
        })
    write_csv(
        ROOT / "data/component_power_summary.csv",
        list(component_summary[0]),
        component_summary,
    )


def write_control_table(data: dict) -> None:
    t10 = data["temporal_secded_10ns"]
    t5 = data["temporal_secded_5ns"]
    hs = data["structural_hsiao_10ns"]
    lines = [
        r"\begin{table*}[t]",
        r"\caption{Controlled implementation space. Controls establish why hardware and condition are frozen before the main activity substitution. Effects are changed minus baseline, paired within seed.}",
        r"\label{tab:implementation-controls}",
        r"\centering\scriptsize\setlength{\tabcolsep}{2.7pt}",
        r"\begin{tabular}{@{}p{1.55cm}p{2.05cm}p{2.55cm}p{1.3cm}p{4.65cm}p{2.05cm}@{}}",
        r"\toprule",
        r"Study & Change & Held fixed / qualification & Cond.; pairs & Main observed effect & Role here \\",
        r"\midrule",
        rf"Temporal SECDED & combinational $\rightarrow$ pipelined & Same (72,64) transaction relation; exact alignment; II=1 & 10 ns; 5 & Area ${t10['standard_cell_area_percent']['mean']:+.1f}\%$, timing ${t10['signed_slack_frequency_metric_percent']['mean']:+.1f}\%$, energy/op ${t10['energy_per_operation_percent']['mean']:+.1f}\%$; directions 5/5; latency 1$\rightarrow$3 cycles & Hardware identity control \\",
        rf"Temporal SECDED & same RTL pair under tighter target & Same qualification and pair identities & 5 ns; 5 & Area ${t5['standard_cell_area_percent']['mean']:+.1f}\%$, timing ${t5['signed_slack_frequency_metric_percent']['mean']:+.1f}\%$, energy/op ${t5['energy_per_operation_percent']['mean']:+.1f}\%$; directions 5/5 & Condition control; not activity replication \\",
        rf"Structural Hsiao & flat $\rightarrow$ hierarchical decode & Same matrix, interface, latency=1, II=1; exact arbitrary-word and boundary proofs & 10 ns; 5 & Area ${hs['standard_cell_area_percent']['mean']:+.3f}\%$, wire ${hs['detailed_wire_percent']['mean']:+.3f}\%$, vias ${hs['via_count_percent']['mean']:+.3f}\%$, timing ${hs['signed_slack_frequency_metric_percent']['mean']:+.3f}\%$, energy ${hs['energy_per_operation_percent']['mean']:+.3f}\%$ & Small mixed structural control \\",
        r"BCH feasibility & stronger W1/W2-correcting realization & Named syndrome/Chien RTL; common physical target & 10 ns; 5 & Evaluated realization timing-feasible in 0/5 attempts & Categorical admission boundary \\",
        r"Main activity study & conventional SECDED $\leftrightarrow$ Hsiao & Interface/reliability contract, 10-ns flow, matched physical identities & 10 ns; 5 & Vectorless favors Hsiao 5/5; operation-specific energy favors it 4/23 & Principal experiment \\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
        "",
    ]
    (ROOT / "tables/controlled_implementation_space.tex").write_text("\n".join(lines), encoding="utf-8")


def write_formal_matrix() -> None:
    records = [
        {
            "architecture pair": "conventional combinational SECDED vs conventional pipelined SECDED",
            "semantic relation": "same systematic extended-Hamming (72,64) transaction relation and status behavior",
            "formal method": "zero-plus-basis affine encoder proof; compositional arbitrary-word decoder proof; exhaustive W2/W3 replay",
            "alignment": "pipelined response shifted by two cycles",
            "latency": "1 vs 3 request cycles",
            "II": "1 vs 1",
            "proof status": "PASS",
            "manuscript wording": "Exact encoder and decoder transaction behavior after two-cycle response alignment.",
        },
        {
            "architecture pair": "flat Hsiao vs hierarchical-nibble Hsiao",
            "semantic relation": "same Hsiao matrix, codeword, correction/status relation, interface, and temporal contract",
            "formal method": "SAT for arbitrary 72-bit received words; temporal induction at registered boundary",
            "alignment": "same cycle; zero-cycle alignment",
            "latency": "1 vs 1 request cycle",
            "II": "1 vs 1",
            "proof status": "PASS",
            "manuscript wording": "Exact arbitrary-word decoder equality and same-cycle registered transaction equality.",
        },
        {
            "architecture pair": "conventional SECDED vs Hsiao SECDED",
            "semantic relation": "same interface and W1-correction/W2-detection contract; internal codewords differ",
            "formal method": "directed/randomized interface and memory-semantics qualification; coding-theoretic guarantees",
            "alignment": "same external transaction boundary",
            "latency": "matched in current experiment",
            "II": "matched in current experiment",
            "proof status": "QUALIFIED_NOT_EXACT_CODEWORD_EQUIVALENCE",
            "manuscript wording": "Interface/correction semantics are qualified; exact internal codeword equivalence is not claimed.",
        },
        {
            "architecture pair": "SECDED/Hsiao vs BCH(78,64,t=2)",
            "semantic relation": "different guarantee; BCH corrects W1/W2 while SECDED corrects W1 and detects W2",
            "formal method": "symbolic payload proofs over all required W0/W1/W2 masks for named BCH realization",
            "alignment": "not an equivalence comparison",
            "latency": "categorical requirement",
            "II": "implementation-specific",
            "proof status": "BCH_GUARANTEE_QUALIFIED",
            "manuscript wording": "BCH is a stronger-correction feasibility boundary, not an equal-semantics energy competitor.",
        },
    ]
    write_csv(ROOT / "FORMAL_QUALIFICATION_MATRIX.csv", list(records[0]), records)


def write_audit_documents(data: dict) -> None:
    t10 = data["temporal_secded_10ns"]
    t5 = data["temporal_secded_5ns"]
    hs = data["structural_hsiao_10ns"]
    (ROOT / "PREVIOUS_MANUSCRIPT_AUDIT_UPDATED.md").write_text(f"""# Previous Manuscript Audit - Updated

The previous identity-focused manuscript remains evidentially useful but is not the narrative baseline. Its temporal SECDED, structural Hsiao, constraint-replication, component-accounting, and BCH results are qualified controls. Campaign history, infrastructure chronology, internal gate labels, and version history remain repository-only.

| Evidence | Disposition in Rev. 2 | Reason |
|---|---|---|
| Matched deterministic seeds | Central | Pairing is required for the main activity claim. |
| Timing, final SPEF, final netlist, VCD, coverage, energy normalization | Central | Directly qualifies the activity substitution. |
| Temporal SECDED at 10 ns | Compact control | Shows that exact transaction equivalence does not freeze physical behavior; mean area {t10['standard_cell_area_percent']['mean']:+.3f}%, timing {t10['signed_slack_frequency_metric_percent']['mean']:+.3f}%, energy {t10['energy_per_operation_percent']['mean']:+.3f}%. |
| Temporal SECDED at 5 ns | Compact control | Shows condition-dependent magnitude; it is not a 5-ns Hamming/Hsiao activity replication. |
| Flat/hierarchical Hsiao | Compact control | Shows a modest mixed displacement, so identity does not predict effect size or sign. |
| BCH(78,64,t=2) | Feasibility boundary | The named realization is 0/5 timing-feasible at 10 ns; no BCH-family claim is made. |
| Historical narration/logging | Repository only | Useful for provenance, not for the six-page argument. |
""", encoding="utf-8")

    (ROOT / "CURRENT_MANUSCRIPT_AUDIT.md").write_text("""# Current Manuscript Audit

The activity-focused baseline correctly centers estimator substitution, five matched seeds, final-netlist VCD, final SPEF association, 46 qualified records, 23 matched cells, coverage, and the ECC-logic boundary. The revision retains these claims and all four activity figures.

Required changes applied in Rev. 2:

- the unsupported broad absence claim was narrowed to a documented awareness statement after re-checking the closest Hamming/Hsiao trace-power comparator;
- the component discussion now says "consistent with" rather than asserting a causal mechanism;
- all 72 output roots are described as represented activity roots, not as proof of workload completeness;
- exact-equivalence wording is restricted to the temporal SECDED and structural Hsiao pairs;
- the long replication protocol is condensed, with the full audit package retained;
- Q1 hardware identity and Q2 implementation condition appear only as controls for Q3 activity identity.
""", encoding="utf-8")

    (ROOT / "CONTROLLED_IMPLEMENTATION_EVIDENCE.md").write_text(f"""# Controlled Implementation Evidence

## Q1 - Hardware identity

The conventional combinational/pipelined SECDED pair implements the same systematic (72,64) transaction relation after a two-cycle response alignment. Request latency is one versus three cycles and II is one for both. At 10 ns, the paired mean changes are area {t10['standard_cell_area_percent']['mean']:+.6f}%, signed-slack timing metric {t10['signed_slack_frequency_metric_percent']['mean']:+.6f}%, and energy/op {t10['energy_per_operation_percent']['mean']:+.6f}%; all three directions hold in 5/5 seeds.

The flat/hierarchical Hsiao pair holds matrix, interface, latency, and II fixed. Hierarchical minus flat means are area {hs['standard_cell_area_percent']['mean']:+.9f}%, detailed wire {hs['detailed_wire_percent']['mean']:+.9f}%, vias {hs['via_count_percent']['mean']:+.9f}%, timing {hs['signed_slack_frequency_metric_percent']['mean']:+.9f}%, and energy {hs['energy_per_operation_percent']['mean']:+.9f}%. The mixed small changes are a counterexample to any assumption that distinct implementation identities must have large effects.

## Q2 - Implementation condition

At 5 ns, the same temporal pair has mean area {t5['standard_cell_area_percent']['mean']:+.9f}%, timing {t5['signed_slack_frequency_metric_percent']['mean']:+.9f}%, and energy {t5['energy_per_operation_percent']['mean']:+.9f}%; directions hold in 5/5 seeds. These are fresh implementations of the temporal pair. They do not replicate the current conventional/Hsiao activity study at 5 ns.

## Feasibility boundary

The evaluated BCH(78,64,t=2) syndrome/Chien realization provides W1/W2 correction but meets the common 10-ns target in 0/5 matched implementation attempts. The result is identity-scoped and is not a claim about BCH as a family.

## Interpretation

Implementation identity determines what must be measured separately; it does not predict the magnitude or sign of the resulting physical displacement. These controls justify freezing hardware identity and physical condition before Q3 substitutes the activity model.
""", encoding="utf-8")

    (ROOT / "DATE2027_TERMINOLOGY_MAP.md").write_text("""# DATE 2027 Terminology Map

| Internal/repository term | Reader-facing term |
|---|---|
| E4 | vectorless post-route power estimation |
| E5 | operation-specific activity-aware post-route energy |
| U0 | unprotected/no-ECC baseline |
| Gate/Level labels | qualification step or timing-feasible routed implementation |
| GREEN version labels | omitted from manuscript; retained only in provenance paths |
| seed | matched deterministic physical-design perturbation |
| final VCD | final-routed-gate-netlist zero-delay VCD |
| power decomposition | tool-reported internal, net-switching, leakage, dynamic, and total accounting |
""", encoding="utf-8")

    (ROOT / "DATE2027_TITLE_AUDIT.md").write_text("""# Title Audit

| Candidate | D9/D13 fit | Clarity | Distinction | Decision |
|---|---|---|---|---|
| When ECC Energy Ordering Depends on Activity: A Matched Post-Route Study | Strong primary D9, clear secondary D13 | Direct | Distinct from the previous identity paper | Selected |
| Activity-Conditioned Energy Ordering of Physically Qualified ECC Hardware | Strong | Precise but dense | Good | Reserve |
| From Hardware Identity to Activity-Conditioned Energy: A Matched ECC Study | Balanced | Longer | Too close to previous title pattern | Reject |
| Physical and Activity Identity in ECC Energy Evaluation | D13-forward | Abstract | Moderate | Reject |
| Do ECC Power Rankings Survive Operation-Specific Activity? | D9-forward | Accessible | Less precise because the result is energy/op | Reject |

The current title is retained because it names the principal variable and the matched post-route design without elevating the supporting identity controls.
""", encoding="utf-8")


def extend_figure_manifest() -> None:
    path = ROOT / "DATE2027_FIGURE_MANIFEST.csv"
    records = list(csv.DictReader(path.open(newline="", encoding="utf-8")))
    fields = list(records[0])
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    for folder, tier, disposition in (
        ("current_baseline", "CURRENT_BASELINE", "preserved; not included"),
        ("superseded_but_preserved", "SUPERSEDED_BUT_PRESERVED", "historical control-paper figure; not included"),
    ):
        for p in sorted((ROOT / f"figures/{folder}").glob("*")):
            if not p.is_file():
                continue
            records.append({
                "figure_id": p.stem,
                "tier": tier,
                "purpose": "Preserved prior manuscript visual",
                "format": p.suffix.lstrip("."),
                "path": str(p.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256(p),
                "source_data": "preserved upstream artifact",
                "source_data_sha256": "NOT_APPLICABLE",
                "generation_script": "preserved; see upstream package",
                "generated_date": "2026-09-10",
                "repository_head": head,
                "sealed_source_commit": "see upstream provenance",
                "manuscript_disposition": disposition,
            })
    write_csv(path, fields, records)


def preserve_historical_figures() -> None:
    target = ROOT / "figures/superseded_but_preserved"
    target.mkdir(parents=True, exist_ok=True)
    source = REPO / "paper/date2027_revision3/figures"
    for p in source.glob("*.pdf"):
        shutil.copy2(p, target / f"previous_{p.name}")


def main() -> int:
    run_activity_builder()
    preserve_historical_figures()
    data = build_control_data()
    append_macros(data)
    write_control_table(data)
    write_formal_matrix()
    write_audit_documents(data)
    extend_figure_manifest()
    print(json.dumps({
        "status": "PASS",
        "activity_pairs": 23,
        "temporal_control_pairs": 10,
        "structural_control_pairs": 5,
        "bch_attempts": 5,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
