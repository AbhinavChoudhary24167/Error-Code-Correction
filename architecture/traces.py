"""Versioned time-varying scenario traces for transition-aware ECC studies."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import random
from typing import Mapping, Sequence


TRACE_SCHEMA_VERSION = 1
TRACE_SOURCES = {"deterministic", "generated_synthetic", "user_supplied"}


@dataclass(frozen=True)
class TraceEpoch:
    """One ordered operating epoch.

    Access counts and duration are both retained because dynamic energy scales
    with accesses while leakage and migration deadlines scale with time.
    """

    epoch_id: str
    duration_s: float
    accesses: int
    active_words: int
    fault_regime: str
    fit_multiplier: float
    vdd_volts: float
    temperature_c: float
    read_fraction: float
    write_fraction: float
    latency_limit_ns: float
    fit_limit: float
    grid_carbon_intensity_kgco2e_per_kwh: float
    active_region_fraction: float = 1.0
    uncertainty: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.duration_s <= 0 or self.accesses <= 0 or self.active_words <= 0:
            raise ValueError("epoch duration, accesses, and active_words must be positive")
        if self.fit_multiplier <= 0 or self.vdd_volts <= 0:
            raise ValueError("FIT multiplier and VDD must be positive")
        if self.latency_limit_ns <= 0 or self.fit_limit < 0:
            raise ValueError("latency limit must be positive and FIT limit non-negative")
        if self.grid_carbon_intensity_kgco2e_per_kwh < 0:
            raise ValueError("grid carbon intensity must be non-negative")
        if not 0 <= self.active_region_fraction <= 1:
            raise ValueError("active_region_fraction must be in [0, 1]")
        if self.read_fraction < 0 or self.write_fraction < 0:
            raise ValueError("read/write fractions must be non-negative")
        if abs(self.read_fraction + self.write_fraction - 1.0) > 1e-9:
            raise ValueError("read_fraction + write_fraction must equal one")
        if any(float(value) < 0 for value in self.uncertainty.values()):
            raise ValueError("uncertainty intervals must be non-negative")

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "TraceEpoch":
        return cls(
            epoch_id=str(raw["epoch_id"]),
            duration_s=float(raw["duration_s"]),
            accesses=int(raw["accesses"]),
            active_words=int(raw["active_words"]),
            fault_regime=str(raw["fault_regime"]),
            fit_multiplier=float(raw.get("fit_multiplier", 1.0)),
            vdd_volts=float(raw["vdd_volts"]),
            temperature_c=float(raw["temperature_c"]),
            read_fraction=float(raw.get("read_fraction", 0.5)),
            write_fraction=float(raw.get("write_fraction", 0.5)),
            latency_limit_ns=float(raw["latency_limit_ns"]),
            fit_limit=float(raw["fit_limit"]),
            grid_carbon_intensity_kgco2e_per_kwh=float(
                raw["grid_carbon_intensity_kgco2e_per_kwh"]
            ),
            active_region_fraction=float(raw.get("active_region_fraction", 1.0)),
            uncertainty={
                str(key): float(value)
                for key, value in dict(raw.get("uncertainty", {})).items()
            },
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ScenarioTrace:
    trace_id: str
    epochs: tuple[TraceEpoch, ...]
    source: str
    seed: int | None = None
    generator: Mapping[str, object] | None = None
    schema_version: int = TRACE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != TRACE_SCHEMA_VERSION:
            raise ValueError(f"unsupported trace schema version: {self.schema_version}")
        if self.source not in TRACE_SOURCES:
            raise ValueError(f"unsupported trace source: {self.source}")
        if not self.epochs:
            raise ValueError("a scenario trace requires at least one epoch")
        ids = [item.epoch_id for item in self.epochs]
        if len(ids) != len(set(ids)):
            raise ValueError("epoch_id values must be unique")
        if self.source == "generated_synthetic" and (self.seed is None or self.generator is None):
            raise ValueError("synthetic traces require a seed and generator metadata")

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "ScenarioTrace":
        return cls(
            trace_id=str(raw["trace_id"]),
            epochs=tuple(TraceEpoch.from_mapping(item) for item in raw["epochs"]),
            source=str(raw.get("source", "user_supplied")),
            seed=int(raw["seed"]) if raw.get("seed") is not None else None,
            generator=dict(raw["generator"]) if raw.get("generator") is not None else None,
            schema_version=int(raw.get("schema_version", TRACE_SCHEMA_VERSION)),
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "trace_id": self.trace_id,
            "source": self.source,
            "seed": self.seed,
            "generator": dict(self.generator) if self.generator is not None else None,
            "epochs": [item.to_dict() for item in self.epochs],
        }


def _regime_pattern(family: str, count: int, rng: random.Random, period: int) -> list[str]:
    if family == "stationary_sbu":
        return ["sbu"] * count
    if family == "stationary_mbu":
        return ["mbu"] * count
    if family == "one_time_sbu_to_mbu":
        return ["sbu" if index < count // 2 else "mbu" for index in range(count)]
    if family == "periodic_fault_transitions":
        return ["sbu" if (index // max(period, 1)) % 2 == 0 else "mbu" for index in range(count)]
    if family == "short_noisy_fluctuations":
        pattern = ["sbu"] * count
        for index in range(1, count, max(period, 2)):
            pattern[index] = "mbu"
        return pattern
    if family in {
        "temperature_vdd_phases",
        "changing_read_write_intensity",
        "grid_carbon_transition",
    }:
        return ["sbu"] * count
    if family in {"combined_changes", "uncertain_transitions"}:
        pattern = []
        current = "sbu"
        for index in range(count):
            if index and index % max(period, 1) == 0:
                current = "mbu" if current == "sbu" else "sbu"
            if family == "uncertain_transitions" and rng.random() < 0.15:
                pattern.append("mbu" if current == "sbu" else "sbu")
            else:
                pattern.append(current)
        return pattern
    raise ValueError(f"unknown synthetic trace family: {family}")


def generate_synthetic_trace(spec: Mapping[str, object]) -> ScenarioTrace:
    """Generate one transparent, deterministic synthetic trace family."""

    family = str(spec["family"])
    count = int(spec.get("epoch_count", 12))
    seed = int(spec.get("seed", 1723))
    if count <= 0:
        raise ValueError("epoch_count must be positive")
    rng = random.Random(seed)
    period = int(spec.get("period_epochs", 2))
    regimes = _regime_pattern(family, count, rng, period)
    base_accesses = int(spec.get("accesses_per_epoch", 10_000_000))
    base_duration = float(spec.get("duration_s", 1.0))
    active_words = int(spec.get("active_words", 1_048_576))
    base_temp = float(spec.get("temperature_c", 75.0))
    base_vdd = float(spec.get("vdd_volts", 0.8))
    low_ci = float(spec.get("low_carbon_intensity", 0.1))
    high_ci = float(spec.get("high_carbon_intensity", 0.7))
    fit_limit = float(spec.get("fit_limit", 250.0))
    latency_limit = float(spec.get("latency_limit_ns", 3.0))
    uncertainty = float(spec.get("relative_uncertainty", 0.0))
    epochs: list[TraceEpoch] = []
    for index, regime in enumerate(regimes):
        second_half = index >= count // 2
        temperature = base_temp
        vdd = base_vdd
        read_fraction = 0.7
        carbon_intensity = low_ci
        fit_multiplier = 1.0
        active_fraction = 1.0
        if family in {"temperature_vdd_phases", "combined_changes"} and second_half:
            temperature += 20.0
            vdd = max(0.55, base_vdd - 0.1)
            fit_multiplier = 1.25
        if family in {"changing_read_write_intensity", "combined_changes"}:
            read_fraction = 0.9 if not second_half else 0.2
        if family in {"grid_carbon_transition", "combined_changes"}:
            carbon_intensity = low_ci if not second_half else high_ci
        if family in {"periodic_fault_transitions", "short_noisy_fluctuations"}:
            active_fraction = 0.125
        if family == "uncertain_transitions":
            uncertainty = max(uncertainty, 0.25)
            active_fraction = 0.25
        epochs.append(
            TraceEpoch(
                epoch_id=f"e{index:03d}",
                duration_s=base_duration,
                accesses=base_accesses,
                active_words=active_words,
                fault_regime=regime,
                fit_multiplier=fit_multiplier,
                vdd_volts=vdd,
                temperature_c=temperature,
                read_fraction=read_fraction,
                write_fraction=1.0 - read_fraction,
                latency_limit_ns=latency_limit,
                fit_limit=fit_limit,
                grid_carbon_intensity_kgco2e_per_kwh=carbon_intensity,
                active_region_fraction=active_fraction,
                uncertainty={
                    "fit": uncertainty,
                    "latency": uncertainty / 2.0,
                    "energy": uncertainty,
                    "carbon": uncertainty,
                },
            )
        )
    generator = {str(key): value for key, value in spec.items()}
    return ScenarioTrace(
        trace_id=str(spec.get("trace_id", family)),
        epochs=tuple(epochs),
        source="generated_synthetic",
        seed=seed,
        generator=generator,
    )


def load_traces(payload: Mapping[str, object]) -> tuple[ScenarioTrace, ...]:
    traces: list[ScenarioTrace] = []
    for item in payload.get("traces", []):
        traces.append(ScenarioTrace.from_mapping(item))
    for item in payload.get("trace_generators", []):
        traces.append(generate_synthetic_trace(item))
    if not traces:
        raise ValueError("configuration requires at least one trace or trace generator")
    return tuple(traces)


def trace_family_names() -> Sequence[str]:
    return (
        "stationary_sbu",
        "stationary_mbu",
        "one_time_sbu_to_mbu",
        "periodic_fault_transitions",
        "short_noisy_fluctuations",
        "temperature_vdd_phases",
        "changing_read_write_intensity",
        "grid_carbon_transition",
        "combined_changes",
        "uncertain_transitions",
    )
