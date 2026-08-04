"""Exact-functional and explicitly analytical multi-ECC scenario study.

No value produced here is physical PPA.  Exact fields arise from manifests,
matrices, or exhaustive decoder execution.  Energy, carbon, and scenario
reliability fields are sensitivity-model outputs and carry their model and
parameter provenance inline.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations, product
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .backends import PHYSICAL_FIELDS
from .contracts import DecodeStatus
from .hashing import canonical_hash, file_sha256
from .registry import EccRegistry


OUTCOME_CORRECTED = "corrected_to_golden_data"
OUTCOME_DUE = "detected_uncorrectable_or_abstained"
OUTCOME_SDC = "silent_miscorrection"
MODEL_LEVEL = "analytical_sensitivity"


def _write(path: Path, payload: Mapping[str, Any] | Sequence[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _analytical(value: float, unit: str, config: Mapping[str, Any], *, interval: Sequence[float] | None = None) -> dict[str, Any]:
    model = config["analytical_model"]
    result: dict[str, Any] = {
        "value": value,
        "unit": unit,
        "model_id": model["model_id"],
        "parameter_provenance": model["provenance"],
        "evidence_level": MODEL_LEVEL,
    }
    if interval is not None:
        result["sensitivity_interval"] = list(interval)
    return result


def _outcome(result: Any, golden: int = 0) -> str:
    if result.status in {DecodeStatus.NO_ERROR, DecodeStatus.CORRECTED}:
        return OUTCOME_CORRECTED if result.data == golden else OUTCOME_SDC
    return OUTCOME_DUE


def _pattern_summary(adapter: Any, patterns: Iterable[tuple[int, ...]]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    first_counterexample: dict[str, list[int]] = {}
    clean = adapter.encode(0)
    total = 0
    for positions in patterns:
        result = adapter.decode(clean ^ sum(1 << position for position in positions))
        outcome = _outcome(result)
        counts[outcome] += 1
        status_counts[result.status.value] += 1
        first_counterexample.setdefault(outcome, list(positions))
        total += 1
    return {
        "patterns": total,
        "outcome_counts": {
            OUTCOME_CORRECTED: counts[OUTCOME_CORRECTED],
            OUTCOME_DUE: counts[OUTCOME_DUE],
            OUTCOME_SDC: counts[OUTCOME_SDC],
        },
        "outcome_fractions": {
            key: {"numerator": counts[key], "denominator": total, "exact_fraction": f"{counts[key]}/{total}"}
            for key in (OUTCOME_CORRECTED, OUTCOME_DUE, OUTCOME_SDC)
        },
        "decoder_status_counts": dict(sorted(status_counts.items())),
        "representative_patterns": dict(sorted(first_counterexample.items())),
        "evidence_level": "exact_exhaustive_canonical_codeword",
        "data_independence_proof": "linear encoder and translation-invariant deterministic syndrome policy",
    }


def exact_error_profiles(registry: EccRegistry, implementation_id: str) -> dict[str, Any]:
    implementation = registry.implementation(implementation_id)
    code = registry.code(str(implementation["code_id"]))
    adapter = registry.adapter(implementation_id)
    n = int(code["n"])
    adjacent_pairs = {tuple(range(start, start + 2)) for start in range(n - 1)}
    adjacent_triples = {tuple(range(start, start + 3)) for start in range(n - 2)}
    profiles = {
        "single": _pattern_summary(adapter, ((position,) for position in range(n))),
        "adjacent_double": _pattern_summary(adapter, iter(sorted(adjacent_pairs))),
        "nonadjacent_double": _pattern_summary(
            adapter, (positions for positions in combinations(range(n), 2) if positions not in adjacent_pairs)
        ),
        "adjacent_triple": _pattern_summary(adapter, iter(sorted(adjacent_triples))),
        "nonadjacent_triple": _pattern_summary(
            adapter, (positions for positions in combinations(range(n), 3) if positions not in adjacent_triples)
        ),
    }
    result: dict[str, Any] = {
        "schema_version": 1,
        "profile_id": f"exact-error-profile-{implementation_id}",
        "code_spec_id": code.get("code_spec_id", code["code_id"]),
        "encoder_id": implementation.get("encoder_id"),
        "implementation_id": implementation_id,
        "decoder_policy_id": implementation["decoder_policy_id"],
        "n": n, "k": int(code["k"]),
        "adjacency_definition": "consecutive canonical encoded-codeword coordinates; no cross-codeword boundary",
        "classes": profiles,
    }
    result["profile_sha256"] = canonical_hash(result)
    return result


def payload_normalization(k: int, n: int) -> dict[str, Any]:
    def payload(bits: int) -> dict[str, Any]:
        codewords = math.ceil(bits / k)
        return {
            "information_payload_bits": bits,
            "codewords_required": codewords,
            "encoded_bits": codewords * n,
            "padding_information_bits": codewords * k - bits,
            "fragmented": codewords > 1,
            "fragmentation_policy": "ceil(payload/k) independent systematic codewords; final unused information coordinates fixed to zero",
        }
    return {
        "per_information_bit_encoded_bits": n / k,
        "protected_64b_word": payload(64),
        "protected_512b_cache_line": payload(512),
        "equal_data_capacity_scaling": {"encoded_bits_per_information_bit": n / k},
    }


def structural_metrics(registry: EccRegistry, implementation_id: str) -> dict[str, Any]:
    implementation = registry.implementation(implementation_id)
    code = registry.code(str(implementation["code_id"]))
    g = code["_resolved_matrix"]["G"]
    h = code["_resolved_matrix"]["H"]
    k, n = int(code["k"]), int(code["n"])
    parity_inputs = [sum(int(g[row][col]) for row in range(k)) for col in range(k, n)]
    syndrome_inputs = [sum(map(int, row)) for row in h]
    encoder_xors = sum(max(0, value - 1) for value in parity_inputs)
    syndrome_xors = sum(max(0, value - 1) for value in syndrome_inputs)
    adapter = registry.adapter(implementation_id)
    decoder_entries = len(
        getattr(adapter, "_locator", getattr(adapter, "_correction_map", getattr(adapter, "_single_map", {})))
    )
    correction_mask_ones = 0
    for mapping_name in ("_locator", "_correction_map"):
        mapping = getattr(adapter, mapping_name, None)
        if mapping:
            correction_mask_ones = sum(len(value) for value in mapping.values())
            break
    if not correction_mask_ones:
        correction_mask_ones = decoder_entries
    comparator_literals = decoder_entries * int(code["redundancy"])
    decoder_complexity = syndrome_xors + comparator_literals + correction_mask_ones
    max_fanin = max([1, *parity_inputs, *syndrome_inputs])
    logic_depth = math.ceil(math.log2(max_fanin)) + (math.ceil(math.log2(max(1, decoder_entries))) if decoder_entries else 0)
    return {
        "encoder_xor_operations": encoder_xors,
        "syndrome_xor_operations": syndrome_xors,
        "decoder_table_entries": decoder_entries,
        "decoder_compare_literals": comparator_literals,
        "correction_mask_ones": correction_mask_ones,
        "decoder_complexity_proxy": decoder_complexity,
        "logic_depth_proxy": logic_depth,
        "generic_structural_cell_count": None,
        "metric_class": "exact_matrix_counts_and_technology_independent_structural_proxies",
        "physical_interpretation": None,
    }


def _fraction(profile: Mapping[str, Any], class_id: str, outcome: str) -> float:
    item = profile["classes"][class_id]["outcome_fractions"][outcome]
    return float(item["numerator"]) / float(item["denominator"])


def _scenario_axes(config: Mapping[str, Any]) -> Iterable[dict[str, Any]]:
    grid = config["grid"]
    keys = [
        "supply_voltage_v", "temperature_c", "scrub_interval_s",
        "carbon_intensity_kgco2_per_kwh", "fault_profile_ids", "workload_ids",
        "reliability_requirement_ids",
    ]
    for values in product(*(grid[key] for key in keys)):
        factors = dict(zip(keys, values))
        basis = {"study_id": config["study_id"], **factors}
        factors["scenario_id"] = "scenario-" + canonical_hash(basis)[:16]
        yield factors


def _candidate_metrics(
    registry: EccRegistry,
    implementation_id: str,
    profile: Mapping[str, Any],
    exact: Mapping[str, Any],
    scenario: Mapping[str, Any],
    config: Mapping[str, Any],
    *, uncertainty: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    uncertainty = uncertainty or {"bit_energy_scale": 1.0, "xor_energy_scale": 1.0, "leakage_scale": 1.0}
    implementation = registry.implementation(implementation_id)
    code = registry.code(str(implementation["code_id"]))
    probabilities = config["fault_profiles"][scenario["fault_profile_ids"]]["class_probability_per_codeword_access"]
    corrected_cw = sum(float(probabilities[name]) * _fraction(profile, name, OUTCOME_CORRECTED) for name in probabilities)
    due_cw = sum(float(probabilities[name]) * _fraction(profile, name, OUTCOME_DUE) for name in probabilities)
    sdc_cw = sum(float(probabilities[name]) * _fraction(profile, name, OUTCOME_SDC) for name in probabilities)
    normalized = exact["payload_normalization"]
    codewords_64 = int(normalized["protected_64b_word"]["codewords_required"])
    corrected_64 = 1.0 - (1.0 - corrected_cw) ** codewords_64
    due_64 = 1.0 - (1.0 - due_cw) ** codewords_64
    sdc_64 = 1.0 - (1.0 - sdc_cw) ** codewords_64

    workload = config["workloads"][scenario["workload_ids"]]
    model = config["analytical_model"]["parameters"]
    vscale = float(scenario["supply_voltage_v"]) ** 2
    bit_energy = float(model["bit_access_energy_j_at_1v"]) * vscale * float(uncertainty["bit_energy_scale"])
    xor_energy = float(model["xor_activity_energy_j_at_1v"]) * vscale * float(uncertainty["xor_energy_scale"])
    write_fraction = float(workload["write_fraction"])
    encoded_bits_64 = int(normalized["protected_64b_word"]["encoded_bits"])
    structural = exact["structural_metrics"]
    operations_per_codeword = float(structural["syndrome_xor_operations"]) + write_fraction * float(structural["encoder_xor_operations"])
    decoder_activity_ops = operations_per_codeword + (corrected_cw + due_cw + sdc_cw) * float(structural["decoder_complexity_proxy"])
    dynamic_per_payload = encoded_bits_64 * bit_energy + codewords_64 * decoder_activity_ops * xor_energy
    dynamic_total = dynamic_per_payload * int(workload["payload_accesses"])
    capacity_bits = int(config["equal_information_capacity_bits"])
    stored_codewords = math.ceil(capacity_bits / int(code["k"]))
    stored_bits = stored_codewords * int(code["n"])
    temperature_multiplier = 1.0 + (
        (float(scenario["temperature_c"]) - 25.0) / 60.0
    ) * (float(model["temperature_leakage_multiplier_at_85c"]) - 1.0)
    leakage_power = (
        stored_bits * float(model["leakage_power_w_per_stored_bit_at_25c"])
        * temperature_multiplier * float(uncertainty["leakage_scale"])
    )
    leakage_total = leakage_power * float(workload["lifetime_s"])
    scrub_count = float(workload["lifetime_s"]) / float(scenario["scrub_interval_s"])
    scrub_total = stored_bits * scrub_count * bit_energy * float(model["scrub_read_write_energy_multiplier"])
    total_energy = dynamic_total + leakage_total + scrub_total
    carbon = total_energy / 3.6e6 * float(scenario["carbon_intensity_kgco2_per_kwh"])
    requirement = config["reliability_requirements"][scenario["reliability_requirement_ids"]]
    feasible_sdc = sdc_64 <= float(requirement["max_sdc_probability_per_64b_access"])
    feasible_due = due_64 <= float(requirement["max_due_probability_per_64b_access"])
    return {
        "candidate_record_id": "candidate-" + canonical_hash({"scenario": scenario["scenario_id"], "implementation": implementation_id, "uncertainty": uncertainty})[:20],
        "code_spec_id": code.get("code_spec_id", code["code_id"]),
        "encoder_id": implementation.get("encoder_id"),
        "implementation_id": implementation_id,
        "decoder_policy_id": implementation["decoder_policy_id"],
        "architecture_id": implementation["compatible_deployment_architectures"][0],
        "backend_id": None,
        "evidence_level": "exact_functional_plus_analytical_sensitivity",
        "exact_metrics": exact,
        "analytical_metrics": {
            "expected_corrected_probability_per_64b_access": _analytical(corrected_64, "probability/access", config, interval=[max(0.0, corrected_64 * 0.5), min(1.0, corrected_64 * 1.5)]),
            "expected_due_probability_per_64b_access": _analytical(due_64, "probability/access", config, interval=[max(0.0, due_64 * 0.5), min(1.0, due_64 * 1.5)]),
            "expected_sdc_probability_per_64b_access": _analytical(sdc_64, "probability/access", config, interval=[max(0.0, sdc_64 * 0.5), min(1.0, sdc_64 * 1.5)]),
            "analytical_decoder_activity": _analytical(decoder_activity_ops * codewords_64, "structural_operations/64b_access", config),
            "modelled_dynamic_energy": _analytical(dynamic_total, "J/scenario", config, interval=[dynamic_total * 0.5, dynamic_total * 2.0]),
            "modelled_leakage_energy": _analytical(leakage_total, "J/scenario", config, interval=[leakage_total * 0.5, leakage_total * 1.5]),
            "scrub_energy": _analytical(scrub_total, "J/scenario", config, interval=[scrub_total * 0.5, scrub_total * 1.5]),
            "modelled_total_energy": _analytical(total_energy, "J/scenario", config, interval=[total_energy * 0.5, total_energy * 2.0]),
            "modelled_operational_carbon": _analytical(carbon, "kgCO2e/scenario", config, interval=[carbon * 0.5, carbon * 2.0]),
            "latency_uncertainty": _analytical(float(structural["logic_depth_proxy"]), "technology-independent logic-depth proxy", config, interval=[float(structural["logic_depth_proxy"]), float(structural["logic_depth_proxy"]) * 2.0]),
        },
        "physical_metrics": {field: None for field in PHYSICAL_FIELDS},
        "constraints": {"verification": True, "sdc": feasible_sdc, "due": feasible_due, "feasible": feasible_sdc and feasible_due},
    }


def _dominates(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    def values(item: Mapping[str, Any]) -> tuple[float, ...]:
        analytical = item["analytical_metrics"]
        exact = item["exact_metrics"]
        return (
            analytical["expected_sdc_probability_per_64b_access"]["value"],
            analytical["expected_due_probability_per_64b_access"]["value"],
            analytical["modelled_total_energy"]["value"],
            float(exact["payload_normalization"]["protected_64b_word"]["encoded_bits"]),
            float(exact["structural_metrics"]["decoder_complexity_proxy"]),
        )
    a, b = values(left), values(right)
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


def _pareto(candidates: Sequence[Mapping[str, Any]]) -> list[str]:
    return sorted(
        str(candidate["implementation_id"])
        for candidate in candidates
        if not any(_dominates(other, candidate) for other in candidates if other is not candidate)
    )


def _winner(candidates: Sequence[Mapping[str, Any]]) -> str | None:
    feasible = [candidate for candidate in candidates if candidate["constraints"]["feasible"]]
    if not feasible:
        return None
    return str(min(feasible, key=lambda item: (
        item["analytical_metrics"]["modelled_total_energy"]["value"],
        item["exact_metrics"]["structural_metrics"]["decoder_complexity_proxy"],
        item["exact_metrics"]["payload_normalization"]["protected_64b_word"]["encoded_bits"],
        item["implementation_id"],
    ))["implementation_id"])


def _scope_inventory(registry: EccRegistry, verification: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for code_id in sorted(registry.codes):
        code = registry.code(code_id)
        implementations = sorted(i for i, item in registry.implementations.items() if item["code_id"] == code_id)
        statuses = [verification[item]["verification_status"] for item in implementations]
        capability_statuses = [verification[item]["capability_verification_status"] for item in implementations]
        if all(status == "failed" for status in statuses):
            status = "integrated_rejected"
        elif "partially_verified" in capability_statuses:
            status = "integrated_partially_verified"
        else:
            status = "integrated_verified"
        rows.append({
            "candidate_id": code_id, "artifact_group": "registered mathematical code and deployed decoder(s)",
            "status": status, "code_spec_id": code.get("code_spec_id", code_id),
            "encoder_id": code.get("encoder_id"), "implementation_ids": implementations,
            "dimensions": {"n": code["n"], "k": code["k"], "redundancy": code["redundancy"]},
            "exact_minimum_distance": code.get("distance_evidence", {}).get("exact_minimum_distance"),
            "designed_distance_lower_bound": code.get("distance_evidence", {}).get("designed_distance_lower_bound"),
            "sources": [item["path"] for item in code["source_provenance"]],
            "selection_scope": "eligible subject to scenario constraints" if status != "integrated_rejected" else "excluded",
        })
    rows.extend([
        {"candidate_id": "cpp-bch63-reference", "artifact_group": "src/bch63.cpp, src/bch63.hpp, tests/unit/BCH63_test.cpp", "status": "duplicate_decoder_policy", "code_spec_id": "primitive-bch-63-51-t2-v1", "reason": "same primitive polynomial and systematic BCH construction; retained as independent source/test evidence for the registered reference"},
        {"candidate_id": "cpp-secdaec64", "artifact_group": "SecDaec64.hpp and tests/unit/SecDaec64_test.cpp", "status": "duplicate_decoder_policy", "code_spec_id": "extended-hamming-secded-72-64-v1", "reason": "positional extended-Hamming encoder with the same bounded adjacent-pair policy family; no distinct certified codeword set"},
        {"candidate_id": "generated-secded-width-family", "artifact_group": "rtl/ecc_generated/secded_{8,16,32,64}b.v", "status": "integrated_experimental", "reason": "complete generated RTL grouped in inventory; lacks archived matrix identity and differential certificate needed for scientific selection"},
        {"candidate_id": "generated-taec-width-family", "artifact_group": "rtl/ecc_generated/taec_{8,16,32,64}b.v", "status": "integrated_experimental", "reason": "complete generated RTL but no distinct TAEC matrix certificate; 64b policy is the same collision-prone positional construction"},
        {"candidate_id": "generated-secdaec-64", "artifact_group": "rtl/ecc_generated/secdaec_64b.v", "status": "duplicate_decoder_policy", "code_spec_id": "extended-hamming-secded-72-64-v1", "reason": "same positional extended-Hamming bounded adjacent-pair policy family"},
        {"candidate_id": "generated-bch-labelled-width-family", "artifact_group": "rtl/ecc_generated/bch_{8,16,32,51}b.v", "status": "integrated_rejected", "reason": "labelled BCH but uses ad-hoc parity equations, not primitive-field BCH generator construction; decoder equations are not certified against encoder"},
        {"candidate_id": "generated-polar-width-family", "artifact_group": "rtl/ecc_generated/polar_{8,16,32,48,96}b.v", "status": "integrated_experimental", "reason": "transform encoder exists but deployed block is not a deterministic SC/SCL SRAM error-correcting decoder"},
        {"candidate_id": "asic-polar-configurations", "artifact_group": "asic/rtl/polar and SRAM wrappers (16/8, 32/16, 64/32, 64/48, 128/96)", "status": "excluded_insufficient_evidence", "reason": "no correction guarantee and differential deployed-decoder certificate under a declared SRAM error model"},
        {"candidate_id": "polar-python-bound-model", "artifact_group": "polar.py", "status": "excluded_missing_decoder", "reason": "Bhattacharyya/SC block-error bound is a communication-channel analytical proxy, not an executable deployed SRAM decoder"},
        {"candidate_id": "taec-coverage-monte-carlo", "artifact_group": "taec_hamming_sim.py and fit.py aliases", "status": "excluded_missing_mathematical_definition", "reason": "coverage assumptions contain no G/H matrix or executable TAEC encoder/decoder"},
        {"candidate_id": "thesis-taec-75-64-i6-i7", "artifact_group": "required named-construction search", "status": "excluded_missing_mathematical_definition", "reason": "no (75,64)-I6/I7 matrix, generator, lookup table, RTL, or simulator was found in the repository"},
        {"candidate_id": "repository-hamming-cpp-simulators", "artifact_group": "Hamming32bit1Gb.cpp, Hamming64bit128Gb.cpp, BCHvsHamming.cpp, ParityCheckMatrix.hpp", "status": "excluded_insufficient_evidence", "reason": "workload/demo simulators and matrix helpers do not archive a distinct deployed code/decoder identity beyond registered constructions"},
        {"candidate_id": "repetition-external-fixture", "artifact_group": "tests/fixtures/multi_ecc_external", "status": "integrated_verified", "reason": "exhaustive framework extensibility fixture only; explicitly excluded from scientific portfolio"},
        {"candidate_id": "ldpc-reed-solomon-literature-only", "artifact_group": "documentation citations and family mentions", "status": "excluded_missing_encoder", "reason": "no repository encoder, deployed decoder, matrix/polynomial, or framing policy exists"},
        {"candidate_id": "legacy-family-energy-aliases", "artifact_group": "sram_ecc_benchmark.py, selector aliases, transition/revision reports", "status": "excluded_insufficient_evidence", "reason": "family-level analytical constants and synthetic winners are not bit-exact code/decoder implementations"},
    ])
    return rows


def _architecture_matrix(registry: EccRegistry, verification: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for implementation_id in sorted(registry.implementations):
        implementation = registry.implementation(implementation_id)
        for architecture_id in sorted(registry.architectures):
            compatible = architecture_id in implementation["compatible_deployment_architectures"]
            verified = verification[implementation_id]["verification_status"] == "passed"
            if not compatible:
                analytical_status = "incompatible"
                reason = "architecture is not declared compatible by the implementation manifest"
            elif not verified:
                analytical_status = "compatible_but_not_evaluated"
                reason = "implementation failed its guaranteed functional universe"
            else:
                analytical_status = "compatible_and_evaluated"
                reason = None
            rows.append({
                "implementation_id": implementation_id, "architecture_id": architecture_id,
                "analytical_status": analytical_status, "analytical_reason": reason,
                "physical_status": "blocked_by_missing_physical_evidence",
                "physical_reason": "MUX/controller/metadata/transition/re-encoding and implementation PPA are uncharacterized",
            })
    return rows


def _capability_matrix(registry: EccRegistry, verification: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for implementation_id in sorted(registry.implementations):
        implementation = registry.implementation(implementation_id)
        report = verification[implementation_id]
        rows.append({
            "code_spec_id": implementation.get("code_spec_id", implementation["code_id"]),
            "encoder_id": implementation.get("encoder_id"), "implementation_id": implementation_id,
            "decoder_policy_id": implementation["decoder_policy_id"],
            "verification_status": report["verification_status"],
            "capability_verification_status": report["capability_verification_status"],
            "verified_capabilities": implementation.get("verified_capabilities", []),
            "failed_capabilities": implementation.get("failed_capabilities", []) + report.get("capability_failures", []),
            "unsupported_capabilities": implementation.get("unsupported_capabilities", []),
            "class_results": report["class_results"],
            "representative_counterexamples": [item for result in report["class_results"] for item in result["failed_patterns"][:1]],
            "backend_id": None, "evidence_level": implementation.get("evidence_level"),
        })
    return rows


def _baseline_regret(scenarios: Sequence[Mapping[str, Any]], baseline_ids: Sequence[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for baseline_id in baseline_ids:
        regrets: list[float] = []
        ratios: list[float] = []
        infeasible = 0
        comparable = 0
        for scenario in scenarios:
            if scenario["winner"] is None:
                continue
            records = {item["implementation_id"]: item for item in scenario["candidate_records"]}
            baseline = records.get(baseline_id)
            winner = records[scenario["winner"]]
            if baseline is None or not baseline["constraints"]["feasible"]:
                infeasible += 1
                continue
            comparable += 1
            base_energy = baseline["analytical_metrics"]["modelled_total_energy"]["value"]
            win_energy = winner["analytical_metrics"]["modelled_total_energy"]["value"]
            regrets.append(base_energy - win_energy)
            ratios.append((base_energy - win_energy) / base_energy if base_energy else 0.0)
        result[baseline_id] = {
            "comparable_feasible_scenarios": comparable,
            "constraint_failure_or_missing_scenarios": infeasible,
            "total_analytical_energy_regret_j": sum(regrets),
            "mean_analytical_energy_regret_j": sum(regrets) / comparable if comparable else None,
            "max_analytical_energy_regret_j": max(regrets) if regrets else None,
            "mean_fractional_regret": sum(ratios) / comparable if comparable else None,
            "metric_evidence_level": MODEL_LEVEL,
        }
    return result


def _adaptive_threshold(scenarios: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    feasible_counts: Counter[str] = Counter()
    energies: defaultdict[str, float] = defaultdict(float)
    for scenario in scenarios:
        for candidate in scenario["candidate_records"]:
            if candidate["constraints"]["feasible"]:
                identifier = candidate["implementation_id"]
                feasible_counts[identifier] += 1
                energies[identifier] += candidate["analytical_metrics"]["modelled_total_energy"]["value"]
    if not feasible_counts:
        return {"status": "no_feasible_fixed_candidate", "physical_values": None}
    best_fixed = min(feasible_counts, key=lambda item: (-feasible_counts[item], energies[item], item))
    gains: list[float] = []
    for scenario in scenarios:
        if scenario["winner"] is None:
            continue
        records = {item["implementation_id"]: item for item in scenario["candidate_records"]}
        baseline = records.get(best_fixed)
        if baseline is None or not baseline["constraints"]["feasible"]:
            continue
        winner = records[scenario["winner"]]
        gains.append(
            baseline["analytical_metrics"]["modelled_total_energy"]["value"]
            - winner["analytical_metrics"]["modelled_total_energy"]["value"]
        )
    gross = sum(max(0.0, value) for value in gains)
    sweep = [
        {"hypothetical_overhead_fraction_of_gross_gain": fraction, "net_analytical_gain_j": gross * (1.0 - fraction), "beneficial": fraction < 1.0}
        for fraction in (0.0, 0.1, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5)
    ]
    return {
        "status": "parameterized_analytical_threshold",
        "best_single_fixed_candidate": best_fixed,
        "gross_oracle_advantage_j_across_comparable_grid": gross,
        "symbolic_condition": "E_mux + E_controller + N_transition*E_transition + N_reencoded_bits*E_reencode_per_bit < E_best_fixed - E_oracle",
        "maximum_tolerable_total_analytical_overhead_j": gross,
        "hypothetical_sweep": sweep,
        "physical_break_even": None,
        "evidence_level": MODEL_LEVEL,
    }


def run_software_study(
    registry: EccRegistry,
    verification: Mapping[str, Mapping[str, Any]],
    config_path: Path,
    outdir: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    inventory = _scope_inventory(registry, verification)
    capability = _capability_matrix(registry, verification)
    architecture = _architecture_matrix(registry, verification)
    _write(outdir / "ecc_scope_matrix.json", {"schema_version": 1, "rows": inventory})
    _write(outdir / "implementation_capability_matrix.json", {"schema_version": 1, "rows": capability})
    _write(outdir / "architecture_compatibility_matrix.json", {"schema_version": 1, "rows": architecture})

    selectable = sorted(
        identifier for identifier, report in verification.items()
        if report["verification_status"] == "passed"
    )
    profiles: dict[str, dict[str, Any]] = {}
    exact_metrics: dict[str, dict[str, Any]] = {}
    for implementation_id in selectable:
        profile = exact_error_profiles(registry, implementation_id)
        profiles[implementation_id] = profile
        code = registry.code(str(registry.implementation(implementation_id)["code_id"]))
        exact_metrics[implementation_id] = {
            "n": int(code["n"]), "k": int(code["k"]), "parity_bits": int(code["redundancy"]),
            "code_rate": int(code["k"]) / int(code["n"]),
            "distance_evidence": code.get("distance_evidence"),
            "verified_error_profile_id": profile["profile_id"],
            "payload_normalization": payload_normalization(int(code["k"]), int(code["n"])),
            "structural_metrics": structural_metrics(registry, implementation_id),
            "storage_metadata_bits_per_codeword": int(registry.implementation(implementation_id)["metadata_requirements"].get("bits_per_codeword", 0)),
        }
    _write(outdir / "exact_functional_profiles.json", {"schema_version": 1, "profiles": profiles})
    _write(outdir / "normalized_exact_metrics.json", {"schema_version": 1, "implementations": exact_metrics})

    scenario_results: list[dict[str, Any]] = []
    for scenario in _scenario_axes(config):
        candidates = [
            _candidate_metrics(registry, identifier, profiles[identifier], exact_metrics[identifier], scenario, config)
            for identifier in selectable
        ]
        feasible = [item for item in candidates if item["constraints"]["feasible"]]
        pareto = _pareto(feasible)
        winner = _winner(candidates)
        decisions = []
        for identifier in sorted(registry.implementations):
            if identifier not in selectable:
                decisions.append({"implementation_id": identifier, "status": "rejected", "reasons": verification[identifier]["failures"] or ["functional verification failed"]})
                continue
            item = next(candidate for candidate in candidates if candidate["implementation_id"] == identifier)
            reasons = []
            if not item["constraints"]["sdc"]:
                reasons.append("SDC limit exceeded")
            if not item["constraints"]["due"]:
                reasons.append("DUE limit exceeded")
            status = "winner" if identifier == winner else "pareto_feasible" if identifier in pareto else "dominated" if not reasons else "rejected"
            decisions.append({"implementation_id": identifier, "status": status, "reasons": reasons})
        record: dict[str, Any] = {
            "scenario_id": scenario["scenario_id"], "factors": scenario,
            "candidate_records": candidates, "feasible_candidate_count": len(feasible),
            "pareto_implementation_ids": pareto, "winner": winner,
            "selector_id": config["selector"]["selector_id"], "candidate_decisions": decisions,
        }
        record["scenario_sha256"] = canonical_hash(record)
        scenario_results.append(record)
    _write(outdir / "scenario_selection_results.json", {"schema_version": 1, "scenarios": scenario_results})

    winner_frequency = Counter(item["winner"] or "NO_WINNER" for item in scenario_results)
    pareto_frequency = Counter(identifier for item in scenario_results for identifier in item["pareto_implementation_ids"])
    baselines = [
        "secded-rtl-combinational-72-64-v1", "hsiao-generated-combinational-72-64-v1",
        "shortened-bch-85-64-t3-v1-reference-decoder",
    ]
    regret = _baseline_regret(scenario_results, baselines)
    _write(outdir / "pareto_and_regret.json", {
        "schema_version": 1, "winner_frequency": dict(sorted(winner_frequency.items())),
        "pareto_membership_frequency": dict(sorted(pareto_frequency.items())), "fixed_baseline_regret": regret,
    })

    uncertainty_records = []
    uncertainty_winners: dict[str, Counter[str]] = {}
    for model_id, scales in config["uncertainty_models"].items():
        counter: Counter[str] = Counter()
        agreements = 0
        for base in scenario_results:
            scenario = base["factors"]
            candidates = [
                _candidate_metrics(registry, identifier, profiles[identifier], exact_metrics[identifier], scenario, config, uncertainty=scales)
                for identifier in selectable
            ]
            winner = _winner(candidates)
            counter[winner or "NO_WINNER"] += 1
            agreements += int(winner == base["winner"])
            uncertainty_records.append({"scenario_id": scenario["scenario_id"], "uncertainty_model_id": model_id, "winner": winner, "base_winner": base["winner"], "stable": winner == base["winner"]})
        uncertainty_winners[model_id] = counter
        counter["__base_agreements__"] = agreements
    stability = {
        model_id: {
            "winner_frequency": dict(sorted((key, value) for key, value in counts.items() if not key.startswith("__"))),
            "base_winner_agreement_count": counts["__base_agreements__"],
            "base_winner_agreement_fraction": counts["__base_agreements__"] / len(scenario_results),
        }
        for model_id, counts in uncertainty_winners.items()
    }
    sensitivity = {
        "schema_version": 1, "uncertainty_stability": stability,
        "per_scenario": uncertainty_records, "adaptive_threshold": _adaptive_threshold(scenario_results),
    }
    _write(outdir / "uncertainty_and_sensitivity.json", sensitivity)

    regions: dict[str, Any] = {}
    for fault in config["grid"]["fault_profile_ids"]:
        for reliability in config["grid"]["reliability_requirement_ids"]:
            key = f"{fault}--{reliability}"
            group = Counter(
                item["winner"] or "NO_WINNER" for item in scenario_results
                if item["factors"]["fault_profile_ids"] == fault and item["factors"]["reliability_requirement_ids"] == reliability
            )
            regions[key] = dict(sorted(group.items()))
    _write(outdir / "scenario_regions.json", {"schema_version": 1, "regions": regions})

    summary: dict[str, Any] = {
        "schema_version": 1, "study_id": config["study_id"],
        "preregistration_sha256": config["preregistration_sha256"],
        "inventory_row_count": len(inventory), "registered_code_specifications": len(registry.codes),
        "registered_encoder_decoder_implementations": len(registry.implementations),
        "selectable_implementation_count": len(selectable),
        "scenario_count": len(scenario_results),
        "feasible_scenario_count": sum(item["winner"] is not None for item in scenario_results),
        "no_winner_scenario_count": sum(item["winner"] is None for item in scenario_results),
        "winner_frequency": dict(sorted(winner_frequency.items())),
        "pareto_membership_frequency": dict(sorted(pareto_frequency.items())),
        "fixed_baseline_regret": regret,
        "uncertainty_stability": stability,
        "adaptive_threshold": sensitivity["adaptive_threshold"],
        "legacy_selector_comparison": {
            "status": "not_applied", "agreement": None,
            "reason": "legacy selector uses nominal SEC-DAEC/TAEC/BCH family aliases and surrogate constants that do not map one-to-one to functionally verified code_spec_id/decoder_policy_id identities",
        },
        "physical_metrics_all_null": all(
            all(value is None for value in candidate["physical_metrics"].values())
            for scenario in scenario_results for candidate in scenario["candidate_records"]
        ),
        "evidence_scope": "exact software functional execution plus preregistered analytical sensitivity model; no physical PPA",
    }
    distinct_winners = {key for key in winner_frequency if key != "NO_WINNER"}
    nonzero_regret = any(
        item["total_analytical_energy_regret_j"] > 0
        for item in regret.values() if item["total_analytical_energy_regret_j"] is not None
    )
    summary["decision_rule_result"] = (
        "scenario_aware_selection_supported_within_analytical_model"
        if len(distinct_winners) > 1 and nonzero_regret
        else "fixed_strategy_supported" if len(distinct_winners) == 1
        else "comparative_selection_indeterminate"
    )
    summary["summary_sha256"] = canonical_hash(summary)
    _write(outdir / "software_study_summary.json", summary)
    _write_scope_markdown(outdir / "ECC_SCOPE_MATRIX.md", inventory)
    _make_plots(outdir, scenario_results, summary, regions)
    return summary


def _write_scope_markdown(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    lines = [
        "# ECC Scope Matrix", "",
        "Grouped artifacts are listed once when they share one generator lineage or decoder policy. Registered mathematical identities remain one row each.", "",
        "| Candidate/artifact group | Status | Code specification | Reason/scope |",
        "|---|---|---|---|",
    ]
    for row in rows:
        reason = str(row.get("reason", row.get("selection_scope", ""))).replace("|", "\\|")
        lines.append(f"| `{row['candidate_id']}` | `{row['status']}` | `{row.get('code_spec_id') or '—'}` | {reason} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _make_plots(outdir: Path, scenarios: Sequence[Mapping[str, Any]], summary: Mapping[str, Any], regions: Mapping[str, Any]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plotdir = outdir / "plots"
    plotdir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []

    representative = next((item for item in scenarios if item["winner"] is not None), scenarios[0])
    fig, ax = plt.subplots(figsize=(9, 5))
    for item in representative["candidate_records"]:
        x = item["analytical_metrics"]["modelled_total_energy"]["value"]
        y = max(item["analytical_metrics"]["expected_sdc_probability_per_64b_access"]["value"], 1e-18)
        ax.scatter(x, y, marker="o" if item["implementation_id"] in representative["pareto_implementation_ids"] else "x")
        ax.annotate(item["implementation_id"][:18], (x, y), fontsize=6)
    ax.set_yscale("log"); ax.set_xlabel("Modelled total energy (J/scenario)"); ax.set_ylabel("Analytical SDC probability / 64b access")
    ax.set_title("Reliability–cost candidates (one traceable scenario)"); fig.tight_layout()
    name = "reliability_cost_pareto.png"; fig.savefig(plotdir / name, dpi=180); plt.close(fig)
    manifest.append({"plot": name, "record_ids": [item["candidate_record_id"] for item in representative["candidate_records"]], "scenario_id": representative["scenario_id"]})

    winners = {key: value for key, value in summary["winner_frequency"].items() if key != "NO_WINNER"}
    fig, ax = plt.subplots(figsize=(10, 5)); ax.bar(range(len(winners)), winners.values())
    ax.set_xticks(range(len(winners)), [key[:18] for key in winners], rotation=35, ha="right", fontsize=7)
    ax.set_ylabel("Scenario wins"); ax.set_title("Winner frequency"); fig.tight_layout()
    name = "winner_frequency.png"; fig.savefig(plotdir / name, dpi=180); plt.close(fig)
    manifest.append({"plot": name, "source": "software_study_summary.json#winner_frequency"})

    labels = sorted(regions)
    dominant = [max(regions[key], key=regions[key].get) for key in labels]
    ids = {value: index for index, value in enumerate(sorted(set(dominant)))}
    fig, ax = plt.subplots(figsize=(10, 3)); image = ax.imshow([[ids[value] for value in dominant]], aspect="auto", cmap="tab20")
    ax.set_xticks(range(len(labels)), labels, rotation=30, ha="right", fontsize=7); ax.set_yticks([0], ["dominant winner"])
    for col, value in enumerate(dominant): ax.text(col, 0, value[:10], ha="center", va="center", fontsize=6)
    ax.set_title("Scenario-region winner map"); fig.tight_layout()
    name = "scenario_region_heatmap.png"; fig.savefig(plotdir / name, dpi=180); plt.close(fig)
    manifest.append({"plot": name, "source": "scenario_regions.json"})

    regrets = summary["fixed_baseline_regret"]
    names = list(regrets); values = [(regrets[key]["mean_fractional_regret"] or 0.0) * 100 for key in names]
    fig, ax = plt.subplots(figsize=(8, 4)); ax.bar(range(len(names)), values)
    ax.set_xticks(range(len(names)), [name[:20] for name in names], rotation=25, ha="right", fontsize=8)
    ax.set_ylabel("Mean analytical energy regret (%)"); ax.set_title("Fixed-baseline regret"); fig.tight_layout()
    name = "fixed_baseline_regret.png"; fig.savefig(plotdir / name, dpi=180); plt.close(fig)
    manifest.append({"plot": name, "source": "pareto_and_regret.json#fixed_baseline_regret"})

    stability = summary["uncertainty_stability"]
    models = list(stability); values = [stability[key]["base_winner_agreement_fraction"] for key in models]
    fig, ax = plt.subplots(figsize=(7, 4)); ax.bar(models, values); ax.set_ylim(0, 1.05)
    ax.set_ylabel("Base-winner agreement fraction"); ax.set_title("Winner stability under sensitivity models"); fig.tight_layout()
    name = "uncertainty_stability.png"; fig.savefig(plotdir / name, dpi=180); plt.close(fig)
    manifest.append({"plot": name, "source": "uncertainty_and_sensitivity.json#uncertainty_stability"})

    payload = {"schema_version": 1, "plots": manifest}
    payload["plot_manifest_sha256"] = canonical_hash(payload)
    _write(outdir / "plot_manifest.json", payload)
