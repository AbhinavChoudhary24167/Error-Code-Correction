from __future__ import annotations

import csv
import hashlib
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
ENERGY = (
    ROOT
    / "campaigns"
    / "iscas_sustainability_extension"
    / "green_refoundation_node_aware_carbon"
    / "energy"
)
sys.path.insert(0, str(ENERGY))

from energy_accounting import (  # noqa: E402
    ActivityCoverage,
    EnergyQuantity,
    EvidenceTier,
    Interval,
    OperationalWorkload,
    account_operational_energy,
    classify_activity_coverage,
    operational_carbon_interval,
)
import audit_attempt10_activity as activity_audit  # noqa: E402


def _q(value: float, *, tier: EvidenceTier = EvidenceTier.TIER_1_INDEPENDENT_CHARACTERIZATION, unit: str = "J/event") -> EnergyQuantity:
    return EnergyQuantity(Interval(value, value), unit, tier, "MEASURED", ("TEST",))


def _complete_quantities() -> dict[str, EnergyQuantity]:
    return {
        "normal_read": _q(2.0),
        "normal_write": _q(3.0),
        "ecc_encode": _q(0.5),
        "ecc_decode": _q(0.25),
        "correction": _q(0.75),
        "scrub": _q(4.0),
        "retry": _q(5.0),
        "recovery": _q(6.0),
        "idle_leakage": _q(0.1, unit="W"),
    }


def test_operational_boundary_keeps_terms_disjoint() -> None:
    workload = OperationalWorkload(10, 4, 2, 3, 2, 1, 20.0)
    result = account_operational_energy(
        workload, _complete_quantities(), activity_qualified=True
    )
    expected = 20 + 12 + 2 + 2.5 + 1.5 + 12 + 10 + 6 + 2
    assert result.total_interval_j == Interval(expected, expected)
    assert sum(value.lower for value in result.breakdown_j.values() if value) == expected
    assert result.classification == "QUALIFIED_ABSOLUTE"


def test_zero_count_missing_term_does_not_block() -> None:
    quantities = _complete_quantities()
    quantities["correction"] = EnergyQuantity(
        None,
        "J/event",
        EvidenceTier.TIER_5_NOT_QUALIFIED,
        "NOT_QUALIFIED",
        ("MISSING",),
    )
    result = account_operational_energy(
        OperationalWorkload(1, 0, corrected_read_count=0),
        quantities,
        activity_qualified=True,
    )
    assert result.total_interval_j == Interval(2.25, 2.25)


def test_active_tier5_blocks_total_but_preserves_subtotal() -> None:
    quantities = _complete_quantities()
    quantities["normal_read"] = EnergyQuantity(
        None,
        "J/event",
        EvidenceTier.TIER_5_NOT_QUALIFIED,
        "NOT_QUALIFIED",
        ("MISSING_MACRO",),
    )
    result = account_operational_energy(
        OperationalWorkload(2, 1), quantities, activity_qualified=True
    )
    assert result.total_interval_j is None
    assert result.accounted_subtotal_j == Interval(4.0, 4.0)
    assert "normal_read:TIER_5_NOT_QUALIFIED" in result.blockers


def test_activity_failure_blocks_otherwise_complete_energy() -> None:
    result = account_operational_energy(
        OperationalWorkload(1, 1), _complete_quantities(), activity_qualified=False
    )
    assert result.classification == "UNQUALIFIED"
    assert result.total_interval_j is None
    assert result.blockers == ("ACTIVITY_NOT_QUALIFIED",)


def test_parametric_bounds_propagate_without_becoming_measured() -> None:
    quantities = _complete_quantities()
    quantities["normal_read"] = EnergyQuantity(
        Interval(1.0, 4.0),
        "J/event",
        EvidenceTier.TIER_4_BOUNDED_PARAMETRIC,
        "PARAMETRIC",
        ("BOUND",),
    )
    result = account_operational_energy(
        OperationalWorkload(2, 0), quantities, activity_qualified=True
    )
    assert result.total_interval_j == Interval(2.5, 8.5)
    assert result.classification == "PARAMETRIC_SENSITIVITY"


def test_operational_carbon_is_linear_in_fixed_grid_ci() -> None:
    result = account_operational_energy(
        OperationalWorkload(3_600_000, 0),
        {**_complete_quantities(), "normal_read": _q(1.0)},
        activity_qualified=True,
    )
    low = operational_carbon_interval(result, Interval(0.1, 0.1))
    high = operational_carbon_interval(result, Interval(0.4, 0.4))
    assert low is not None and high is not None
    assert high.lower == pytest.approx(4.0 * low.lower)


def test_non_applicable_term_is_explicit_zero() -> None:
    quantities = _complete_quantities()
    quantities["ecc_encode"] = EnergyQuantity.not_applicable(
        "J/event", "UNPROTECTED_ARCHITECTURE"
    )
    result = account_operational_energy(
        OperationalWorkload(0, 10), quantities, activity_qualified=True
    )
    assert result.breakdown_j["ecc_encode"] == Interval(0.0, 0.0)


def test_activity_is_qualified_per_required_component() -> None:
    rows = [
        ActivityCoverage("clock", 99, 100, True, "MAPPED"),
        ActivityCoverage("macro", 148, 148, True, "MAPPED"),
        ActivityCoverage("antenna", 0, 20, False, "UNANNOTATED"),
    ]
    status = classify_activity_coverage(rows, minimum_fraction=0.95)
    assert status["qualified"] is True
    rows.append(ActivityCoverage("decoder", None, None, True, "NOT_SEPARABLE"))
    status = classify_activity_coverage(rows, minimum_fraction=0.95)
    assert status["qualified"] is False
    assert "decoder:COVERAGE_NOT_MEASURED" in status["blockers"]


def test_attempt10_component_partition_reproduces_aggregate_counts() -> None:
    with (ENERGY / "ACTIVITY_COVERAGE_BY_COMPONENT.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    expected = {"U0": (296, 608), "E0": (142, 3268)}
    for architecture, pair in expected.items():
        partition = [
            row
            for row in rows
            if row["architecture_id"] == architecture
            and row["count_partition"] == "true"
        ]
        annotated = sum(int(row["annotated_pin_count"]) for row in partition)
        total = sum(int(row["total_pin_count"]) for row in partition)
        assert (annotated, total) == pair


def test_attempt10_component_csv_is_byte_reproducible(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, expected in activity_audit.EXPECTED_SHA256.items():
        architecture, report = key.split("/", 1)
        path = activity_audit.POSTROUTE / architecture / "slash_scope" / report
        raw = path.read_bytes()
        canonical = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        assert hashlib.sha256(canonical).hexdigest() == expected
        monkeypatch.setitem(
            activity_audit.EXPECTED_SHA256,
            key,
            hashlib.sha256(raw).hexdigest(),
        )
    assert (ENERGY / "ACTIVITY_COVERAGE_BY_COMPONENT.csv").read_text(
        "utf-8"
    ) == activity_audit.render_csv()


def test_interval_rejects_negative_reversed_and_nonfinite() -> None:
    with pytest.raises(ValueError):
        Interval(-1.0, 1.0)
    with pytest.raises(ValueError):
        Interval(2.0, 1.0)
    with pytest.raises(ValueError):
        Interval(0.0, float("inf"))


def test_tier5_cannot_carry_a_decision_value() -> None:
    with pytest.raises(ValueError):
        EnergyQuantity(
            Interval(1.0, 2.0),
            "J/event",
            EvidenceTier.TIER_5_NOT_QUALIFIED,
            "NOT_QUALIFIED",
            ("BAD",),
        )
