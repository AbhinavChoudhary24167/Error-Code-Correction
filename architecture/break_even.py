"""Break-even conditions for ECC transitions and adaptable architectures."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math


BREAK_EVEN_STATUSES = {
    "finite",
    "immediate_benefit",
    "never_beneficial",
    "insufficient_characterization",
    "infeasible_transition",
}


@dataclass(frozen=True)
class BreakEvenResult:
    status: str
    horizon_accesses: int | None
    one_time_cost: float | None
    net_improvement_per_access: float | None
    units: str
    explanation: str

    def __post_init__(self) -> None:
        if self.status not in BREAK_EVEN_STATUSES:
            raise ValueError(f"invalid break-even status: {self.status}")

    def to_dict(self) -> dict:
        return asdict(self)


def break_even_horizon(
    *,
    current_cost_per_access: float | None,
    new_cost_per_access: float | None,
    continuing_adaptive_overhead_per_access: float | None,
    one_time_transition_cost: float | None,
    one_time_allocated_cost: float = 0.0,
    feasible: bool = True,
    units: str,
) -> BreakEvenResult:
    if not feasible:
        return BreakEvenResult(
            "infeasible_transition", None, None, None, units, "transition is disallowed or unsafe"
        )
    values = (
        current_cost_per_access,
        new_cost_per_access,
        continuing_adaptive_overhead_per_access,
        one_time_transition_cost,
    )
    if any(value is None for value in values):
        return BreakEvenResult(
            "insufficient_characterization",
            None,
            None,
            None,
            units,
            "one or more physical cost terms are unavailable",
        )
    assert current_cost_per_access is not None
    assert new_cost_per_access is not None
    assert continuing_adaptive_overhead_per_access is not None
    assert one_time_transition_cost is not None
    if min(
        current_cost_per_access,
        new_cost_per_access,
        continuing_adaptive_overhead_per_access,
        one_time_transition_cost,
        one_time_allocated_cost,
    ) < 0:
        raise ValueError("break-even cost terms must be non-negative")
    delta = current_cost_per_access - new_cost_per_access - continuing_adaptive_overhead_per_access
    one_time = one_time_transition_cost + one_time_allocated_cost
    if delta <= 0:
        return BreakEvenResult(
            "never_beneficial",
            None,
            one_time,
            delta,
            units,
            "continuing cost is not lower after adaptability overhead",
        )
    if one_time == 0:
        return BreakEvenResult(
            "immediate_benefit", 0, 0.0, delta, units, "positive saving with no one-time cost"
        )
    horizon = math.ceil(one_time / delta)
    return BreakEvenResult(
        "finite",
        horizon,
        one_time,
        delta,
        units,
        "one-time transition and allocated implementation cost divided by net per-access saving",
    )


def energy_break_even(
    *,
    current_energy_j_per_access: float | None,
    new_energy_j_per_access: float | None,
    adaptive_energy_j_per_access: float | None,
    migration_energy_j: float | None,
    control_energy_j: float | None,
    feasible: bool = True,
) -> BreakEvenResult:
    transition = (
        migration_energy_j + control_energy_j
        if migration_energy_j is not None and control_energy_j is not None
        else None
    )
    return break_even_horizon(
        current_cost_per_access=current_energy_j_per_access,
        new_cost_per_access=new_energy_j_per_access,
        continuing_adaptive_overhead_per_access=adaptive_energy_j_per_access,
        one_time_transition_cost=transition,
        feasible=feasible,
        units="J and J/access",
    )


def carbon_break_even(
    *,
    current_carbon_kg_per_access: float | None,
    new_carbon_kg_per_access: float | None,
    adaptive_carbon_kg_per_access: float | None,
    migration_carbon_kg: float | None,
    allocated_embodied_carbon_kg: float | None,
    feasible: bool = True,
) -> BreakEvenResult:
    allocated = allocated_embodied_carbon_kg if allocated_embodied_carbon_kg is not None else 0.0
    return break_even_horizon(
        current_cost_per_access=current_carbon_kg_per_access,
        new_cost_per_access=new_carbon_kg_per_access,
        continuing_adaptive_overhead_per_access=adaptive_carbon_kg_per_access,
        one_time_transition_cost=migration_carbon_kg,
        one_time_allocated_cost=allocated,
        feasible=feasible,
        units="kgCO2e and kgCO2e/access",
    )


def overhead_ratio(overhead: float | None, gross_benefit: float | None) -> dict:
    if overhead is None or gross_benefit is None:
        return {"status": "insufficient_characterization", "ratio": None, "beneficial": None}
    if overhead < 0:
        raise ValueError("overhead must be non-negative")
    if gross_benefit <= 0:
        return {
            "status": "no_gross_benefit",
            "ratio": None if overhead > 0 else 0.0,
            "beneficial": False,
        }
    ratio = overhead / gross_benefit
    return {"status": "ok", "ratio": ratio, "beneficial": ratio < 1.0}
