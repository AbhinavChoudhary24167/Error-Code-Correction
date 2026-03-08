from schema import (
    SELECT_CANDIDATE_CSV_FIELDS,
    TARGET_FEASIBLE_CSV_FIELDS,
    TELEMETRY_FIELDS,
    canonical_projection,
    get_semantic_value,
    infer_schema_aliases,
)


def test_alias_resolution_for_scores_and_carbon_fields() -> None:
    row = {
        "FIT": 1.0,
        "ESII": 0.4,
        "NESII": 60.0,
        "GS": 0.7,
        "total_kgCO2e": 0.12,
        "confidence_score": 0.88,
        "ood_max_abs_z": 1.2,
    }

    assert get_semantic_value(row, "fit") == 1.0
    assert get_semantic_value(row, "esii") == 0.4
    assert get_semantic_value(row, "nesii") == 60.0
    assert get_semantic_value(row, "green_score") == 0.7
    assert get_semantic_value(row, "carbon_total_kgco2e") == 0.12
    assert get_semantic_value(row, "confidence") == 0.88
    assert get_semantic_value(row, "ood_score") == 1.2


def test_projection_and_inference_keep_known_semantics() -> None:
    row = {
        "FIT": 2.0,
        "E_scrub_kWh": 0.01,
        "total_kgco2e": 0.11,
        "advisory_confidence": 0.5,
        "advisory_ood_score": 0.2,
    }
    projection = canonical_projection(row)
    assert projection["fit"] == 2.0
    assert projection["energy_scrub_kwh"] == 0.01
    assert projection["carbon_total_kgco2e"] == 0.11
    assert projection["confidence"] == 0.5
    assert projection["ood_score"] == 0.2

    inferred = infer_schema_aliases(row.keys())
    assert inferred["fit"] == {"FIT"}
    assert inferred["energy_scrub_kwh"] == {"E_scrub_kWh"}


def test_shared_csv_and_telemetry_field_orders_remain_stable() -> None:
    assert list(TELEMETRY_FIELDS) == [
        "workload_id",
        "node_nm",
        "vdd",
        "tempC",
        "clk_MHz",
        "xor_toggles",
        "and_toggles",
        "add_toggles",
        "corr_events",
        "words",
        "accesses",
        "scrub_s",
        "capacity_gib",
        "runtime_s",
    ]

    assert list(SELECT_CANDIDATE_CSV_FIELDS) == [
        "code",
        "scrub_s",
        "FIT",
        "carbon_kg",
        "latency_ns",
        "ESII",
        "NESII",
        "GS",
        "areas",
        "energies",
        "violations",
        "scenario_hash",
    ]

    assert list(TARGET_FEASIBLE_CSV_FIELDS) == [
        "code",
        "fit_bit",
        "fit_word_post",
        "FIT",
        "carbon_kg",
        "ESII",
        "NESII",
        "GS",
        "scrub_s",
        "area_logic_mm2",
        "area_macro_mm2",
        "E_dyn_kWh",
        "E_leak_kWh",
        "E_scrub_kWh",
    ]
