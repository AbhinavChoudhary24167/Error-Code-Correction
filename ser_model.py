r"""4-state soft error model for SRAM bits.

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
import math
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


@dataclass
class HazuchaParams:
    """Parameters for the Hazucha–Svensson SER model.

    Attributes
    ----------
    Qs_fC:
        Fitted charge collection parameter in femtocoulombs.
    flux_rel:
        Neutron flux relative to sea level at 45° latitude.
    area_um2:
        Sensitive area of the storage node in square micrometres.
    C:
        Technology dependent constant. Defaults to ``2.2e-5``.
    """

    Qs_fC: float
    flux_rel: float
    area_um2: float
    C: float = 2.2e-5


def ser_hazucha(Qcrit_fC: float, hp: HazuchaParams) -> float:
    """Return the FIT per node using the Hazucha–Svensson model.

    The model relates the critical charge of a node to the resulting soft
    error rate via an exponential law.
    """

    return hp.C * hp.flux_rel * hp.area_um2 * math.exp(-Qcrit_fC / hp.Qs_fC)


def flux_from_location(
    alt_km: float, latitude_deg: float, flux_rel: float | None = None
) -> float:
    """Return relative neutron flux for a given location.

    The Hazucha–Svensson model uses neutron flux relative to sea level at
    45° latitude as its environmental scaling factor.  ``flux_rel`` allows
    advanced users to override the automatically computed ratio.  When the
    override is not provided the function applies a light‑weight empirical
    approximation:

    * altitude scaling is derived from a small lookup table sourced from
      published aviation neutron measurements and interpolated linearly; and
    * latitude dependence follows a smooth ``sin^1.5`` profile normalised to
      unity at 45° latitude, capturing the increased flux near the poles and
      the reduction at the geomagnetic equator.

    Parameters
    ----------
    alt_km:
        Installation altitude in kilometres.  Values below zero are clamped to
        sea level.
    latitude_deg:
        Geographic latitude in degrees.  The absolute value is used and clamped
        to the range ``[0°, 90°]``.
    flux_rel:
        Optional manual override.  When provided it is returned verbatim.
    """

    if flux_rel is not None:
        return flux_rel

    altitude_profile = [
        (0.0, 1.0),
        (1.0, 1.3),
        (2.0, 1.8),
        (5.0, 4.0),
        (8.0, 8.0),
        (10.0, 15.0),
        (12.0, 25.0),
    ]

    alt = max(float(alt_km), 0.0)
    alt_factor = altitude_profile[0][1]
    for (x0, y0), (x1, y1) in zip(altitude_profile, altitude_profile[1:]):
        if alt <= x1:
            if alt <= x0:
                alt_factor = y0
            else:
                span = x1 - x0
                if span <= 0:
                    alt_factor = y1
                else:
                    weight = (alt - x0) / span
                    alt_factor = y0 + weight * (y1 - y0)
            break
    else:
        x0, y0 = altitude_profile[-2]
        x1, y1 = altitude_profile[-1]
        slope = (y1 - y0) / (x1 - x0)
        alt_factor = y1 + slope * (alt - x1)

    lat = min(max(abs(float(latitude_deg)), 0.0), 90.0)
    sin_term = math.sin(math.radians(lat))
    raw_lat = 0.75 + 0.25 * (sin_term**1.5)
    ref_lat = 0.75 + 0.25 * (math.sin(math.radians(45.0)) ** 1.5)
    lat_factor = raw_lat / ref_lat

    return alt_factor * lat_factor


from qcrit_loader import qcrit_lookup


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
