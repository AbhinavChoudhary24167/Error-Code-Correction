#!/usr/bin/env python3
"""ECC Selector based on runtime conditions."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ECCOption:
    ecc_type: str
    code: str
    correctable_bits: int
    burst_tolerance: int
    energy_per_read: float
    min_ber: float
    voltage_range: List[float]
    gate_overhead: int
    tags: List[str]


ECC_TABLE: List[ECCOption] = [
    ECCOption(
        ecc_type="Hamming_SEC-DED",
        code="(72,64)",
        correctable_bits=1,
        burst_tolerance=2,
        energy_per_read=1.08e-15,
        min_ber=1e-9,
        voltage_range=[0.4, 1.0],
        gate_overhead=12,
        tags=["low_power", "high_speed"],
    ),
    ECCOption(
        ecc_type="TAEC",
        code="(75,64)-I6",
        correctable_bits=3,
        burst_tolerance=3,
        energy_per_read=9.75e-16,
        min_ber=1e-8,
        voltage_range=[0.4, 0.8],
        gate_overhead=10,
        tags=["burst_resistant", "low_voltage"],
    ),
    ECCOption(
        ecc_type="BCH_DEC",
        code="(78,64)",
        correctable_bits=2,
        burst_tolerance=3,
        energy_per_read=2.34e-15,
        min_ber=1e-6,
        voltage_range=[0.5, 1.2],
        gate_overhead=25,
        tags=["medium_ber", "standard"],
    ),
    ECCOption(
        ecc_type="RS_SbEC_DbED",
        code="(79,64)",
        correctable_bits=1,
        burst_tolerance=4,
        energy_per_read=2.73e-15,
        min_ber=1e-5,
        voltage_range=[0.5, 1.2],
        gate_overhead=30,
        tags=["byte_level", "burst", "symbol_correct"],
    ),
    ECCOption(
        ecc_type="ErrorLocality_2G4L",
        code="custom",
        correctable_bits=2,
        burst_tolerance=4,
        energy_per_read=2.74e-15,
        min_ber=1e-6,
        voltage_range=[0.6, 1.2],
        gate_overhead=35,
        tags=["automotive", "burst", "high_coverage"],
    ),
]


def select_ecc(
    ber: float,
    burst_length: int,
    vdd: float,
    energy_budget: float,
    sustainability_mode: bool,
    required_correction: int,
) -> Optional[ECCOption]:
    """Return the best ECC option for the given conditions."""
    candidates = []
    for option in ECC_TABLE:
        if not (option.voltage_range[0] <= vdd <= option.voltage_range[1]):
            continue
        if ber < option.min_ber:
            continue
        if option.energy_per_read > energy_budget:
            continue
        if option.correctable_bits < required_correction:
            continue
        if option.burst_tolerance < burst_length:
            continue
        candidates.append(option)

    if not candidates:
        return None

    if sustainability_mode:
        candidates.sort(key=lambda o: o.energy_per_read)
    else:
        candidates.sort(
            key=lambda o: (o.correctable_bits, o.burst_tolerance, -o.energy_per_read),
            reverse=True,
        )
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Select an ECC scheme")
    parser.add_argument("ber", type=float, help="Bit error rate")
    parser.add_argument("burst_length", type=int, help="Burst error length")
    parser.add_argument("vdd", type=float, help="Supply voltage in volts")
    parser.add_argument("energy_budget", type=float, help="Energy budget per access")
    parser.add_argument("required_correction", type=int, help="Minimum correctable bits required")
    parser.add_argument("--sustainability", action="store_true", help="Prefer low energy ECCs")

    args = parser.parse_args()
    ecc = select_ecc(
        ber=args.ber,
        burst_length=args.burst_length,
        vdd=args.vdd,
        energy_budget=args.energy_budget,
        sustainability_mode=args.sustainability,
        required_correction=args.required_correction,
    )

    if ecc is None:
        print("No suitable ECC found for the provided parameters.")
        return

    print(f"Selected ECC_Type: {ecc.ecc_type}")
    print(f"Code: {ecc.code}")
    print(f"Correctable bits: {ecc.correctable_bits}")
    print(f"Burst tolerance: {ecc.burst_tolerance}")
    print(f"Estimated energy per read: {ecc.energy_per_read:.3e} J")
    print(f"Supported VDD range: {ecc.voltage_range[0]}-{ecc.voltage_range[1]} V")


if __name__ == "__main__":
    main()
