"""Multi-objective ECC selector.

The :func:`select` helper evaluates a set of ECC codes under a common
scenario and returns a recommendation together with the Pareto optimal
frontier.  The frontier is determined with respect to ``FIT`` (failures in
time), total ``carbon_kg`` and ``latency_ns`` – all of which are minimised.

Only a very small subset of ECC codes is modelled.  The implementation is
light‑weight and trades accuracy for clarity; it is sufficient for unit tests
and for demonstrating the selection flow used by :mod:`eccsim`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping

import math

from carbon import embodied_kgco2e, operational_kgco2e, default_alpha
from energy_model import estimate_energy
from esii import ESIIInputs, compute_esii, normalise_esii
from fit import (
    compute_fit_pre,
    compute_fit_post,
    ecc_coverage_factory,
    fit_system,
)
from mbu import pmf_adjacent
from qcrit_loader import qcrit_lookup
from ser_model import HazuchaParams, ser_hazucha, flux_from_location


# ---------------------------------------------------------------------------
# Simplified technology characterisation for supported ECC codes.  The values
# are deliberately approximate – they merely provide ordering for the unit
# tests and examples.


@dataclass(frozen=True)
class _CodeInfo:
    family: str
    parity_bits: int
    latency_ns: float
    area_logic_mm2: float
    notes: str = ""


_CODE_DB: Dict[str, _CodeInfo] = {
    "sec-ded-64": _CodeInfo("SEC-DED", parity_bits=8, latency_ns=1.0, area_logic_mm2=1.0),
    "sec-daec-64": _CodeInfo(
        "SEC-DAEC", parity_bits=9, latency_ns=1.3, area_logic_mm2=1.2
    ),
    "taec-64": _CodeInfo("TAEC", parity_bits=11, latency_ns=1.6, area_logic_mm2=1.5),
}


# ---------------------------------------------------------------------------
# Pareto helpers


def _dominates(a: Mapping[str, float], b: Mapping[str, float]) -> bool:
    """Return ``True`` if record ``a`` dominates ``b``.

    Dominance is with respect to the ``FIT``, ``carbon_kg`` and ``latency_ns``
    keys, all of which are minimised.
    """

    keys = ("FIT", "carbon_kg", "latency_ns")
    le = all(a[k] <= b[k] for k in keys)
    lt = any(a[k] < b[k] for k in keys)
    return le and lt


def _pareto_front(records: Iterable[Mapping[str, float]]) -> List[Dict[str, float]]:
    """Return the Pareto frontier of ``records``.

    The returned list is sorted by the ``code`` field for stable output.
    """

    recs = list(records)
    frontier: List[Dict[str, float]] = []
    for rec in recs:
        dominated = False
        for other in recs:
            if other is rec:
                continue
            if _dominates(other, rec):
                dominated = True
                break
        if not dominated:
            frontier.append(dict(rec))
    frontier.sort(key=lambda r: r["code"])
    return frontier


# ---------------------------------------------------------------------------
# Selection logic


def _compute_metrics(
    code: str,
    *,
    node: int,
    vdd: float,
    temp: float,
    ci: float,
    capacity_gib: float,
    bitcell_um2: float,
    mbu: str,
    scrub_s: float,
) -> Dict[str, float | str]:
    """Return metric record for ``code`` under the specified scenario."""

    info = _CODE_DB[code]

    # --- Reliability -----------------------------------------------------
    try:
        qcrit_fC = qcrit_lookup("sram6t", node, vdd, temp, 50)
        area_um2 = bitcell_um2
    except Exception:  # pragma: no cover - defensive fallback
        qcrit_fC = 0.3
        area_um2 = bitcell_um2

    flux = flux_from_location(0.0, 45.0, None)
    hp = HazuchaParams(Qs_fC=0.05, flux_rel=flux, area_um2=area_um2)
    fit_bit = ser_hazucha(qcrit_fC, hp)

    mbu_dist = pmf_adjacent(mbu, word_bits=64, bitline_bits=64)
    severity_scale = {"light": 0.0, "moderate": 1.0, "heavy": 5.0}.get(mbu, 1.0)
    # Scale probabilities to FIT rates; the multiplier ensures MBUs have a
    # noticeable impact on the final metric.
    mbu_rates = {
        k: {kind: fit_bit * 64 * k * p * severity_scale for kind, p in probs.items()}
        for k, probs in mbu_dist.items()
    }

    fit_pre = compute_fit_pre(64, fit_bit, mbu_rates)
    ecc_cov = ecc_coverage_factory(info.family)
    fit_post = compute_fit_post(64, fit_bit, mbu_rates, ecc_cov, scrub_s)

    fit_base_sys = fit_system(capacity_gib, fit_pre.nominal)
    fit_post_sys = fit_system(capacity_gib, fit_post.nominal)

    # --- Energy & Carbon -------------------------------------------------
    words = capacity_gib * (2**30 * 8) / 64
    e_per_read = estimate_energy(info.parity_bits, 0, node_nm=node, vdd=vdd)
    e_dyn = e_per_read * words  # joules for one scrub sweep
    e_leak = 0.0

    alpha_logic, alpha_macro = default_alpha(node)
    area_macro_mm2 = info.parity_bits * words * bitcell_um2 / 1e6
    embodied = embodied_kgco2e(
        info.area_logic_mm2, area_macro_mm2, alpha_logic, alpha_macro
    )
    operational = operational_kgco2e(e_dyn / 3_600_000.0, e_leak / 3_600_000.0, ci)
    carbon_total = embodied + operational

    esii_inp = ESIIInputs(
        fit_base=fit_base_sys,
        fit_ecc=fit_post_sys,
        e_dyn=e_dyn,
        e_leak=e_leak,
        ci_kgco2e_per_kwh=ci,
        embodied_kgco2e=embodied,
        basis="system",
    )
    esii = compute_esii(esii_inp)["ESII"]

    return {
        "code": code,
        "FIT": fit_post_sys,
        "ESII": esii,
        "carbon_kg": carbon_total,
        "E_dyn_kWh": e_dyn / 3_600_000.0,
        "E_leak_kWh": e_leak / 3_600_000.0,
        "latency_ns": info.latency_ns,
        "area_logic_mm2": info.area_logic_mm2,
        "area_macro_mm2": area_macro_mm2,
        "notes": info.notes,
    }


def select(
    codes: Iterable[str],
    *,
    weights: Mapping[str, float] | None = None,
    constraints: Mapping[str, float | None] | None = None,
    backend: str = "hazucha",
    mbu: str = "moderate",
    scrub_s: float = 10.0,
    **kwargs,
) -> Dict[str, object]:
    """Return a recommended ECC and the Pareto frontier.

    Parameters
    ----------
    codes:
        Iterable of code identifiers such as ``"sec-ded-64"``.
    weights:
        Mapping specifying ``reliability``, ``carbon`` and ``latency``
        weights used for scalarisation.  Defaults to ``{1.0, 1.0, 0.25}``.
    constraints:
        Optional ``{"latency_ns_max": ..., "carbon_kg_max": ...}`` limits.
    backend:
        Reliability backend – currently only ``"hazucha"`` is supported.
    mbu:
        Multi-bit upset severity preset.
    scrub_s:
        Scrub interval in seconds.
    **kwargs:
        Additional parameters forwarded to the metric computation such as
        ``node``, ``vdd`` and ``temp``.
    """

    if backend != "hazucha":  # pragma: no cover - defensive programming
        raise ValueError("Only 'hazucha' backend supported")

    weights = dict({"reliability": 1.0, "carbon": 1.0, "latency": 0.25}, **(weights or {}))
    constraints = dict({"latency_ns_max": None, "carbon_kg_max": None}, **(constraints or {}))

    required = {"node", "vdd", "temp", "capacity_gib", "ci", "bitcell_um2"}
    missing = required - kwargs.keys()
    if missing:
        raise ValueError(f"Missing required parameters: {sorted(missing)}")

    # Compute metrics for each candidate and apply constraints
    recs = []
    for code in codes:
        if code not in _CODE_DB:
            raise KeyError(code)
        rec = _compute_metrics(
            code,
            node=int(kwargs["node"]),
            vdd=float(kwargs["vdd"]),
            temp=float(kwargs["temp"]),
            ci=float(kwargs["ci"]),
            capacity_gib=float(kwargs["capacity_gib"]),
            bitcell_um2=float(kwargs["bitcell_um2"]),
            mbu=mbu,
            scrub_s=float(scrub_s),
        )

        lat_max = constraints.get("latency_ns_max")
        if lat_max is not None and rec["latency_ns"] > lat_max:
            continue
        carbon_max = constraints.get("carbon_kg_max")
        if carbon_max is not None and rec["carbon_kg"] > carbon_max:
            continue

        recs.append(rec)

    if not recs:
        return {"best": None, "pareto": [], "nesii_p5": float("nan"), "nesii_p95": float("nan")}

    # Normalise ESII across candidates
    nesii_scores, p5, p95 = normalise_esii([r["ESII"] for r in recs])
    for rec, score in zip(recs, nesii_scores):
        rec["NESII"] = score

    # Determine Pareto frontier
    pareto = _pareto_front(recs)

    # Scalarise for single recommendation using min–max normalisation
    mins = {k: min(r[k] for r in recs) for k in ("FIT", "carbon_kg", "latency_ns")}
    maxs = {k: max(r[k] for r in recs) for k in ("FIT", "carbon_kg", "latency_ns")}

    def norm(key: str, value: float) -> float:
        span = maxs[key] - mins[key]
        if span <= 0:
            return 0.0
        return (value - mins[key]) / span

    best = None
    best_score = math.inf
    for rec in recs:
        score = (
            weights["reliability"] * norm("FIT", rec["FIT"])
            + weights["carbon"] * norm("carbon_kg", rec["carbon_kg"])
            + weights["latency"] * norm("latency_ns", rec["latency_ns"])
        )
        if score < best_score:
            best_score = score
            best = rec

    return {"best": best, "pareto": pareto, "nesii_p5": p5, "nesii_p95": p95}


__all__ = ["select", "_pareto_front"]

