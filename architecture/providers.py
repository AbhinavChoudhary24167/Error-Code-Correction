"""Hardware-metric provider abstractions and repository adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
from pathlib import Path
from typing import Iterable, Mapping

from ecc_selector import select

from .mux import MuxCellCharacterization
from .types import ECCConfiguration, MetricProvenance, Scenario


class HardwareMetricProvider(ABC):
    """Common interface for analytical, synthesis, SPICE, and measured data."""

    provider_id: str

    @abstractmethod
    def evaluate(
        self,
        candidates: Iterable[ECCConfiguration],
        scenario: Scenario,
    ) -> list[dict]:
        raise NotImplementedError


class LegacySelectorProjectedProvider(HardwareMetricProvider):
    """Adapt the existing selector while labeling its PPA honestly."""

    provider_id = "legacy_selector_projected"

    def evaluate(
        self,
        candidates: Iterable[ECCConfiguration],
        scenario: Scenario,
    ) -> list[dict]:
        configs = list(candidates)
        supported = [
            item
            for item in configs
            if item.supports_pvt(scenario.node_nm, scenario.vdd, scenario.temperature_c)
        ]
        if not supported:
            return []
        selector_codes = [item.selector_code for item in supported]
        result = select(
            selector_codes,
            node=scenario.node_nm,
            vdd=scenario.vdd,
            temp=scenario.temperature_c,
            capacity_gib=scenario.capacity_gib,
            ci=scenario.carbon_intensity_kgco2e_per_kwh,
            bitcell_um2=scenario.bitcell_area_um2,
            mbu=scenario.fault_regime,
            scrub_s=min(item.scrub_interval_s for item in supported),
            lifetime_h=scenario.lifetime_hours,
            constraints={},
        )
        by_selector = {item.selector_code: item for item in supported}
        provenance = MetricProvenance(
            source="projected",
            technology_node_nm=scenario.node_nm,
            process_corner="unspecified",
            vdd_volts=scenario.vdd,
            temperature_c=scenario.temperature_c,
            tool="GREEN-ECC Python analytical selector",
            calibration_source="tech_calib.json, qcrit_sram6t.json, carbon_defaults.json",
            notes=(
                "Reliability is analytical/calibrated. Candidate area and latency are legacy projected "
                "constants; dynamic and leakage energy are unavailable in this selector path."
            ),
        )
        records: list[dict] = []
        for raw in result.get("candidate_records", []):
            config = by_selector[str(raw["code"])]
            record = dict(raw)
            record.update(
                {
                    "config_id": config.config_id,
                    "family": config.family,
                    "variant": config.variant,
                    "n": config.n,
                    "k": config.k,
                    "rate": config.rate,
                    "parity_width": config.parity_width,
                    "metric_provenance": {
                        "reliability": {
                            **provenance.to_dict(),
                            "source": "analytical",
                            "notes": "Hazucha-style SER and repository ECC coverage model.",
                        },
                        "area": provenance.to_dict(),
                        "latency": provenance.to_dict(),
                        "energy": {
                            **provenance.to_dict(),
                            "source": "uncharacterized",
                            "notes": "Only scrub energy is non-zero in the legacy selector record.",
                        },
                        "carbon": {
                            **provenance.to_dict(),
                            "source": "projected",
                            "notes": "Legacy embodied-carbon defaults include placeholder provenance.",
                        },
                    },
                    "legacy_scenario_hash": result.get("scenario_hash"),
                }
            )
            records.append(record)
        return records


class MuxCharacterizationProvider:
    """Exact-PVT loader for MUX cell characterization records.

    No interpolation or node scaling is performed. When no exact record exists,
    callers receive ``None`` and must retain analytical gate counts only.
    """

    _SOURCE_PRIORITY = {
        "measured": 6,
        "synthesized": 5,
        "simulated": 4,
        "calibrated": 3,
        "projected": 2,
        "analytical": 1,
        "test_fixture": 0,
    }

    def __init__(self, records: Iterable[Mapping[str, object]]) -> None:
        self._records = [dict(item) for item in records]

    @classmethod
    def from_json(cls, path: Path) -> "MuxCharacterizationProvider":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(payload.get("records", []))

    def resolve(
        self,
        *,
        node_nm: int,
        vdd: float,
        temperature_c: float,
        process_corner: str,
    ) -> MuxCellCharacterization | None:
        matching = [
            item
            for item in self._records
            if int(item["node_nm"]) == node_nm
            and float(item["vdd"]) == vdd
            and float(item["temperature_c"]) == temperature_c
            and str(item["process_corner"]) == process_corner
        ]
        if not matching:
            return None
        matching.sort(
            key=lambda item: self._SOURCE_PRIORITY.get(str(item.get("source", "analytical")), -1),
            reverse=True,
        )
        item = matching[0]
        return MuxCellCharacterization(
            area_um2=float(item["area_um2"]),
            delay_ns=float(item["delay_ns"]),
            switched_capacitance_f=float(item["switched_capacitance_f"]),
            leakage_current_a=float(item["leakage_current_a"]),
            switching_activity=float(item["switching_activity"]),
            source=str(item["source"]),
            node_nm=int(item["node_nm"]),
            vdd=float(item["vdd"]),
            temperature_c=float(item["temperature_c"]),
            process_corner=str(item["process_corner"]),
            library=str(item["library"]),
            tool=str(item["tool"]),
            tool_version=str(item["tool_version"]),
            calibration_source=str(item["calibration_source"]),
        )
