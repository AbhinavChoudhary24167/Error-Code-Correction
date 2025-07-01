"""4-state soft error model for SRAM bits.

Implements the Markov model from Equations (4.1) and (4.2) of the thesis
introduction. The supply voltage influences the state transition rates
\(\epsilon_1\) through \(\epsilon_4\). The raw soft error rate (SER) for a
single cell is computed as

    SER(VDD) = (epsilon1 * epsilon2 * epsilon3 * epsilon4) / VDD**k

as shown in Equation (4.1). For a memory word containing ``nodes`` bits the
resulting bit error rate (BER) follows Equation (4.2)

    BER = 1 - (1 - SER)**nodes.

``ber`` exposes this calculation. Parameters are bundled in
``DEFAULT_PARAMS`` so the model can be tuned without changing code.
"""
from __future__ import annotations

from dataclasses import dataclass
import argparse
from typing import Dict

# Default Markov parameters derived from the thesis tables.
DEFAULT_PARAMS: Dict[str, float] = {
    "epsilon1": 0.01,
    "epsilon2": 0.02,
    "epsilon3": 0.03,
    "epsilon4": 0.036,
    "k": 3.0,
}
"""Baseline transition probabilities and voltage exponent."""

# Alternative Gilbert-Elliott style parameters for quick experiments.
GILBERT_PARAMS: Dict[str, float] = {
    "epsilon1": 0.005,
    "epsilon2": 0.01,
    "epsilon3": 0.015,
    "epsilon4": 0.02,
    "k": 2.5,
}
"""Simplified two-state parameters."""

LOW_VOLTAGE_LIMIT = 0.4
"""Voltages below this value are outside the model's validity."""


def _ser(vdd: float, params: Dict[str, float]) -> float:
    """Return the raw soft error rate for a single bit.

    Parameters
    ----------
    vdd : float
        Supply voltage in volts.
    params : Dict[str, float]
        Model parameters read from ``DEFAULT_PARAMS`` or ``GILBERT_PARAMS``.
    """
    eps = (
        params["epsilon1"]
        * params["epsilon2"]
        * params["epsilon3"]
        * params["epsilon4"]
    )
    return eps / (vdd ** params["k"])


def ber(vdd: float, nodes: int = 22, params: Dict[str, float] | None = None) -> float:
    """Estimate the bit error rate at a given supply voltage.

    Parameters
    ----------
    vdd : float
        Supply voltage in volts. Must not be lower than ``LOW_VOLTAGE_LIMIT``.
    nodes : int
        Number of storage nodes (bits) in the word.
    params : optional
        Parameter dictionary, ``DEFAULT_PARAMS`` by default.

    Returns
    -------
    float
        Bit error rate according to Equation (4.2).
    """
    if vdd < LOW_VOLTAGE_LIMIT:
        raise ValueError("Voltage below model validity range")

    if params is None:
        params = DEFAULT_PARAMS

    ser = _ser(vdd, params)
    return 1.0 - (1.0 - ser) ** nodes


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate BER for a given VDD")
    parser.add_argument("vdd", type=float, help="Supply voltage in volts")
    parser.add_argument("--nodes", type=int, default=22, help="Number of bits")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--gilbert", action="store_true", help="Use Gilbert parameters")
    group.add_argument("--4mc", action="store_true", help="Use 4-state Markov parameters (default)")
    args = parser.parse_args()

    params = DEFAULT_PARAMS
    if args.gilbert:
        params = GILBERT_PARAMS

    result = ber(args.vdd, nodes=args.nodes, params=params)
    print(f"BER: {result:.3e}")


if __name__ == "__main__":
    main()
