"""Exact and baseline schedulers for transition-aware ECC co-design."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import itertools
import math
from typing import Callable, Mapping, Sequence

from .traces import ScenarioTrace, TraceEpoch
from .transitions import ArchitectureDesign, ECCOperatingMode, TransitionCost


@dataclass(frozen=True)
class EpochModeCost:
    epoch_id: str
    mode_id: str
    ecc_id: str
    design_id: str
    objective_cost: float | None
    operational_energy_j: float | None
    operational_carbon_kgco2e: float | None
    latency_ns: float
    fit: float
    area_mm2: float | None
    feasible: bool
    feasibility_probability: float
    objective_std: float
    constraint_margins: Mapping[str, float | None]
    violations: tuple[str, ...]
    cost_breakdown: Mapping[str, float | None]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ScheduleResult:
    policy: str
    status: str
    objective: str
    path: tuple[str, ...]
    total_objective: float | None
    epoch_objective: float | None
    transition_objective: float | None
    implementation_objective: float | None
    transitions: int
    timeline: tuple[Mapping[str, object], ...]
    theoretical_complexity: str
    reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


TransitionLookup = Callable[[int, str, str], TransitionCost]


def _uniform_probability_below(nominal: float, relative: float, limit: float) -> float:
    if relative <= 0:
        return 1.0 if nominal <= limit else 0.0
    low = nominal * max(0.0, 1.0 - relative)
    high = nominal * (1.0 + relative)
    if limit < low:
        return 0.0
    if limit >= high or high == low:
        return 1.0
    return (limit - low) / (high - low)


def evaluate_epoch_mode(
    *,
    epoch: TraceEpoch,
    mode: ECCOperatingMode,
    design: ArchitectureDesign,
    objective: str,
    area_limit_mm2: float | None,
) -> EpochModeCost:
    regime = epoch.fault_regime
    try:
        read_energy = float(mode.read_energy_j_per_access_by_regime[regime])
        write_energy = float(mode.write_energy_j_per_access_by_regime[regime])
        nominal_fit = float(mode.fit_by_regime[regime])
        nominal_latency = float(mode.latency_ns_by_regime[regime])
    except KeyError as exc:
        raise ValueError(f"mode {mode.ecc_id} does not model fault regime {regime}") from exc
    delta_temp = epoch.temperature_c - mode.reference_temperature_c
    temp_energy_factor = max(0.0, 1.0 + mode.energy_temperature_coefficient_per_c * delta_temp)
    vdd_energy_factor = (epoch.vdd_volts / mode.reference_vdd_volts) ** 2
    per_access_codec = (
        epoch.read_fraction * read_energy + epoch.write_fraction * write_energy
    ) * temp_energy_factor * vdd_energy_factor
    adaptability = design.adaptability_energy_j_per_access
    metadata = design.metadata_lookup_energy_j_per_access
    dynamic_known = adaptability is not None and metadata is not None
    dynamic = (
        epoch.accesses * (per_access_codec + float(adaptability) + float(metadata))
        if dynamic_known
        else None
    )
    mode_leakage = mode.leakage_power_w
    inactive_leakage = design.inactive_engine_leakage_w
    leakage = (
        epoch.duration_s * (mode_leakage + float(inactive_leakage))
        if inactive_leakage is not None
        else None
    )
    decision = design.controller_energy_j_per_decision
    energy = (
        float(dynamic) + float(leakage) + float(decision)
        if dynamic is not None and leakage is not None and decision is not None
        else None
    )
    carbon = (
        energy * epoch.grid_carbon_intensity_kgco2e_per_kwh / 3.6e6
        if energy is not None
        else None
    )
    adaptability_dynamic = (
        epoch.accesses * float(adaptability) if adaptability is not None else None
    )
    metadata_dynamic = (
        epoch.accesses * float(metadata) if metadata is not None else None
    )
    selected_leakage = epoch.duration_s * mode_leakage
    inactive_leakage_energy = (
        epoch.duration_s * float(inactive_leakage)
        if inactive_leakage is not None
        else None
    )
    continuing_adaptability_energy = (
        float(adaptability_dynamic)
        + float(metadata_dynamic)
        + float(inactive_leakage_energy)
        + float(decision)
        if adaptability_dynamic is not None
        and metadata_dynamic is not None
        and inactive_leakage_energy is not None
        and decision is not None
        else None
    )
    fit = (
        nominal_fit
        * epoch.fit_multiplier
        * math.exp(mode.fit_temperature_coefficient_per_c * delta_temp)
        * (mode.reference_vdd_volts / epoch.vdd_volts) ** mode.fit_vdd_exponent
    )
    latency = nominal_latency * (
        mode.reference_vdd_volts / epoch.vdd_volts
    ) ** mode.latency_vdd_exponent
    margins: dict[str, float | None] = {
        "fit": epoch.fit_limit - fit,
        "latency_ns": epoch.latency_limit_ns - latency,
        "area_mm2": area_limit_mm2 - design.area_mm2
        if area_limit_mm2 is not None and design.area_mm2 is not None
        else None,
    }
    violations = []
    if fit > epoch.fit_limit:
        violations.append("fit")
    if latency > epoch.latency_limit_ns:
        violations.append("latency_ns")
    if area_limit_mm2 is not None and design.area_mm2 is not None and design.area_mm2 > area_limit_mm2:
        violations.append("area_mm2")
    if area_limit_mm2 is not None and design.area_mm2 is None:
        violations.append("area_uncharacterized")
    if energy is None:
        violations.append("operational_energy_uncharacterized")
    probability = _uniform_probability_below(
        fit, float(epoch.uncertainty.get("fit", 0.0)), epoch.fit_limit
    ) * _uniform_probability_below(
        latency, float(epoch.uncertainty.get("latency", 0.0)), epoch.latency_limit_ns
    )
    objective_value = energy if objective == "lifecycle_energy_j" else carbon
    relative = float(
        epoch.uncertainty.get(
            "energy" if objective == "lifecycle_energy_j" else "carbon", 0.0
        )
    )
    objective_std = abs(float(objective_value or 0.0)) * relative / math.sqrt(3.0)
    return EpochModeCost(
        epoch_id=epoch.epoch_id,
        mode_id=f"{design.design_id}:{mode.ecc_id}",
        ecc_id=mode.ecc_id,
        design_id=design.design_id,
        objective_cost=objective_value,
        operational_energy_j=energy,
        operational_carbon_kgco2e=carbon,
        latency_ns=latency,
        fit=fit,
        area_mm2=design.area_mm2,
        feasible=not violations,
        feasibility_probability=probability,
        objective_std=objective_std,
        constraint_margins=margins,
        violations=tuple(violations),
        cost_breakdown={
            "accesses": epoch.accesses,
            "codec_dynamic_energy_j": epoch.accesses * per_access_codec,
            "adaptability_dynamic_energy_j": adaptability_dynamic,
            "metadata_dynamic_energy_j": metadata_dynamic,
            "leakage_energy_j": leakage,
            "selected_engine_leakage_energy_j": selected_leakage,
            "inactive_engine_leakage_energy_j": inactive_leakage_energy,
            "controller_decision_energy_j": decision,
            "controller_decision_frequency_hz": 1.0 / epoch.duration_s,
            "continuing_adaptability_energy_j": continuing_adaptability_energy,
            "continuing_adaptability_carbon_kgco2e": (
                continuing_adaptability_energy
                * epoch.grid_carbon_intensity_kgco2e_per_kwh
                / 3.6e6
                if continuing_adaptability_energy is not None
                else None
            ),
        },
    )


def build_epoch_costs(
    trace: ScenarioTrace,
    modes: Mapping[str, ECCOperatingMode],
    design: ArchitectureDesign,
    *,
    objective: str,
    area_limit_mm2: float | None,
) -> tuple[dict[str, EpochModeCost], ...]:
    return tuple(
        {
            ecc_id: evaluate_epoch_mode(
                epoch=epoch,
                mode=modes[ecc_id],
                design=design,
                objective=objective,
                area_limit_mm2=area_limit_mm2,
            )
            for ecc_id in design.supported_eccs
        }
        for epoch in trace.epochs
    )


def _implementation_objective(design: ArchitectureDesign, objective: str) -> float | None:
    if objective == "lifecycle_energy_j":
        return design.implementation_energy_j
    if objective == "lifecycle_carbon_kgco2e":
        return design.embodied_carbon_kgco2e
    raise ValueError(f"unsupported scheduling objective: {objective}")


def evaluate_path(
    *,
    policy_name: str,
    path: Sequence[str],
    epoch_costs: Sequence[Mapping[str, EpochModeCost]],
    transition_lookup: TransitionLookup,
    design: ArchitectureDesign,
    objective: str,
    theoretical_complexity: str,
    selection_reasons: Sequence[str] | None = None,
) -> ScheduleResult:
    if len(path) != len(epoch_costs):
        raise ValueError("schedule path length must equal epoch count")
    implementation = _implementation_objective(design, objective)
    if implementation is None:
        return ScheduleResult(
            policy_name,
            "insufficient_characterization",
            objective,
            tuple(path),
            None,
            None,
            None,
            None,
            0,
            (),
            theoretical_complexity,
            "architecture implementation objective is unavailable",
        )
    epoch_total = 0.0
    transition_total = 0.0
    transition_count = 0
    timeline: list[dict[str, object]] = []
    for index, ecc_id in enumerate(path):
        cost = epoch_costs[index][ecc_id]
        if not cost.feasible or cost.objective_cost is None:
            return ScheduleResult(
                policy_name,
                "infeasible",
                objective,
                tuple(path),
                None,
                None,
                None,
                implementation,
                transition_count,
                tuple(timeline),
                theoretical_complexity,
                f"{cost.epoch_id}/{ecc_id} is infeasible: {', '.join(cost.violations)}",
            )
        transition = None
        transition_value = 0.0
        if index and path[index - 1] != ecc_id:
            transition = transition_lookup(index, path[index - 1], ecc_id)
            value = transition.objective_cost(objective)
            if value is None:
                return ScheduleResult(
                    policy_name,
                    "infeasible",
                    objective,
                    tuple(path),
                    None,
                    None,
                    None,
                    implementation,
                    transition_count,
                    tuple(timeline),
                    theoretical_complexity,
                    transition.reason or "transition is infeasible or uncharacterized",
                )
            transition_value = float(value)
            transition_total += transition_value
            transition_count += 1
        epoch_total += float(cost.objective_cost)
        timeline.append(
            {
                "epoch_index": index,
                "epoch_id": cost.epoch_id,
                "ecc_id": ecc_id,
                "mode_id": cost.mode_id,
                "epoch_objective": cost.objective_cost,
                "transition_objective": transition_value,
                "transition": transition.to_dict() if transition is not None else None,
                "fit": cost.fit,
                "latency_ns": cost.latency_ns,
                "feasibility_probability": cost.feasibility_probability,
                "constraint_margins": dict(cost.constraint_margins),
                "reason": selection_reasons[index] if selection_reasons else "policy decision",
            }
        )
    return ScheduleResult(
        policy_name,
        "ok",
        objective,
        tuple(path),
        implementation + epoch_total + transition_total,
        epoch_total,
        transition_total,
        implementation,
        transition_count,
        tuple(timeline),
        theoretical_complexity,
    )


def exact_dynamic_programming(
    *,
    epoch_costs: Sequence[Mapping[str, EpochModeCost]],
    transition_lookup: TransitionLookup,
    design: ArchitectureDesign,
    objective: str,
    min_dwell_epochs: int = 1,
    max_transitions: int | None = None,
    policy_name: str = "transition_aware_dynamic_programming",
) -> ScheduleResult:
    if min_dwell_epochs <= 0:
        raise ValueError("min_dwell_epochs must be positive")
    if not epoch_costs:
        raise ValueError("epoch_costs must not be empty")
    modes = tuple(epoch_costs[0])
    if any(tuple(costs) != modes for costs in epoch_costs):
        raise ValueError("all epochs must expose the same ordered mode set")
    # State is (mode, capped dwell, transitions). Extending the state keeps the
    # dynamic program exact under dwell and switching-rate constraints.
    state: dict[tuple[str, int, int], tuple[float, tuple[str, ...]]] = {}
    for mode in modes:
        cost = epoch_costs[0][mode]
        if cost.feasible and cost.objective_cost is not None:
            state[(mode, 1, 0)] = (float(cost.objective_cost), (mode,))
    for index in range(1, len(epoch_costs)):
        next_state: dict[tuple[str, int, int], tuple[float, tuple[str, ...]]] = {}
        for (previous, dwell, switches), (accumulated, path) in state.items():
            for current in modes:
                cost = epoch_costs[index][current]
                if not cost.feasible or cost.objective_cost is None:
                    continue
                changed = current != previous
                if changed and dwell < min_dwell_epochs:
                    continue
                next_switches = switches + int(changed)
                if max_transitions is not None and next_switches > max_transitions:
                    continue
                transition_value = 0.0
                if changed:
                    transition = transition_lookup(index, previous, current)
                    value = transition.objective_cost(objective)
                    if value is None:
                        continue
                    transition_value = float(value)
                next_dwell = 1 if changed else min(min_dwell_epochs, dwell + 1)
                key = (current, next_dwell, next_switches)
                candidate = accumulated + transition_value + float(cost.objective_cost)
                incumbent = next_state.get(key)
                if incumbent is None or candidate < incumbent[0]:
                    next_state[key] = (candidate, path + (current,))
        state = next_state
        if not state:
            break
    if not state:
        return ScheduleResult(
            policy_name,
            "infeasible",
            objective,
            (),
            None,
            None,
            None,
            _implementation_objective(design, objective),
            0,
            (),
            "O(T*M^2) basic; extended by dwell and transition-count state",
            "no feasible schedule",
        )
    _, best_path = min(state.values(), key=lambda item: (item[0], item[1]))
    return evaluate_path(
        policy_name=policy_name,
        path=best_path,
        epoch_costs=epoch_costs,
        transition_lookup=transition_lookup,
        design=design,
        objective=objective,
        theoretical_complexity="O(T*M^2) basic; O(T*M^2*D*S) with dwell D and switch-count S state",
    )


def best_static_schedule(
    *,
    epoch_costs: Sequence[Mapping[str, EpochModeCost]],
    transition_lookup: TransitionLookup,
    design: ArchitectureDesign,
    objective: str,
) -> ScheduleResult:
    candidates = []
    for mode in epoch_costs[0]:
        result = evaluate_path(
            policy_name="best_static",
            path=(mode,) * len(epoch_costs),
            epoch_costs=epoch_costs,
            transition_lookup=transition_lookup,
            design=design,
            objective=objective,
            theoretical_complexity="O(T*M)",
            selection_reasons=("single mode retained for complete trace",) * len(epoch_costs),
        )
        if result.status == "ok":
            candidates.append(result)
    if not candidates:
        return ScheduleResult(
            "best_static", "infeasible", objective, (), None, None, None,
            _implementation_objective(design, objective), 0, (), "O(T*M)",
            "no single ECC is feasible across the complete trace",
        )
    return min(candidates, key=lambda item: (float(item.total_objective), item.path))


def snapshot_oracle_schedule(
    *,
    epoch_costs: Sequence[Mapping[str, EpochModeCost]],
    transition_lookup: TransitionLookup,
    design: ArchitectureDesign,
    objective: str,
) -> ScheduleResult:
    path = []
    for costs in epoch_costs:
        feasible = [
            item for item in costs.values() if item.feasible and item.objective_cost is not None
        ]
        if not feasible:
            return ScheduleResult(
                "snapshot_oracle_ignoring_transitions", "infeasible", objective, (), None,
                None, None, _implementation_objective(design, objective), 0, (), "O(T*M)",
                "an epoch has no feasible mode",
            )
        path.append(min(feasible, key=lambda item: (float(item.objective_cost), item.ecc_id)).ecc_id)
    return evaluate_path(
        policy_name="snapshot_oracle_ignoring_transitions",
        path=path,
        epoch_costs=epoch_costs,
        transition_lookup=transition_lookup,
        design=design,
        objective=objective,
        theoretical_complexity="O(T*M); transition costs ignored during decisions and charged afterward",
        selection_reasons=("minimum feasible snapshot cost; transition ignored",) * len(path),
    )


def greedy_schedule(
    *,
    epoch_costs: Sequence[Mapping[str, EpochModeCost]],
    transition_lookup: TransitionLookup,
    design: ArchitectureDesign,
    objective: str,
) -> ScheduleResult:
    path: list[str] = []
    reasons: list[str] = []
    for index, costs in enumerate(epoch_costs):
        candidates = []
        for mode, cost in costs.items():
            if not cost.feasible or cost.objective_cost is None:
                continue
            transition_value = 0.0
            if path and path[-1] != mode:
                value = transition_lookup(index, path[-1], mode).objective_cost(objective)
                if value is None:
                    continue
                transition_value = float(value)
            candidates.append((float(cost.objective_cost) + transition_value, mode, transition_value))
        if not candidates:
            return ScheduleResult(
                "greedy", "infeasible", objective, tuple(path), None, None, None,
                _implementation_objective(design, objective), 0, (), "O(T*M)",
                "no feasible local action",
            )
        _, mode, transition_value = min(candidates)
        path.append(mode)
        reasons.append(f"minimum current epoch plus immediate transition cost ({transition_value:.6g})")
    return evaluate_path(
        policy_name="greedy",
        path=path,
        epoch_costs=epoch_costs,
        transition_lookup=transition_lookup,
        design=design,
        objective=objective,
        theoretical_complexity="O(T*M)",
        selection_reasons=reasons,
    )


def fault_lookup_schedule(
    *,
    trace: ScenarioTrace,
    lookup: Mapping[str, str],
    epoch_costs: Sequence[Mapping[str, EpochModeCost]],
    transition_lookup: TransitionLookup,
    design: ArchitectureDesign,
    objective: str,
    safe_fallback: str,
) -> ScheduleResult:
    path = [str(lookup.get(epoch.fault_regime, safe_fallback)) for epoch in trace.epochs]
    return evaluate_path(
        policy_name="fault_regime_lookup",
        path=path,
        epoch_costs=epoch_costs,
        transition_lookup=transition_lookup,
        design=design,
        objective=objective,
        theoretical_complexity="O(T)",
        selection_reasons=("configured fault-regime lookup",) * len(path),
    )


def robust_dynamic_programming(
    *,
    epoch_costs: Sequence[Mapping[str, EpochModeCost]],
    transition_lookup: TransitionLookup,
    design: ArchitectureDesign,
    objective: str,
    chance_constraint_epsilon: float,
    risk_aversion_z: float,
    min_dwell_epochs: int,
    max_transitions: int | None,
) -> ScheduleResult:
    if not 0 <= chance_constraint_epsilon < 1:
        raise ValueError("chance_constraint_epsilon must be in [0, 1)")
    robust_costs = []
    for costs in epoch_costs:
        robust_costs.append(
            {
                mode: replace(
                    cost,
                    feasible=(
                        cost.feasible
                        and cost.feasibility_probability >= 1.0 - chance_constraint_epsilon
                    ),
                    objective_cost=(
                        float(cost.objective_cost) + risk_aversion_z * cost.objective_std
                        if cost.objective_cost is not None
                        else None
                    ),
                    violations=(
                        cost.violations
                        if cost.feasibility_probability >= 1.0 - chance_constraint_epsilon
                        else cost.violations + ("chance_constraint",)
                    ),
                )
                for mode, cost in costs.items()
            }
        )
    robust = exact_dynamic_programming(
        epoch_costs=robust_costs,
        transition_lookup=transition_lookup,
        design=design,
        objective=objective,
        min_dwell_epochs=min_dwell_epochs,
        max_transitions=max_transitions,
        policy_name="robust_transition_aware",
    )
    if robust.status != "ok":
        return robust
    # Re-evaluate the chosen path with nominal costs so reported lifecycle cost
    # remains in physical units; robust optimization cost is a decision aid.
    return evaluate_path(
        policy_name="robust_transition_aware",
        path=robust.path,
        epoch_costs=epoch_costs,
        transition_lookup=transition_lookup,
        design=design,
        objective=objective,
        theoretical_complexity=robust.theoretical_complexity,
        selection_reasons=(
            f"chance constraint >= {1.0 - chance_constraint_epsilon:.3f}; risk margin z={risk_aversion_z}",
        ) * len(robust.path),
    )


def brute_force_optimal_path(
    *,
    epoch_costs: Sequence[Mapping[str, EpochModeCost]],
    transition_lookup: TransitionLookup,
    objective: str,
    min_dwell_epochs: int = 1,
) -> tuple[tuple[str, ...], float] | None:
    """Exponential reference used only to validate small dynamic programs."""

    modes = tuple(epoch_costs[0])
    best = None
    for path in itertools.product(modes, repeat=len(epoch_costs)):
        dwell = 1
        valid = True
        total = 0.0
        for index, mode in enumerate(path):
            cost = epoch_costs[index][mode]
            if not cost.feasible or cost.objective_cost is None:
                valid = False
                break
            total += float(cost.objective_cost)
            if index:
                if mode != path[index - 1]:
                    if dwell < min_dwell_epochs:
                        valid = False
                        break
                    value = transition_lookup(index, path[index - 1], mode).objective_cost(objective)
                    if value is None:
                        valid = False
                        break
                    total += float(value)
                    dwell = 1
                else:
                    dwell += 1
        if valid and (best is None or (total, path) < (best[1], best[0])):
            best = (tuple(path), total)
    return best
