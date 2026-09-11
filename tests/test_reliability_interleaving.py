from __future__ import annotations

import csv
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = (
    ROOT
    / "campaigns"
    / "iscas_sustainability_extension"
    / "green_refoundation_node_aware_carbon"
)
sys.path.insert(0, str(CAMPAIGN / "interleaving"))
sys.path.insert(0, str(CAMPAIGN / "reliability"))

from physical_mapping import (  # noqa: E402
    InterleavingId,
    PhysicalSlot,
    TopologyScenario,
    bounded_codeword_multiplicities,
    logical_to_slot,
    map_physical_slots_to_codewords,
    slot_to_logical,
)
from service_outcomes import (  # noqa: E402
    ServiceOutcome,
    TransactionObservation,
    classify_transaction,
    summarize_observations,
    useful_service_bits,
)


@pytest.mark.parametrize("protected,bits", [(False, 64), (True, 72)])
@pytest.mark.parametrize("interleaving", list(InterleavingId))
def test_i0_i1_i2_mapping_is_exhaustively_bijective(
    protected: bool, bits: int, interleaving: InterleavingId
) -> None:
    slots = set()
    for word in range(256):
        for bit in range(bits):
            slot = logical_to_slot(word, bit, interleaving, protected=protected)
            assert slot not in slots
            slots.add(slot)
            assert slot_to_logical(
                slot, interleaving, protected=protected
            ) == (word, bit)
    assert len(slots) == 256 * bits


def test_unused_banked_capacity_fails_closed() -> None:
    with pytest.raises(ValueError, match="unused capacity"):
        slot_to_logical(
            PhysicalSlot("data", 0, 255, 0), InterleavingId.I2, protected=False
        )


def test_external_physical_slots_map_to_codeword_masks() -> None:
    slots = [
        logical_to_slot(7, 1, "I2", protected=True),
        logical_to_slot(7, 4, "I2", protected=True),
        logical_to_slot(8, 70, "I2", protected=True),
    ]
    faults = map_physical_slots_to_codewords(slots, "I2", protected=True)
    assert [(fault.word_address, fault.codeword_bits) for fault in faults] == [
        (7, (1, 4)),
        (8, (70,)),
    ]
    assert faults[0].error_mask == (1 << 1) | (1 << 4)


def test_duplicate_physical_sites_are_rejected() -> None:
    slot = logical_to_slot(0, 0, "I1", protected=True)
    with pytest.raises(ValueError, match="duplicate"):
        map_physical_slots_to_codewords([slot, slot], "I1", protected=True)


@pytest.mark.parametrize("weight", range(1, 17))
def test_bounded_topologies_conserve_fault_weight(weight: int) -> None:
    best = bounded_codeword_multiplicities(
        weight, TopologyScenario.BEST_CASE_INTERLEAVING
    )
    worst = bounded_codeword_multiplicities(
        weight, TopologyScenario.WORST_CASE_CLUSTERING
    )
    nominal = bounded_codeword_multiplicities(
        weight,
        TopologyScenario.NOMINAL_PARAMETRIC,
        nominal_codeword_spread=min(weight, 4),
    )
    assert sum(best) == sum(worst) == sum(nominal) == weight
    assert max(best) <= max(nominal) <= max(worst)


def test_deterministic_service_categories_cover_retry_due_sdc_and_timeout() -> None:
    observations = [
        TransactionObservation(True, True, latency_ns=1.0),
        TransactionObservation(True, True, correction_applied=True, latency_ns=1.0),
        TransactionObservation(
            True,
            True,
            due_detected=True,
            failure_detected=True,
            retry_count=1,
            latency_ns=2.0,
        ),
        TransactionObservation(False, False, due_detected=True, latency_ns=1.0),
        TransactionObservation(
            True, False, correction_applied=True, latency_ns=1.0
        ),
        TransactionObservation(True, True, latency_ns=11.0),
    ]
    expected = [
        ServiceOutcome.SUCCESS_NORMAL,
        ServiceOutcome.SUCCESS_CORRECTED,
        ServiceOutcome.SUCCESS_AFTER_RETRY,
        ServiceOutcome.DETECTED_FAILURE,
        ServiceOutcome.SILENT_DATA_CORRUPTION,
        ServiceOutcome.TIMEOUT_OR_SLA_FAILURE,
    ]
    assert [
        classify_transaction(item, sla_limit_ns=10.0) for item in observations
    ] == expected
    summary = summarize_observations(observations, sla_limit_ns=10.0)
    assert summary.service_success_probability == pytest.approx(0.5)
    assert useful_service_bits(64, summary) == 3 * 64
    assert summary.corrected_event_count == 2
    assert summary.retry_event_count == 1


def test_no_sla_is_invented_and_declared_sla_requires_latency() -> None:
    slow_but_correct = TransactionObservation(True, True, latency_ns=1e9)
    assert classify_transaction(slow_but_correct) == ServiceOutcome.SUCCESS_NORMAL
    with pytest.raises(ValueError, match="latency"):
        classify_transaction(TransactionObservation(True, True), sla_limit_ns=10.0)


def test_reliability_rows_are_exhaustive_and_not_physical_rates() -> None:
    path = CAMPAIGN / "reliability" / "RELIABILITY_RESULTS.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 14
    outcome_fields = [
        "success_normal_count",
        "success_corrected_count",
        "success_after_retry_count",
        "detected_failure_count",
        "sdc_count",
        "timeout_count",
    ]
    for row in rows:
        assert sum(int(row[field]) for field in outcome_fields) == int(
            row["pattern_count"]
        )
        assert row["physical_rate"] == "NOT_QUALIFIED"
        expected = sum(int(row[field]) for field in outcome_fields[:3]) / int(
            row["pattern_count"]
        )
        assert float(row["service_success_probability"]) == pytest.approx(expected)


def test_interleaving_costs_never_claim_unmeasured_benefit() -> None:
    path = CAMPAIGN / "interleaving" / "INTERLEAVING_COST.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert {(row["architecture_id"], row["interleaving_id"]) for row in rows} == {
        (architecture, mapping)
        for architecture in ("U0", "E0")
        for mapping in ("I0", "I1", "I2")
    }
    for row in rows:
        assert row["energy_overhead_j"] == "NOT_MEASURED"
        assert row["latency_impact_ns"] == "NOT_MEASURED"
