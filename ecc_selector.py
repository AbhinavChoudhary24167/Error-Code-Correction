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

import logging

import hashlib
import json
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


_PARETO_EPS = 1e-8


_log = logging.getLogger(__name__)
_logged_fallback = False
_logged_degenerate = False


def _pareto_front(
    records: Iterable[Mapping[str, float]], eps: float = _PARETO_EPS
) -> List[Dict[str, float]]:
    """Return the Pareto frontier of ``records`` using ε-dominance.

    The comparison operates on min–max normalised axes with a small epsilon to
    avoid floating point jitter.  The returned list is sorted by the ``code``
    field for stable output.
    """

    recs = list(records)
    if not recs:
        return []

    keys = ("FIT", "carbon_kg", "latency_ns")
    mins = {k: min(r[k] for r in recs) for k in keys}
    maxs = {k: max(r[k] for r in recs) for k in keys}

    def norm(k: str, v: float) -> float:
        span = maxs[k] - mins[k]
        if span <= 0:
            return 0.0
        return (v - mins[k]) / span

    frontier: List[Dict[str, float]] = []
    for rec in recs:
        dominated = False
        for other in recs:
            if other is rec:
                continue
            le = all(norm(k, other[k]) <= norm(k, rec[k]) + eps for k in keys)
            lt = any(norm(k, other[k]) < norm(k, rec[k]) - eps for k in keys)
            if le and lt:
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

    scenario = dict(kwargs)
    scenario.update({"mbu": mbu, "scrub_s": float(scrub_s)})
    scenario_hash = hashlib.sha1(
        json.dumps(scenario, sort_keys=True).encode()
    ).hexdigest()

    if not recs:
        norm_meta = {
            "method": "winsor",
            "p5": float("nan"),
            "p95": float("nan"),
            "N": 0,
            "scope": "feasible_set",
        }
        return {
            "best": None,
            "pareto": [],
            "normalization": norm_meta,
            "candidates": list(codes),
            "scenario_hash": scenario_hash,
        }

    # Normalise ESII across candidates; fall back deterministically if needed
    esii_vals = [r["ESII"] for r in recs]
    N = len(esii_vals)
    scores, p5, p95 = normalise_esii(esii_vals)
    method = "winsor"
    status = "ok"
    if N < 20 or math.isclose(p5, p95):
        global _logged_fallback
        if not _logged_fallback:
            _log.warning("NESII normalization fallback to min-max")
            _logged_fallback = True
        method = "minmax"
        p5 = min(esii_vals)
        p95 = max(esii_vals)
        span = p95 - p5
        if span <= 0:
            global _logged_degenerate
            if not _logged_degenerate:
                _log.warning("NESII degenerate scale; forcing score 50")
                _logged_degenerate = True
            scores = [50.0 for _ in esii_vals]
            status = "degenerate_scale"
        else:
            scores = [100.0 * (v - p5) / span for v in esii_vals]

    for rec, score in zip(recs, scores):
        rec["NESII"] = score
        rec["p5"] = p5
        rec["p95"] = p95
        rec["N_scale"] = N
        rec["scrub_s"] = float(scrub_s)

    basis = "system"
    lifetime_h = float(kwargs.get("lifetime_h", float("nan")))
    ci_source = kwargs.get("ci_source", "unspecified")

    norm_meta = {
        "method": method,
        "p5": p5,
        "p95": p95,
        "N": N,
        "scope": "feasible_set",
        "epsilon_on_normalized_axes": _PARETO_EPS,
        "basis": basis,
        "lifetime_h": lifetime_h,
        "ci_kg_per_kwh": float(kwargs["ci"]),
        "ci_source": ci_source,
    }
    if status != "ok":
        norm_meta["status"] = status

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

    return {
        "best": best,
        "pareto": pareto,
        "normalization": norm_meta,
        "candidates": list(codes),
        "scenario_hash": scenario_hash,
    }


__all__ = ["select", "_pareto_front"]

