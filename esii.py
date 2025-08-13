"""Environmental Sustainability Improvement Index (ESII).

This module provides a helper function to compute the ESII given reliability
improvements and carbon cost components.  The ESII is defined as the ratio of
failure rate improvement to the total carbon footprint associated with the
technique.
"""

from __future__ import annotations

def compute_esii(
    fit_base: float,
    fit_ecc: float,
    E_dyn_kWh: float,
    E_leak_kWh: float,
    CI: float,
    EC_embodied_kg: float,
) -> float:
    """Compute the Environmental Sustainability Improvement Index (ESII).

    Parameters
    ----------
    fit_base : float
        Failure rate in FIT (failures per 1e9 hours) for the baseline system.
    fit_ecc : float
        Failure rate in FIT when error correction is applied.
    E_dyn_kWh : float
        Dynamic energy consumption over the lifetime in kWh.
    E_leak_kWh : float
        Leakage energy consumption over the lifetime in kWh.
    CI : float
        Carbon intensity in kgCO2e per kWh.
    EC_embodied_kg : float
        Embodied carbon of the technique in kgCO2e.

    Returns
    -------
    float
        The ESII value which represents reliability improvement per kgCO2e.
    """
    if CI < 0 or E_dyn_kWh < 0 or E_leak_kWh < 0 or EC_embodied_kg < 0:
        raise ValueError("Energy and carbon terms must be non-negative")
    if fit_base < fit_ecc:
        raise ValueError("ECC must not worsen the FIT")

    dynamic = E_dyn_kWh * CI
    leakage = E_leak_kWh * CI
    total_carbon = dynamic + leakage + EC_embodied_kg
    if total_carbon <= 0:
        raise ValueError("Total carbon must be positive")

    reliability_gain = fit_base - fit_ecc
    return reliability_gain / total_carbon
