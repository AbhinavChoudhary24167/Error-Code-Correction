"""Architecture-level ECC selection fabric and MUX resource models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Iterable, Mapping

from .types import ECCConfiguration


@dataclass(frozen=True)
class MuxCellCharacterization:
    """Characterization for one 2:1 MUX cell at one exact PVT point.

    ``switching_activity`` is the expected transition probability per MUX cell
    per operation. The dynamic-energy convention is ``alpha * C * V^2`` and
    does not include an additional one-half factor.
    """

    area_um2: float
    delay_ns: float
    switched_capacitance_f: float
    leakage_current_a: float
    switching_activity: float
    source: str
    node_nm: int
    vdd: float
    temperature_c: float
    process_corner: str
    library: str
    tool: str
    tool_version: str
    calibration_source: str

    def __post_init__(self) -> None:
        numeric = (
            self.area_um2,
            self.delay_ns,
            self.switched_capacitance_f,
            self.leakage_current_a,
            self.switching_activity,
        )
        if any(value < 0 for value in numeric):
            raise ValueError("MUX characterization values must be non-negative")
        if not 0 <= self.switching_activity <= 1:
            raise ValueError("switching_activity must be in [0, 1]")


@dataclass(frozen=True)
class MuxPath:
    name: str
    width_bits: int
    modes: int
    wire_delay_ns: float = 0.0
    route_area_um2: float = 0.0

    def __post_init__(self) -> None:
        if self.width_bits < 0 or self.modes <= 0:
            raise ValueError("MUX path width must be non-negative and modes positive")
        if self.wire_delay_ns < 0 or self.route_area_um2 < 0:
            raise ValueError("Wire delay and route area must be non-negative")


def mux_depth(modes: int) -> int:
    if modes <= 0:
        raise ValueError("modes must be positive")
    return 0 if modes == 1 else math.ceil(math.log2(modes))


def mux_2to1_count(width_bits: int, modes: int, *, implementation: str = "pruned") -> int:
    """Return the exact 2:1 cell count for a balanced M-to-1 tree."""

    if width_bits < 0 or modes <= 0:
        raise ValueError("width_bits must be non-negative and modes positive")
    if modes == 1 or width_bits == 0:
        return 0
    if implementation == "pruned":
        return width_bits * (modes - 1)
    if implementation == "padded":
        return width_bits * ((2 ** mux_depth(modes)) - 1)
    raise ValueError("implementation must be 'pruned' or 'padded'")


def evaluate_mux_path(
    path: MuxPath,
    *,
    implementation: str = "pruned",
    characterization: MuxCellCharacterization | None = None,
) -> dict:
    depth = mux_depth(path.modes)
    count = mux_2to1_count(path.width_bits, path.modes, implementation=implementation)
    if count == 0:
        return {
            "name": path.name,
            "width_bits": path.width_bits,
            "modes": path.modes,
            "implementation": implementation,
            "depth": 0,
            "mux_2to1_count": 0,
            "area_um2": 0.0,
            "delay_ns": 0.0,
            "dynamic_energy_j_per_operation": 0.0,
            "leakage_power_w": 0.0,
            "physical_metrics_characterized": True,
        }
    if characterization is None:
        return {
            "name": path.name,
            "width_bits": path.width_bits,
            "modes": path.modes,
            "implementation": implementation,
            "depth": depth,
            "mux_2to1_count": count,
            "area_um2": None,
            "delay_ns": None,
            "dynamic_energy_j_per_operation": None,
            "leakage_power_w": None,
            "physical_metrics_characterized": False,
        }

    area = count * characterization.area_um2 + path.route_area_um2
    delay = depth * characterization.delay_ns + path.wire_delay_ns
    energy = (
        count
        * characterization.switching_activity
        * characterization.switched_capacitance_f
        * characterization.vdd**2
    )
    leakage = count * characterization.vdd * characterization.leakage_current_a
    return {
        "name": path.name,
        "width_bits": path.width_bits,
        "modes": path.modes,
        "implementation": implementation,
        "depth": depth,
        "mux_2to1_count": count,
        "area_um2": area,
        "delay_ns": delay,
        "dynamic_energy_j_per_operation": energy,
        "leakage_power_w": leakage,
        "physical_metrics_characterized": True,
        "characterization": asdict(characterization),
    }


def physical_container_layout(
    candidates: Iterable[ECCConfiguration], logical_width_bits: int
) -> dict:
    configs = list(candidates)
    if not configs:
        raise ValueError("At least one ECC configuration is required")
    used = {
        item.config_id: item.physical_bits_for_payload(logical_width_bits)
        for item in configs
    }
    container_bits = max(used.values())
    entries = []
    for item in configs:
        physical_bits = used[item.config_id]
        entries.append(
            {
                "config_id": item.config_id,
                "family": item.family,
                "n": item.n,
                "k": item.k,
                "codewords_per_logical_word": item.codewords_for_payload(logical_width_bits),
                "physical_bits_used": physical_bits,
                "container_bits": container_bits,
                "padding_bits": container_bits - physical_bits,
                "capacity_efficiency": logical_width_bits / container_bits,
            }
        )
    return {
        "layout": "fixed_nmax_physical_slot",
        "logical_width_bits": logical_width_bits,
        "container_bits": container_bits,
        "entries": entries,
    }


def protected_metadata_bits(modes: int, protection: str) -> dict:
    if modes <= 0:
        raise ValueError("modes must be positive")
    raw_bits = 0 if modes == 1 else math.ceil(math.log2(modes))
    factors = {"none": 1, "parity": 2, "triplicated": 3}
    if protection not in factors:
        raise ValueError("metadata protection must be none, parity, or triplicated")
    stored_bits = raw_bits * factors[protection]
    return {
        "mode_bits": raw_bits,
        "protection": protection,
        "stored_bits": stored_bits,
        "protection_factor": factors[protection],
    }


def metadata_failure_probability(
    modes: int,
    protection: str,
    bit_failure_probability: float | None,
) -> float | None:
    metadata = protected_metadata_bits(modes, protection)
    raw_bits = metadata["mode_bits"]
    if raw_bits == 0:
        return 0.0
    if bit_failure_probability is None:
        return None
    p = float(bit_failure_probability)
    if not 0 <= p <= 1:
        raise ValueError("bit_failure_probability must be in [0, 1]")
    if protection == "triplicated":
        group_fail = 3 * p * p * (1 - p) + p**3
        return 1 - (1 - group_fail) ** raw_bits
    if protection == "parity":
        # Conservative approximation: parity detects but cannot correct a bit
        # failure, so a detected metadata error triggers the safe fallback.
        return 1 - (1 - p) ** raw_bits
    return 1 - (1 - p) ** raw_bits


def system_failure_probability(
    ecc_failure_probability: float,
    *,
    mux_failure_probability: float | None = None,
    controller_failure_probability: float | None = None,
    metadata_failure_probability_value: float | None = None,
) -> dict:
    """Combine independent failure terms with an explicit fault-tree model."""

    terms = {
        "ecc": ecc_failure_probability,
        "mux": mux_failure_probability,
        "controller": controller_failure_probability,
        "metadata": metadata_failure_probability_value,
    }
    enabled = {name: value for name, value in terms.items() if value is not None}
    for name, value in enabled.items():
        if not 0 <= float(value) <= 1:
            raise ValueError(f"{name} failure probability must be in [0, 1]")
    success = 1.0
    for value in enabled.values():
        success *= 1.0 - float(value)
    return {
        "system_failure_probability": 1.0 - success,
        "terms": enabled,
        "assumption": "Independent failure events; disabled terms are omitted, not assumed zero.",
    }


def default_selection_paths(
    *,
    topology: str,
    modes: int,
    logical_width_bits: int,
    container_bits: int,
    status_width_bits: int,
    path_overrides: Mapping[str, Mapping[str, float]] | None = None,
) -> tuple[MuxPath, ...]:
    if topology == "fixed" or modes == 1:
        return (
            MuxPath("write_codeword_mux", container_bits, 1),
            MuxPath("read_data_mux", logical_width_bits, 1),
            MuxPath("read_status_mux", status_width_bits, 1),
        )
    if topology not in {"parallel", "gated_parallel", "shared_reconfigurable"}:
        raise ValueError(f"Unknown architecture topology: {topology}")

    overrides = dict(path_overrides or {})

    def build(name: str, width: int) -> MuxPath:
        values = dict(overrides.get(name, {}))
        return MuxPath(
            name=name,
            width_bits=width,
            modes=modes,
            wire_delay_ns=float(values.get("wire_delay_ns", 0.0)),
            route_area_um2=float(values.get("route_area_um2", 0.0)),
        )

    paths = [
        build("write_codeword_mux", container_bits),
        build("read_data_mux", logical_width_bits),
        build("read_status_mux", status_width_bits),
    ]
    if topology == "shared_reconfigurable":
        paths.append(build("shared_input_route", container_bits))
    return tuple(paths)


def evaluate_selection_fabric(
    paths: Iterable[MuxPath],
    *,
    implementation: str,
    characterization: MuxCellCharacterization | None,
) -> dict:
    evaluated = [
        evaluate_mux_path(
            path,
            implementation=implementation,
            characterization=characterization,
        )
        for path in paths
    ]
    total_cells = sum(int(item["mux_2to1_count"]) for item in evaluated)
    complete = all(bool(item["physical_metrics_characterized"]) for item in evaluated)

    def sum_optional(name: str) -> float | None:
        values = [item[name] for item in evaluated]
        return sum(float(value) for value in values) if all(value is not None for value in values) else None

    return {
        "paths": evaluated,
        "mux_2to1_count_total": total_cells,
        "area_um2_total": sum_optional("area_um2"),
        "dynamic_energy_j_per_operation_total": sum_optional("dynamic_energy_j_per_operation"),
        "leakage_power_w_total": sum_optional("leakage_power_w"),
        "max_path_delay_ns": (
            max(float(item["delay_ns"]) for item in evaluated)
            if complete and evaluated
            else None
        ),
        "physical_metrics_characterized": complete,
    }


def compare_topology_logical_resources(
    candidates: Iterable[ECCConfiguration],
    *,
    logical_width_bits: int,
    status_width_bits: int = 4,
    implementation: str = "pruned",
    metadata_protection: str = "triplicated",
) -> list[dict]:
    configs = list(candidates)
    layout = physical_container_layout(configs, logical_width_bits)
    modes = len(configs)
    results = []
    for topology in ("fixed", "parallel", "gated_parallel", "shared_reconfigurable"):
        active_modes = 1 if topology == "fixed" else modes
        paths = default_selection_paths(
            topology=topology,
            modes=active_modes,
            logical_width_bits=logical_width_bits,
            container_bits=int(layout["container_bits"]),
            status_width_bits=status_width_bits,
        )
        fabric = evaluate_selection_fabric(
            paths,
            implementation=implementation,
            characterization=None,
        )
        results.append(
            {
                "topology": topology,
                "engine_instances": modes if topology in {"parallel", "gated_parallel"} else 1,
                "mux_2to1_count": fabric["mux_2to1_count_total"],
                "mux_max_depth": max(int(path["depth"]) for path in fabric["paths"]),
                "metadata_bits": protected_metadata_bits(
                    active_modes, metadata_protection
                )["stored_bits"],
                "container_bits": (
                    None if topology == "fixed" else layout["container_bits"]
                ),
                "physical_ppa_status": (
                    "zero_selection_overhead"
                    if topology == "fixed"
                    else "uncharacterized_without_exact_pvt_provider"
                ),
            }
        )
    return results
