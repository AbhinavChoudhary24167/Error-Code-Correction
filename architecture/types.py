"""Typed, extensible interfaces for ECC configurations and scenarios."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
from typing import Generic, Iterable, Mapping, TypeVar


METRIC_SOURCES = {
    "measured",
    "synthesized",
    "simulated",
    "analytical",
    "calibrated",
    "projected",
    "uncharacterized",
    "test_fixture",
}
ARCHITECTURE_TOPOLOGIES = {
    "fixed",
    "parallel",
    "gated_parallel",
    "shared_reconfigurable",
}


@dataclass(frozen=True)
class MetricProvenance:
    """Machine-readable provenance attached to a metric or metric group."""

    source: str
    technology_node_nm: int | None = None
    standard_cell_library: str | None = None
    device_model: str | None = None
    process_corner: str | None = None
    vdd_volts: float | None = None
    temperature_c: float | None = None
    tool: str | None = None
    tool_version: str | None = None
    calibration_source: str | None = None
    uncertainty: Mapping[str, float | str] = field(default_factory=dict)
    repository_commit: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        if self.source not in METRIC_SOURCES:
            raise ValueError(f"Unsupported metric source: {self.source}")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ECCConfiguration:
    """A concrete implementation of an ECC family.

    ``n`` and ``k`` describe one codeword. A logical memory word may require
    multiple codewords; :meth:`physical_bits_for_payload` handles that layout.
    """

    config_id: str
    family: str
    variant: str
    selector_code: str
    n: int
    k: int
    correction_bits: int
    detection_bits: int
    burst_length: int = 1
    adjacency_assumption: str = "none"
    encoder_implementation: str = "repository_model"
    decoder_implementation: str = "repository_model"
    interleaving_depth: int = 1
    scrub_interval_s: float = 10.0
    supported_nodes_nm: tuple[int, ...] = ()
    vdd_range: tuple[float, float] | None = None
    temperature_range_c: tuple[float, float] | None = None
    metric_provider: str = "legacy_selector_projected"
    provenance: MetricProvenance = field(
        default_factory=lambda: MetricProvenance(
            source="projected",
            notes="Legacy repository selector model; not synthesis or measurement.",
        )
    )

    def __post_init__(self) -> None:
        if self.n <= 0 or self.k <= 0 or self.n < self.k:
            raise ValueError("ECC configuration requires n >= k > 0")
        if self.correction_bits < 0 or self.detection_bits < 0:
            raise ValueError("Correction and detection capabilities must be non-negative")
        if self.interleaving_depth <= 0:
            raise ValueError("interleaving_depth must be positive")

    @property
    def rate(self) -> float:
        return self.k / self.n

    @property
    def parity_width(self) -> int:
        return self.n - self.k

    def codewords_for_payload(self, logical_width_bits: int) -> int:
        if logical_width_bits <= 0:
            raise ValueError("logical_width_bits must be positive")
        return math.ceil(logical_width_bits / self.k)

    def physical_bits_for_payload(self, logical_width_bits: int) -> int:
        return self.codewords_for_payload(logical_width_bits) * self.n

    def supports_pvt(self, node_nm: int, vdd: float, temperature_c: float) -> bool:
        if self.supported_nodes_nm and node_nm not in self.supported_nodes_nm:
            return False
        if self.vdd_range is not None and not self.vdd_range[0] <= vdd <= self.vdd_range[1]:
            return False
        if self.temperature_range_c is not None and not (
            self.temperature_range_c[0] <= temperature_c <= self.temperature_range_c[1]
        ):
            return False
        return True

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["rate"] = self.rate
        payload["parity_width"] = self.parity_width
        return payload

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "ECCConfiguration":
        prov_raw = raw.get("provenance", {})
        provenance = MetricProvenance(**dict(prov_raw)) if prov_raw else MetricProvenance(
            source="projected",
            notes="No external PPA artifact was supplied.",
        )
        return cls(
            config_id=str(raw["config_id"]),
            family=str(raw["family"]),
            variant=str(raw.get("variant", raw["config_id"])),
            selector_code=str(raw.get("selector_code", raw["config_id"])),
            n=int(raw["n"]),
            k=int(raw["k"]),
            correction_bits=int(raw.get("correction_bits", 0)),
            detection_bits=int(raw.get("detection_bits", 0)),
            burst_length=int(raw.get("burst_length", 1)),
            adjacency_assumption=str(raw.get("adjacency_assumption", "none")),
            encoder_implementation=str(raw.get("encoder_implementation", "repository_model")),
            decoder_implementation=str(raw.get("decoder_implementation", "repository_model")),
            interleaving_depth=int(raw.get("interleaving_depth", 1)),
            scrub_interval_s=float(raw.get("scrub_interval_s", 10.0)),
            supported_nodes_nm=tuple(int(v) for v in raw.get("supported_nodes_nm", ())),
            vdd_range=tuple(float(v) for v in raw["vdd_range"]) if raw.get("vdd_range") else None,
            temperature_range_c=(
                tuple(float(v) for v in raw["temperature_range_c"])
                if raw.get("temperature_range_c")
                else None
            ),
            metric_provider=str(raw.get("metric_provider", "legacy_selector_projected")),
            provenance=provenance,
        )


@dataclass(frozen=True)
class Workload:
    read_fraction: float
    write_fraction: float
    total_accesses: int
    decision_epochs: int = 1
    migrated_words_per_transition: int = 0

    def __post_init__(self) -> None:
        if self.read_fraction < 0 or self.write_fraction < 0:
            raise ValueError("read/write fractions must be non-negative")
        if not math.isclose(self.read_fraction + self.write_fraction, 1.0, abs_tol=1e-9):
            raise ValueError("read_fraction + write_fraction must equal 1")
        if self.total_accesses <= 0 or self.decision_epochs <= 0:
            raise ValueError("total_accesses and decision_epochs must be positive")
        if self.migrated_words_per_transition < 0:
            raise ValueError("migrated_words_per_transition must be non-negative")

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "Workload":
        return cls(
            read_fraction=float(raw.get("read_fraction", 0.5)),
            write_fraction=float(raw.get("write_fraction", 0.5)),
            total_accesses=int(raw["total_accesses"]),
            decision_epochs=int(raw.get("decision_epochs", 1)),
            migrated_words_per_transition=int(raw.get("migrated_words_per_transition", 0)),
        )


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    node_nm: int
    vdd: float
    temperature_c: float
    capacity_gib: float
    logical_width_bits: int
    bitcell_area_um2: float
    carbon_intensity_kgco2e_per_kwh: float
    fault_regime: str
    lifetime_hours: float
    workload: Workload
    constraints: Mapping[str, float] = field(default_factory=dict)
    bit_failure_probability: float | None = None
    memory_read_latency_ns: float | None = None
    memory_write_latency_ns: float | None = None

    def __post_init__(self) -> None:
        if self.capacity_gib <= 0 or self.logical_width_bits <= 0:
            raise ValueError("capacity_gib and logical_width_bits must be positive")
        if self.vdd <= 0 or self.bitcell_area_um2 < 0:
            raise ValueError("vdd must be positive and bitcell area non-negative")
        if self.carbon_intensity_kgco2e_per_kwh < 0 or self.lifetime_hours < 0:
            raise ValueError("carbon intensity and lifetime must be non-negative")
        if self.bit_failure_probability is not None and not 0 <= self.bit_failure_probability <= 1:
            raise ValueError("bit_failure_probability must be in [0, 1]")

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "Scenario":
        return cls(
            scenario_id=str(raw["scenario_id"]),
            node_nm=int(raw["node_nm"]),
            vdd=float(raw["vdd"]),
            temperature_c=float(raw["temperature_c"]),
            capacity_gib=float(raw["capacity_gib"]),
            logical_width_bits=int(raw["logical_width_bits"]),
            bitcell_area_um2=float(raw["bitcell_area_um2"]),
            carbon_intensity_kgco2e_per_kwh=float(raw["carbon_intensity_kgco2e_per_kwh"]),
            fault_regime=str(raw.get("fault_regime", "moderate")),
            lifetime_hours=float(raw.get("lifetime_hours", 8760.0)),
            workload=Workload.from_mapping(dict(raw["workload"])),
            constraints={str(k): float(v) for k, v in dict(raw.get("constraints", {})).items()},
            bit_failure_probability=(
                float(raw["bit_failure_probability"])
                if raw.get("bit_failure_probability") is not None
                else None
            ),
            memory_read_latency_ns=(
                float(raw["memory_read_latency_ns"])
                if raw.get("memory_read_latency_ns") is not None
                else None
            ),
            memory_write_latency_ns=(
                float(raw["memory_write_latency_ns"])
                if raw.get("memory_write_latency_ns") is not None
                else None
            ),
        )


T = TypeVar("T")


class CandidateRegistry(Generic[T]):
    """Small plugin registry; callers can register candidates without selector edits."""

    def __init__(self) -> None:
        self._items: dict[str, T] = {}

    def register(self, name: str, candidate: T) -> None:
        if name in self._items:
            raise ValueError(f"Candidate already registered: {name}")
        self._items[name] = candidate

    def get(self, name: str) -> T:
        try:
            return self._items[name]
        except KeyError as exc:
            raise KeyError(f"Unknown registered candidate: {name}") from exc

    def values(self) -> tuple[T, ...]:
        return tuple(self._items.values())

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._items))

    @classmethod
    def from_configurations(cls, candidates: Iterable[T], *, key: str = "config_id") -> "CandidateRegistry[T]":
        registry: CandidateRegistry[T] = cls()
        for candidate in candidates:
            registry.register(str(getattr(candidate, key)), candidate)
        return registry
