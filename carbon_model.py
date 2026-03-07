from __future__ import annotations

"""Calibrated carbon accounting helpers.

Embodied (static) carbon is modeled from effective area, node-dependent
fabrication intensity and yield loss. Operational (dynamic) carbon is modeled
from energy and grid emission factors.
"""

from pathlib import Path
import json
from typing import Any, Mapping

JOULES_PER_KWH = 3.6e6
_DEFAULT_CALIB = Path(__file__).with_name("carbon_calib.json")


def _load_calibration(calib_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(calib_path) if calib_path is not None else _DEFAULT_CALIB
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    for key in ("node_defaults", "grid_defaults", "lifetime_defaults"):
        if key not in data:
            raise ValueError(f"Missing calibration section: {key}")
    return data


def _as_float(value: float | int | None, name: str, *, allow_none: bool = False) -> float | None:
    if value is None:
        if allow_none:
            return None
        raise ValueError(f"{name} is required")
    out = float(value)
    if out < 0.0:
        raise ValueError(f"{name} must be non-negative")
    return out


def _resolve_node(node_nm: int, calib: Mapping[str, Any]) -> dict[str, Any]:
    nodes = calib["node_defaults"]
    key = str(int(node_nm))
    if key in nodes:
        return dict(nodes[key])
    # Fallback to nearest configured node for backward-compatible operation.
    choices = sorted(int(k) for k in nodes)
    nearest = min(choices, key=lambda n: abs(n - int(node_nm)))
    return dict(nodes[str(nearest)])


def _resolve_area_cm2(
    *,
    area_cm2: float | None,
    memory_bits: int | None,
    bitcell_area_um2: float | None,
    area_scaling_factor: float,
) -> float:
    if area_cm2 is not None:
        return float(_as_float(area_cm2, "area_cm2"))
    if memory_bits is None or bitcell_area_um2 is None:
        raise ValueError("Provide area_cm2 directly, or memory_bits with bitcell_area_um2")
    mem_bits = int(memory_bits)
    bitcell = float(_as_float(bitcell_area_um2, "bitcell_area_um2"))
    if mem_bits <= 0:
        raise ValueError("memory_bits must be positive")
    # 1 um^2 = 1e-8 cm^2
    return mem_bits * bitcell * 1e-8 * area_scaling_factor


def estimate_embodied_carbon(
    *,
    node_nm: int,
    area_cm2: float | None = None,
    memory_bits: int | None = None,
    bitcell_area_um2: float | None = None,
    yield_loss_factor: float | None = None,
    fab_intensity_kgco2e_per_cm2: float | None = None,
    uncertainty_margin: float | None = None,
    area_scaling_factor: float | None = None,
    calib_path: str | Path | None = None,
) -> dict[str, Any]:
    """Estimate embodied/static carbon with nominal and bounded variants."""

    calib = _load_calibration(calib_path)
    node_cfg = _resolve_node(node_nm, calib)
    intensity_cfg = node_cfg["fab_intensity_kgco2e_per_cm2"]
    yield_cfg = node_cfg["yield_loss_factor"]

    scaling = float(
        _as_float(
            area_scaling_factor if area_scaling_factor is not None else node_cfg.get("area_scaling_factor", 1.0),
            "area_scaling_factor",
        )
    )
    resolved_area_cm2 = _resolve_area_cm2(
        area_cm2=area_cm2,
        memory_bits=memory_bits,
        bitcell_area_um2=bitcell_area_um2,
        area_scaling_factor=scaling,
    )
    resolved_yield = float(
        _as_float(yield_loss_factor if yield_loss_factor is not None else yield_cfg["nominal"], "yield_loss_factor")
    )
    resolved_intensity = float(
        _as_float(
            fab_intensity_kgco2e_per_cm2 if fab_intensity_kgco2e_per_cm2 is not None else intensity_cfg["nominal"],
            "fab_intensity_kgco2e_per_cm2",
        )
    )
    margin = float(_as_float(uncertainty_margin if uncertainty_margin is not None else node_cfg["uncertainty_margin"], "uncertainty_margin"))

    nominal = resolved_area_cm2 * resolved_intensity * resolved_yield
    best_case = resolved_area_cm2 * float(intensity_cfg["min"]) * float(yield_cfg["min"]) * (1.0 - margin)
    worst_case = resolved_area_cm2 * float(intensity_cfg["max"]) * float(yield_cfg["max"]) * (1.0 + margin)

    return {
        "nominal_kgco2e": nominal,
        "lower_bound_kgco2e": nominal * (1.0 - margin),
        "upper_bound_kgco2e": nominal * (1.0 + margin),
        "best_case_kgco2e": best_case,
        "worst_case_kgco2e": worst_case,
        "assumptions": {
            "node_nm": int(node_nm),
            "effective_area_cm2": resolved_area_cm2,
            "fab_intensity_kgco2e_per_cm2": resolved_intensity,
            "yield_loss_factor": resolved_yield,
            "uncertainty_margin": margin,
            "area_proxy_used": area_cm2 is None,
            "memory_bits": memory_bits,
            "bitcell_area_um2": bitcell_area_um2,
            "area_scaling_factor": scaling,
        },
    }


def estimate_operational_carbon(
    *,
    energy_joules: float,
    grid_region: str = "global_avg",
    grid_factor_kgco2e_per_kwh: float | None = None,
    best_grid_factor_kgco2e_per_kwh: float | None = None,
    worst_grid_factor_kgco2e_per_kwh: float | None = None,
    lifetime_energy_joules: float | None = None,
    accesses_per_day: float | None = None,
    total_accesses: float | None = None,
    years: float | None = None,
    workload_repetitions: float | None = None,
    calib_path: str | Path | None = None,
) -> dict[str, Any]:
    """Estimate operational/dynamic carbon with lifetime scaling support."""

    calib = _load_calibration(calib_path)
    grid_cfg = calib["grid_defaults"]
    lifetime_cfg = calib["lifetime_defaults"]

    energy_per_unit_j = float(_as_float(energy_joules, "energy_joules"))
    if lifetime_energy_joules is not None:
        total_energy_j = float(_as_float(lifetime_energy_joules, "lifetime_energy_joules"))
        lifetime_mode = "explicit_lifetime_energy"
    elif total_accesses is not None:
        total_energy_j = energy_per_unit_j * float(_as_float(total_accesses, "total_accesses"))
        lifetime_mode = "total_accesses"
    elif workload_repetitions is not None:
        total_energy_j = energy_per_unit_j * float(_as_float(workload_repetitions, "workload_repetitions"))
        lifetime_mode = "workload_repetitions"
    else:
        yrs = float(_as_float(years if years is not None else lifetime_cfg.get("years", 1.0), "years"))
        apd = float(_as_float(accesses_per_day if accesses_per_day is not None else lifetime_cfg.get("accesses_per_day", 1.0), "accesses_per_day"))
        total_energy_j = energy_per_unit_j * apd * 365.0 * yrs
        lifetime_mode = "accesses_per_day_and_years"

    regions = grid_cfg["regions_kgco2e_per_kwh"]
    if grid_factor_kgco2e_per_kwh is None:
        if grid_region not in regions:
            available = ", ".join(sorted(regions.keys()))
            raise ValueError(f"Unknown grid_region={grid_region}; available: {available}")
        grid_factor = float(regions[grid_region])
    else:
        grid_factor = float(_as_float(grid_factor_kgco2e_per_kwh, "grid_factor_kgco2e_per_kwh"))

    best_grid = float(
        _as_float(
            best_grid_factor_kgco2e_per_kwh if best_grid_factor_kgco2e_per_kwh is not None else grid_cfg["best_case_kgco2e_per_kwh"],
            "best_grid_factor_kgco2e_per_kwh",
        )
    )
    worst_grid = float(
        _as_float(
            worst_grid_factor_kgco2e_per_kwh if worst_grid_factor_kgco2e_per_kwh is not None else grid_cfg["worst_case_kgco2e_per_kwh"],
            "worst_grid_factor_kgco2e_per_kwh",
        )
    )

    energy_kwh = total_energy_j / JOULES_PER_KWH
    nominal = energy_kwh * grid_factor
    best_case = energy_kwh * best_grid
    worst_case = energy_kwh * worst_grid

    return {
        "nominal_kgco2e": nominal,
        "best_case_kgco2e": best_case,
        "worst_case_kgco2e": worst_case,
        "energy_kwh": energy_kwh,
        "lifetime_energy_joules": total_energy_j,
        "assumptions": {
            "grid_region": grid_region,
            "grid_factor_kgco2e_per_kwh": grid_factor,
            "best_grid_factor_kgco2e_per_kwh": best_grid,
            "worst_grid_factor_kgco2e_per_kwh": worst_grid,
            "lifetime_mode": lifetime_mode,
            "energy_joules_per_unit": energy_per_unit_j,
        },
    }


def estimate_total_carbon(
    *,
    embodied_kgco2e: float,
    dynamic_kgco2e_lifetime: float,
) -> float:
    """Return lifetime total carbon in kgCO2e."""
    embodied = float(_as_float(embodied_kgco2e, "embodied_kgco2e"))
    dynamic = float(_as_float(dynamic_kgco2e_lifetime, "dynamic_kgco2e_lifetime"))
    return embodied + dynamic


def estimate_carbon_bounds(
    *,
    node_nm: int,
    energy_joules: float,
    area_cm2: float | None = None,
    memory_bits: int | None = None,
    bitcell_area_um2: float | None = None,
    grid_region: str = "global_avg",
    grid_factor_kgco2e_per_kwh: float | None = None,
    yield_loss_factor: float | None = None,
    fab_intensity_kgco2e_per_cm2: float | None = None,
    uncertainty_margin: float | None = None,
    years: float | None = None,
    accesses_per_day: float | None = None,
    total_accesses: float | None = None,
    workload_repetitions: float | None = None,
    lifetime_energy_joules: float | None = None,
    calib_path: str | Path | None = None,
) -> dict[str, Any]:
    """Estimate nominal/best/worst static, dynamic, and total carbon."""

    embodied = estimate_embodied_carbon(
        node_nm=node_nm,
        area_cm2=area_cm2,
        memory_bits=memory_bits,
        bitcell_area_um2=bitcell_area_um2,
        yield_loss_factor=yield_loss_factor,
        fab_intensity_kgco2e_per_cm2=fab_intensity_kgco2e_per_cm2,
        uncertainty_margin=uncertainty_margin,
        calib_path=calib_path,
    )
    operational = estimate_operational_carbon(
        energy_joules=energy_joules,
        grid_region=grid_region,
        grid_factor_kgco2e_per_kwh=grid_factor_kgco2e_per_kwh,
        years=years,
        accesses_per_day=accesses_per_day,
        total_accesses=total_accesses,
        workload_repetitions=workload_repetitions,
        lifetime_energy_joules=lifetime_energy_joules,
        calib_path=calib_path,
    )

    nominal = {
        "static_carbon_kgco2e": embodied["nominal_kgco2e"],
        "dynamic_carbon_kgco2e": operational["nominal_kgco2e"],
    }
    nominal["total_carbon_kgco2e"] = estimate_total_carbon(
        embodied_kgco2e=nominal["static_carbon_kgco2e"],
        dynamic_kgco2e_lifetime=nominal["dynamic_carbon_kgco2e"],
    )

    best_case = {
        "static_carbon_kgco2e": embodied["best_case_kgco2e"],
        "dynamic_carbon_kgco2e": operational["best_case_kgco2e"],
    }
    best_case["total_carbon_kgco2e"] = best_case["static_carbon_kgco2e"] + best_case["dynamic_carbon_kgco2e"]

    worst_case = {
        "static_carbon_kgco2e": embodied["worst_case_kgco2e"],
        "dynamic_carbon_kgco2e": operational["worst_case_kgco2e"],
    }
    worst_case["total_carbon_kgco2e"] = worst_case["static_carbon_kgco2e"] + worst_case["dynamic_carbon_kgco2e"]

    return {
        "nominal": nominal,
        "best_case": best_case,
        "worst_case": worst_case,
        "assumptions": {
            "embodied": embodied["assumptions"],
            "operational": operational["assumptions"],
            "energy_kwh": operational["energy_kwh"],
            "lifetime_energy_joules": operational["lifetime_energy_joules"],
        },
    }


def carbon_breakdown(*, bounds: Mapping[str, Any]) -> dict[str, Any]:
    """Return normalized carbon score view from ``estimate_carbon_bounds`` output."""

    nominal = bounds["nominal"]
    best_case = bounds["best_case"]
    worst_case = bounds["worst_case"]
    total_nominal = float(nominal["total_carbon_kgco2e"])
    total_best = float(best_case["total_carbon_kgco2e"])
    total_worst = float(worst_case["total_carbon_kgco2e"])

    if total_nominal > 0.0:
        static_fraction = float(nominal["static_carbon_kgco2e"]) / total_nominal
        dynamic_fraction = float(nominal["dynamic_carbon_kgco2e"]) / total_nominal
    else:
        static_fraction = 0.0
        dynamic_fraction = 0.0

    span = max(1e-12, total_worst - total_best)
    nominal_score = max(0.0, min(1.0, (total_worst - total_nominal) / span))

    return {
        "static_carbon_kgco2e": float(nominal["static_carbon_kgco2e"]),
        "dynamic_carbon_kgco2e": float(nominal["dynamic_carbon_kgco2e"]),
        "total_carbon_kgco2e": total_nominal,
        "static_fraction": static_fraction,
        "dynamic_fraction": dynamic_fraction,
        "nominal_score": nominal_score,
        "best_case_score": 1.0,
        "worst_case_score": 0.0,
        "assumptions": dict(bounds.get("assumptions", {})),
    }


__all__ = [
    "JOULES_PER_KWH",
    "estimate_embodied_carbon",
    "estimate_operational_carbon",
    "estimate_total_carbon",
    "estimate_carbon_bounds",
    "carbon_breakdown",
]
