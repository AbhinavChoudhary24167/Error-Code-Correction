"""ECC/design definitions and complete, asymmetric transition-cost models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Mapping

from .granularity import evaluate_granularity, scale_transition_for_granularity
from .traces import TraceEpoch


ARCHITECTURE_MODES = {"fixed", "configurable", "adaptive"}


@dataclass(frozen=True)
class ArchitectureDesign:
    design_id: str
    architecture_mode: str
    topology: str
    granularity: str
    supported_eccs: tuple[str, ...]
    metadata_protection: str
    total_words: int
    bank_count: int = 8
    page_words: int = 512
    mux_replication_regions: int | None = None
    mux_2to1_cells_per_replica: int = 0
    adaptability_energy_j_per_access: float | None = None
    metadata_lookup_energy_j_per_access: float | None = None
    controller_energy_j_per_decision: float | None = None
    inactive_engine_leakage_w: float | None = None
    area_mm2: float | None = None
    embodied_carbon_kgco2e: float | None = None
    implementation_energy_j: float | None = None
    physical_word_selection_credible: bool = False
    provenance: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.architecture_mode not in ARCHITECTURE_MODES:
            raise ValueError(f"unsupported architecture mode: {self.architecture_mode}")
        if not self.supported_eccs:
            raise ValueError("architecture design requires at least one ECC")
        if self.architecture_mode == "fixed" and len(self.supported_eccs) != 1:
            raise ValueError("a fixed design must instantiate exactly one ECC")
        if self.total_words <= 0:
            raise ValueError("total_words must be positive")
        optional_nonnegative = (
            self.adaptability_energy_j_per_access,
            self.metadata_lookup_energy_j_per_access,
            self.controller_energy_j_per_decision,
            self.inactive_engine_leakage_w,
            self.area_mm2,
            self.embodied_carbon_kgco2e,
            self.implementation_energy_j,
        )
        if any(value is not None and value < 0 for value in optional_nonnegative):
            raise ValueError("design cost terms must be non-negative")

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "ArchitectureDesign":
        return cls(
            design_id=str(raw["design_id"]),
            architecture_mode=str(raw["architecture_mode"]),
            topology=str(raw["topology"]),
            granularity=str(raw["granularity"]),
            supported_eccs=tuple(str(value) for value in raw["supported_eccs"]),
            metadata_protection=str(raw.get("metadata_protection", "triplicated")),
            total_words=int(raw["total_words"]),
            bank_count=int(raw.get("bank_count", 8)),
            page_words=int(raw.get("page_words", 512)),
            mux_replication_regions=(
                int(raw["mux_replication_regions"])
                if raw.get("mux_replication_regions") is not None
                else None
            ),
            mux_2to1_cells_per_replica=int(raw.get("mux_2to1_cells_per_replica", 0)),
            adaptability_energy_j_per_access=(
                float(raw["adaptability_energy_j_per_access"])
                if raw.get("adaptability_energy_j_per_access") is not None
                else None
            ),
            metadata_lookup_energy_j_per_access=(
                float(raw["metadata_lookup_energy_j_per_access"])
                if raw.get("metadata_lookup_energy_j_per_access") is not None
                else None
            ),
            controller_energy_j_per_decision=(
                float(raw["controller_energy_j_per_decision"])
                if raw.get("controller_energy_j_per_decision") is not None
                else None
            ),
            inactive_engine_leakage_w=(
                float(raw["inactive_engine_leakage_w"])
                if raw.get("inactive_engine_leakage_w") is not None
                else None
            ),
            area_mm2=float(raw["area_mm2"]) if raw.get("area_mm2") is not None else None,
            embodied_carbon_kgco2e=(
                float(raw["embodied_carbon_kgco2e"])
                if raw.get("embodied_carbon_kgco2e") is not None
                else None
            ),
            implementation_energy_j=(
                float(raw["implementation_energy_j"])
                if raw.get("implementation_energy_j") is not None
                else None
            ),
            physical_word_selection_credible=bool(
                raw.get("physical_word_selection_credible", False)
            ),
            provenance=dict(raw.get("provenance", {})),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ECCOperatingMode:
    ecc_id: str
    family: str
    read_energy_j_per_access_by_regime: Mapping[str, float]
    write_energy_j_per_access_by_regime: Mapping[str, float]
    fit_by_regime: Mapping[str, float]
    latency_ns_by_regime: Mapping[str, float]
    leakage_power_w: float
    reference_vdd_volts: float = 0.8
    reference_temperature_c: float = 75.0
    energy_temperature_coefficient_per_c: float = 0.0
    fit_temperature_coefficient_per_c: float = 0.0
    fit_vdd_exponent: float = 0.0
    latency_vdd_exponent: float = 1.0
    provenance: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.reference_vdd_volts <= 0 or self.leakage_power_w < 0:
            raise ValueError("reference VDD must be positive and leakage non-negative")
        mappings = (
            self.read_energy_j_per_access_by_regime,
            self.write_energy_j_per_access_by_regime,
            self.fit_by_regime,
            self.latency_ns_by_regime,
        )
        if any(not mapping for mapping in mappings):
            raise ValueError("operating mode metric mappings must not be empty")
        if any(float(value) < 0 for mapping in mappings for value in mapping.values()):
            raise ValueError("operating mode metrics must be non-negative")

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "ECCOperatingMode":
        def numeric_mapping(name: str) -> dict[str, float]:
            return {str(key): float(value) for key, value in dict(raw[name]).items()}

        return cls(
            ecc_id=str(raw["ecc_id"]),
            family=str(raw["family"]),
            read_energy_j_per_access_by_regime=numeric_mapping(
                "read_energy_j_per_access_by_regime"
            ),
            write_energy_j_per_access_by_regime=numeric_mapping(
                "write_energy_j_per_access_by_regime"
            ),
            fit_by_regime=numeric_mapping("fit_by_regime"),
            latency_ns_by_regime=numeric_mapping("latency_ns_by_regime"),
            leakage_power_w=float(raw.get("leakage_power_w", 0.0)),
            reference_vdd_volts=float(raw.get("reference_vdd_volts", 0.8)),
            reference_temperature_c=float(raw.get("reference_temperature_c", 75.0)),
            energy_temperature_coefficient_per_c=float(
                raw.get("energy_temperature_coefficient_per_c", 0.0)
            ),
            fit_temperature_coefficient_per_c=float(
                raw.get("fit_temperature_coefficient_per_c", 0.0)
            ),
            fit_vdd_exponent=float(raw.get("fit_vdd_exponent", 0.0)),
            latency_vdd_exponent=float(raw.get("latency_vdd_exponent", 1.0)),
            provenance=dict(raw.get("provenance", {})),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TransitionCost:
    from_mode: str
    to_mode: str
    allowed: bool
    energy_j: float | None
    carbon_kgco2e: float | None
    latency_s: float | None
    migrated_words: int
    temporary_words: int
    characterization_status: str
    reason: str = ""

    def objective_cost(self, objective: str) -> float | None:
        if not self.allowed:
            return None
        if objective == "lifecycle_energy_j":
            return self.energy_j
        if objective == "lifecycle_carbon_kgco2e":
            return self.carbon_kgco2e
        raise ValueError(f"unsupported scheduling objective: {objective}")

    def to_dict(self) -> dict:
        return asdict(self)


class TransitionModel:
    """Build complete per-epoch transition costs from a physical-unit model."""

    def __init__(self, raw: Mapping[str, object]) -> None:
        self.base = dict(raw.get("base", {}))
        self.overrides = {
            (str(item["from_ecc"]), str(item["to_ecc"])): dict(item)
            for item in raw.get("overrides", [])
        }
        self.schema_version = int(raw.get("schema_version", 1))
        if self.schema_version != 1:
            raise ValueError("unsupported transition-cost schema version")

    def evaluate(
        self,
        *,
        from_ecc: str,
        to_ecc: str,
        design: ArchitectureDesign,
        epoch: TraceEpoch,
    ) -> TransitionCost:
        from_mode = f"{design.design_id}:{from_ecc}"
        to_mode = f"{design.design_id}:{to_ecc}"
        if from_ecc == to_ecc:
            return TransitionCost(
                from_mode,
                to_mode,
                True,
                0.0,
                0.0,
                0.0,
                0,
                0,
                "identity",
                "mode unchanged",
            )
        if design.architecture_mode == "fixed":
            return TransitionCost(
                from_mode,
                to_mode,
                False,
                None,
                None,
                None,
                0,
                0,
                "infeasible",
                "fixed architecture cannot change ECC",
            )
        raw = dict(self.base)
        raw.update(self.overrides.get((from_ecc, to_ecc), {}))
        granularity = evaluate_granularity(
            granularity=design.granularity,
            total_words=min(design.total_words, epoch.active_words),
            active_region_fraction=epoch.active_region_fraction,
            mode_count=len(design.supported_eccs),
            metadata_protection=design.metadata_protection,
            bank_count=design.bank_count,
            page_words=design.page_words,
            mux_replication_regions=design.mux_replication_regions,
            physical_word_selection_credible=design.physical_word_selection_credible,
        )
        scaled = scale_transition_for_granularity(raw, granularity)
        if not bool(scaled.get("allowed", False)):
            return TransitionCost(
                from_mode,
                to_mode,
                False,
                None,
                None,
                None,
                0,
                0,
                str(scaled.get("characterization_status", "infeasible")),
                str(scaled.get("reason", "transition disabled")),
            )
        energy = scaled.get("migration_energy_j")
        explicit_carbon = scaled.get("one_time_carbon_kgco2e")
        carbon = None
        if energy is not None:
            carbon = (
                float(energy)
                * epoch.grid_carbon_intensity_kgco2e_per_kwh
                / 3.6e6
            ) + float(explicit_carbon or 0.0)
        elif explicit_carbon is not None:
            carbon = float(explicit_carbon)
        latency = scaled.get("transition_latency_s")
        allowed = latency is None or float(latency) <= epoch.duration_s
        return TransitionCost(
            from_mode,
            to_mode,
            allowed,
            float(energy) if energy is not None else None,
            carbon,
            float(latency) if latency is not None else None,
            int(scaled.get("migrated_words", 0)),
            int(scaled.get("dual_format_temporary_words", 0)),
            str(scaled.get("characterization_status", "uncharacterized")),
            "" if allowed else "transition duration exceeds epoch duration",
        )
