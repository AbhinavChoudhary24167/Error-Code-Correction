"""Scientific guards for the GREEN Matrix 3.1 physical-population campaign.

The functions in this module deliberately keep physical event generation,
charge/circuit susceptibility, logical corruption, ECC outcome, service, and
resource accounting as separate layers.  Missing inputs are rejected or left
blocked; none of the helpers supplies a default physical probability.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Iterable, Mapping, Sequence


EVIDENCE_KINDS = frozenset(
    {
        "MEASURED",
        "DERIVED_FROM_MATCHED_MEASUREMENT",
        "ANALYTICAL",
        "POST_ROUTE_ESTIMATE",
        "LITERATURE_REFERENCE",
        "PARAMETRIC",
        "BOUND",
        "EXPLICIT_ZERO",
        "EXCLUDED",
        "UNAVAILABLE",
        "TECHNOLOGY_MISMATCH",
        "BLOCKED",
    }
)

OUTCOMES = ("CORRECT", "CORRECTED", "DUE", "SDC")


def _finite(name: str, value: float) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _nonnegative(name: str, value: float) -> float:
    number = _finite(name, value)
    if number < 0.0:
        raise ValueError(f"{name} must be non-negative")
    return number


def validate_evidence_kind(kind: str) -> str:
    if kind not in EVIDENCE_KINDS:
        raise ValueError(f"unsupported evidence kind: {kind}")
    return kind


def validate_probability_distribution(
    probabilities: Mapping[str, float], *, tolerance: float = 1e-12
) -> dict[str, float]:
    """Return a normalized copy only when the supplied PMF already sums to one.

    The function validates; it never silently normalizes evidence.
    """

    if not probabilities:
        raise ValueError("probability distribution must not be empty")
    checked = {name: _nonnegative(f"P({name})", value) for name, value in probabilities.items()}
    if any(value > 1.0 for value in checked.values()):
        raise ValueError("individual probabilities must not exceed one")
    total = math.fsum(checked.values())
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=tolerance):
        raise ValueError(f"probabilities must sum to one, got {total!r}")
    return checked


def aggregate_physical_outcomes(
    topology_probabilities: Mapping[str, float],
    conditional_outcomes: Mapping[str, Mapping[str, float]],
) -> dict[str, float]:
    """Apply total probability without conflating DUE and SDC.

    This implements ``P(outcome)=sum_f P(outcome|f)P(f)``.  Both the physical
    topology PMF and every conditional outcome PMF must be explicit and
    complete.  Logical enumeration frequencies are therefore not acceptable
    substitutes unless a caller has independently established that they are a
    physical PMF.
    """

    topology = validate_probability_distribution(topology_probabilities)
    if set(conditional_outcomes) != set(topology):
        raise ValueError("conditional outcomes must cover exactly the physical topology support")
    result = {outcome: 0.0 for outcome in OUTCOMES}
    for fault, p_fault in topology.items():
        conditional = conditional_outcomes[fault]
        if set(conditional) != set(OUTCOMES):
            raise ValueError(f"conditional outcome PMF for {fault} must contain {OUTCOMES}")
        checked = validate_probability_distribution(conditional)
        for outcome in OUTCOMES:
            result[outcome] += p_fault * checked[outcome]
    validate_probability_distribution(result, tolerance=2e-12)
    return result


@dataclass(frozen=True)
class PhysicalCell:
    cell_id: str
    row: int
    column: int
    bit_index: int
    codeword: int
    word: int
    bank: int
    x_um: float | None = None
    y_um: float | None = None

    def __post_init__(self) -> None:
        if not self.cell_id:
            raise ValueError("cell_id is required")
        for name in ("row", "column", "bit_index", "codeword", "word", "bank"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if (self.x_um is None) != (self.y_um is None):
            raise ValueError("physical coordinates must supply both x_um and y_um")
        if self.x_um is not None:
            _finite("x_um", self.x_um)
            _finite("y_um", self.y_um)  # type: ignore[arg-type]


def validate_geometry(cells: Sequence[PhysicalCell]) -> dict[str, PhysicalCell]:
    if not cells:
        raise ValueError("geometry must contain at least one physical cell")
    by_id: dict[str, PhysicalCell] = {}
    logical: set[tuple[int, int, int]] = set()
    for cell in cells:
        if cell.cell_id in by_id:
            raise ValueError(f"duplicate physical cell ID: {cell.cell_id}")
        key = (cell.bank, cell.codeword, cell.bit_index)
        if key in logical:
            raise ValueError(f"duplicate logical bit mapping: {key}")
        by_id[cell.cell_id] = cell
        logical.add(key)
    return by_id


def propagate_topology(
    event_cell_ids: Iterable[str],
    cells: Sequence[PhysicalCell],
    decoder: Callable[[int, int], str],
) -> dict[str, object]:
    """Map a physical cluster to codeword masks and distinct ECC outcomes.

    ``decoder(codeword, mask)`` must return CORRECT, CORRECTED, DUE, or SDC.
    Requiring a decoder callback prevents a weight-only MBU approximation from
    being silently presented as an ECC result.
    """

    geometry = validate_geometry(cells)
    selected = list(event_cell_ids)
    if not selected:
        raise ValueError("an event must upset at least one physical cell")
    if len(set(selected)) != len(selected):
        raise ValueError("an event cannot list the same physical cell twice")
    unknown = sorted(set(selected) - set(geometry))
    if unknown:
        raise ValueError(f"unknown physical cells: {unknown}")
    masks: dict[int, int] = {}
    for cell_id in selected:
        cell = geometry[cell_id]
        masks[cell.codeword] = masks.get(cell.codeword, 0) | (1 << cell.bit_index)
    outcomes: dict[int, str] = {}
    for codeword, mask in sorted(masks.items()):
        outcome = decoder(codeword, mask)
        if outcome not in OUTCOMES:
            raise ValueError(f"decoder returned unsupported outcome: {outcome}")
        outcomes[codeword] = outcome
    return {
        "physical_cells": selected,
        "codeword_masks": {str(key): value for key, value in sorted(masks.items())},
        "outcomes": {str(key): value for key, value in sorted(outcomes.items())},
    }


def classify_secded_control(mask: int) -> str:
    """Exact only for the SECDED guarantees at weights one and two.

    Higher weights depend on the actual parity-check matrix and decoder, so the
    helper refuses to invent an outcome for them.
    """

    if isinstance(mask, bool) or not isinstance(mask, int) or mask < 0:
        raise ValueError("mask must be a non-negative integer")
    weight = mask.bit_count()
    if weight == 0:
        return "CORRECT"
    if weight == 1:
        return "CORRECTED"
    if weight == 2:
        return "DUE"
    raise ValueError("weight-three-or-greater SECDED outcome requires the actual decoder")


@dataclass(frozen=True)
class EnergyDerivation:
    window_energy_j: float
    energy_per_service_j: float
    source_kind: str
    derived_kind: str
    functional_unit: str


def derive_energy_from_power(
    power_w: float,
    duration_s: float,
    service_count: int,
    *,
    source_kind: str,
    functional_unit: str,
) -> EnergyDerivation:
    """Integrate power over a declared window and service denominator.

    POST_ROUTE_ESTIMATE remains POST_ROUTE_ESTIMATE.  Only a matched measured
    power source can yield DERIVED_FROM_MATCHED_MEASUREMENT.
    """

    validate_evidence_kind(source_kind)
    if source_kind in {"UNAVAILABLE", "BLOCKED", "EXCLUDED", "TECHNOLOGY_MISMATCH"}:
        raise ValueError(f"cannot derive energy from {source_kind} power")
    power = _nonnegative("power_w", power_w)
    duration = _nonnegative("duration_s", duration_s)
    if isinstance(service_count, bool) or not isinstance(service_count, int) or service_count <= 0:
        raise ValueError("service_count must be a strictly positive integer")
    if not functional_unit.strip():
        raise ValueError("functional_unit is required")
    energy = power * duration
    derived_kind = (
        "DERIVED_FROM_MATCHED_MEASUREMENT" if source_kind == "MEASURED" else source_kind
    )
    return EnergyDerivation(energy, energy / service_count, source_kind, derived_kind, functional_unit)


def validate_disjoint_power_partition(
    total_power_w: float,
    components_w: Mapping[str, float],
    *,
    tolerance_w: float = 1e-12,
) -> None:
    if not components_w:
        raise ValueError("at least one power component is required")
    if any("total" in name.lower() for name in components_w):
        raise ValueError("the total must not also appear as an additive component")
    total = _nonnegative("total_power_w", total_power_w)
    component_total = math.fsum(
        _nonnegative(f"components_w[{name}]", value) for name, value in components_w.items()
    )
    if not math.isclose(component_total, total, rel_tol=1e-6, abs_tol=tolerance_w):
        raise ValueError("power components do not form the declared disjoint total")


@dataclass(frozen=True)
class ServiceMetrics:
    latency_cycles: int
    initiation_interval_cycles: int
    clock_period_s: float

    def __post_init__(self) -> None:
        for name in ("latency_cycles", "initiation_interval_cycles"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a strictly positive integer")
        if _finite("clock_period_s", self.clock_period_s) <= 0.0:
            raise ValueError("clock_period_s must be strictly positive")

    @property
    def latency_s(self) -> float:
        return self.latency_cycles * self.clock_period_s

    @property
    def nominal_initiation_capacity_services_per_s(self) -> float:
        return 1.0 / (self.initiation_interval_cycles * self.clock_period_s)


def classify_literature_transfer(
    source_technology: str,
    target_technology: str,
    *,
    independent_equivalence_established: bool = False,
) -> str:
    """Guard numeric transfer across technologies, including generic 130 nm.

    A matching marketing node is insufficient.  Exact technology identity or
    explicit independent equivalence evidence is required.
    """

    source = source_technology.strip().casefold()
    target = target_technology.strip().casefold()
    if not source or not target:
        raise ValueError("source and target technologies are required")
    if source == target or independent_equivalence_established:
        return "LITERATURE_REFERENCE"
    return "LITERATURE_REFERENCE_TECHNOLOGY_MISMATCH"


@dataclass(frozen=True)
class QCritRecord:
    value_c: float
    waveform_provenance: str
    evidence_kind: str
    technology: str
    pvt: str

    def __post_init__(self) -> None:
        if _finite("value_c", self.value_c) <= 0.0:
            raise ValueError("value_c must be strictly positive")
        validate_evidence_kind(self.evidence_kind)
        if not self.waveform_provenance.strip() or not self.technology.strip() or not self.pvt.strip():
            raise ValueError("Qcrit requires waveform provenance, technology, and PVT")


def event_rate_from_qcrit(_qcrit: QCritRecord) -> float:
    raise ValueError("Qcrit is conditional circuit susceptibility and cannot establish a particle event rate")


def validate_interleaver_mapping(
    physical_to_logical: Mapping[str, tuple[int, int]],
    *,
    expected_cell_count: int,
) -> None:
    if expected_cell_count <= 0:
        raise ValueError("expected_cell_count must be positive")
    if len(physical_to_logical) != expected_cell_count:
        raise ValueError("interleaver mapping is incomplete")
    logical = list(physical_to_logical.values())
    if len(set(logical)) != len(logical):
        raise ValueError("interleaver mapping is not bijective")
    for codeword, bit in logical:
        if codeword < 0 or bit < 0:
            raise ValueError("logical coordinates must be non-negative")


def exact_pareto_indices(points: Sequence[Sequence[float]]) -> list[int]:
    """Return deterministic nondominated indices for all-minimize objectives."""

    checked: list[tuple[float, ...]] = []
    width: int | None = None
    for point in points:
        row = tuple(_finite("objective", value) for value in point)
        if not row:
            raise ValueError("each Pareto point needs at least one objective")
        width = len(row) if width is None else width
        if len(row) != width:
            raise ValueError("Pareto points must have equal dimensionality")
        checked.append(row)
    front: list[int] = []
    for index, candidate in enumerate(checked):
        dominated = False
        for other_index, other in enumerate(checked):
            if other_index == index:
                continue
            if all(left <= right for left, right in zip(other, candidate)) and any(
                left < right for left, right in zip(other, candidate)
            ):
                dominated = True
                break
        if not dominated:
            front.append(index)
    return front


def classify_pareto_front(
    evidence_tiers: Iterable[str],
    *,
    physical_probabilities_qualified: bool,
    sustainability_qualified: bool,
) -> str:
    tiers = set(evidence_tiers)
    if sustainability_qualified and physical_probabilities_qualified:
        return "SUSTAINABILITY_QUALIFIED_FRONT"
    if physical_probabilities_qualified:
        return "PHYSICALLY_QUALIFIED_FRONT"
    if "E1" in tiers:
        return "PARAMETRIC_FRONT"
    return "DIAGNOSTIC_FRONT"
