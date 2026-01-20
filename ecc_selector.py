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
from typing import Dict, Iterable, List, Mapping, Tuple

import logging

import hashlib
import json
import math

from carbon import embodied_kgco2e, operational_kgco2e, default_alpha
from energy_model import scrub_energy_kwh
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
from gs import GSInputs, compute_gs
from analysis.knee import max_perp_norm
from analysis.hv import hypervolume, schott_spacing


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
    word_bits: int = 64
    notes: str = ""


_CODE_DB: Dict[str, _CodeInfo] = {
    "sec-ded-64": _CodeInfo("SEC-DED", parity_bits=8, latency_ns=1.0, area_logic_mm2=1.0),
    "sec-daec-64": _CodeInfo(
        "SEC-DAEC", parity_bits=9, latency_ns=1.3, area_logic_mm2=1.2
    ),
    "taec-64": _CodeInfo("TAEC", parity_bits=11, latency_ns=1.6, area_logic_mm2=1.5),
    "bch-63": _CodeInfo(
        "BCH", parity_bits=12, latency_ns=2.4, area_logic_mm2=2.1, notes="BCH(63,51,2)"
    ),
    "polar-64-32": _CodeInfo(
        "POLAR-64-32",
        parity_bits=32,
        latency_ns=2.2,
        area_logic_mm2=2.0,
        word_bits=64,
        notes="Polar (N=64, K=32) SC decoder",
    ),
    "polar-64-48": _CodeInfo(
        "POLAR-64-48",
        parity_bits=16,
        latency_ns=2.0,
        area_logic_mm2=1.8,
        word_bits=64,
        notes="Polar (N=64, K=48) SC decoder",
    ),
    "polar-128-96": _CodeInfo(
        "POLAR-128-96",
        parity_bits=32,
        latency_ns=2.6,
        area_logic_mm2=2.4,
        word_bits=128,
        notes="Polar (N=128, K=96) SC decoder",
    ),
}


# ---------------------------------------------------------------------------
# Pareto helpers


_PARETO_EPS = 1e-8


_log = logging.getLogger(__name__)
_logged_fallback = False
_logged_degenerate = False
_carbon_cap_warned = False
_degenerate_warned = {"carbon": False, "latency": False}


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


def _nsga2_sort(
    recs: List[Dict[str, float]],
) -> Tuple[List[List[int]], Dict[int, float], Dict[str, float], Dict[str, float], Dict[int, Dict[str, float]]]:
    """Return NSGA-II fronts and crowding distances on normalised axes."""

    if not recs:
        return [], {}, {}, {}, {}

    keys = ("FIT", "carbon_kg", "latency_ns")

    mins = {k: min(r[k] for r in recs) for k in keys}
    maxs = {k: max(r[k] for r in recs) for k in keys}

    def norm(idx: int, key: str) -> float:
        span = maxs[key] - mins[key]
        if span <= 0:
            return 0.0
        return (recs[idx][key] - mins[key]) / span

    # Non-dominated sorting
    S: List[List[int]] = [[] for _ in recs]
    n = [0 for _ in recs]
    fronts: List[List[int]] = [[]]

    def dominates(p: Dict[str, float], q: Dict[str, float]) -> bool:
        return all(p[k] <= q[k] for k in keys) and any(p[k] < q[k] for k in keys)

    for i, p in enumerate(recs):
        for j, q in enumerate(recs):
            if i == j:
                continue
            if dominates(p, q):
                S[i].append(j)
            elif dominates(q, p):
                n[i] += 1
        if n[i] == 0:
            fronts[0].append(i)

    i = 0
    while fronts[i]:
        next_front: List[int] = []
        for p_idx in fronts[i]:
            for q_idx in S[p_idx]:
                n[q_idx] -= 1
                if n[q_idx] == 0:
                    next_front.append(q_idx)
        i += 1
        fronts.append(next_front)

    # Crowding distance on normalised axes
    crowd = {idx: 0.0 for idx in range(len(recs))}
    norm_vals: Dict[int, Dict[str, float]] = {
        i: {k: norm(i, k) for k in keys} for i in range(len(recs))
    }
    for front in fronts:
        if not front:
            continue
        for key in keys:
            sorted_f = sorted(front, key=lambda idx: norm_vals[idx][key])
            crowd[sorted_f[0]] = crowd[sorted_f[-1]] = float("inf")
            for k in range(1, len(sorted_f) - 1):
                prev_val = norm_vals[sorted_f[k - 1]][key]
                next_val = norm_vals[sorted_f[k + 1]][key]
                crowd[sorted_f[k]] += next_val - prev_val
    return fronts, crowd, mins, maxs, norm_vals


# ---------------------------------------------------------------------------
# GS helpers


def _percentile(values: List[float], pct: float) -> float:
    vs = sorted(values)
    if not vs:
        return 0.0
    k = (len(vs) - 1) * pct / 100.0
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return vs[int(k)]
    return vs[f] * (c - k) + vs[c] * (k - f)


def _annotate_gs(recs: List[Dict[str, float]], weights: Tuple[float, float, float]) -> None:
    global _carbon_cap_warned
    carbon_vals = [r["carbon_kg"] for r in recs]
    if len(carbon_vals) < 5:
        cap = max(carbon_vals)
        if not _carbon_cap_warned:
            _log.warning("carbon cap fallback to max for N<5")
            _carbon_cap_warned = True
    else:
        cap = _percentile(carbon_vals, 95)
    carbon_clipped = [min(v, cap) for v in carbon_vals]
    c_span = max(carbon_clipped) - min(carbon_clipped)
    if c_span <= max(1.0, cap) * 1e-9 and not _degenerate_warned["carbon"]:
        _log.warning("carbon values nearly identical; treating as neutral")
        _degenerate_warned["carbon"] = True
        carbon_clipped = [0.0 for _ in carbon_clipped]

    lat_vals = [r["latency_ns"] for r in recs]
    l_span = max(lat_vals) - min(lat_vals)
    if l_span <= max(1.0, max(lat_vals)) * 1e-9 and not _degenerate_warned["latency"]:
        _log.warning("latency values nearly identical; treating as neutral")
        _degenerate_warned["latency"] = True
        lat_vals = [r.get("latency_base_ns", 0.0) for r in recs]

    for rec, c_val, l_val in zip(recs, carbon_clipped, lat_vals):
        inp = GSInputs(
            fit_base=rec["fit_base"],
            fit_ecc=rec["FIT"],
            carbon_kg=c_val,
            latency_ns=l_val,
            latency_base_ns=rec.get("latency_base_ns", 0.0),
        )
        gs_res = compute_gs(inp, weights=weights)
        rec["GS"] = gs_res["GS"]
        rec["Sr"] = gs_res["Sr"]
        rec["Sc"] = gs_res["Sc"]
        rec["Sl"] = gs_res["Sl"]


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
    alt_km: float,
    latitude_deg: float,
    flux_rel: float | None,
    mbu: str,
    scrub_s: float,
    lifetime_h: float = float("nan"),
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

    flux = flux_from_location(alt_km, latitude_deg, flux_rel)
    hp = HazuchaParams(Qs_fC=0.05, flux_rel=flux, area_um2=area_um2)
    fit_bit = ser_hazucha(qcrit_fC, hp)

    word_bits = info.word_bits
    mbu_dist = pmf_adjacent(mbu, word_bits=word_bits, bitline_bits=word_bits)
    severity_scale = {"light": 0.0, "moderate": 1.0, "heavy": 5.0}.get(mbu, 1.0)
    # Scale probabilities to FIT rates; the multiplier ensures MBUs have a
    # noticeable impact on the final metric.
    mbu_rates = {
        k: {kind: fit_bit * word_bits * k * p * severity_scale for kind, p in probs.items()}
        for k, probs in mbu_dist.items()
    }

    fit_pre = compute_fit_pre(word_bits, fit_bit, mbu_rates)
    ecc_cov = ecc_coverage_factory(info.family, word_bits=word_bits)
    fit_post = compute_fit_post(word_bits, fit_bit, mbu_rates, ecc_cov, scrub_s)

    fit_base_sys = fit_system(capacity_gib, fit_pre.nominal)
    fit_post_sys = fit_system(capacity_gib, fit_post.nominal)

    # --- Energy & Carbon -------------------------------------------------
    words = capacity_gib * (2**30 * 8) / word_bits
    e_scrub_kwh = scrub_energy_kwh(
        info.parity_bits,
        capacity_gib,
        lifetime_h,
        scrub_s,
        node_nm=node,
        vdd=vdd,
        word_bits=word_bits,
    )
    e_scrub = e_scrub_kwh * 3_600_000.0
    e_dyn = 0.0
    e_leak = 0.0

    try:
        alpha_logic, alpha_macro = default_alpha(node)
    except ValueError as exc:
        raise ValueError(f"{exc}. Unable to estimate embodied carbon.") from exc
    area_macro_mm2 = info.parity_bits * words * bitcell_um2 / 1e6
    embodied = embodied_kgco2e(
        info.area_logic_mm2, area_macro_mm2, alpha_logic, alpha_macro
    )
    operational = operational_kgco2e(
        e_dyn / 3_600_000.0, e_leak / 3_600_000.0, ci, e_scrub_kwh
    )
    carbon_total = embodied + operational

    esii_inp = ESIIInputs(
        fit_base=fit_base_sys,
        fit_ecc=fit_post_sys,
        e_dyn=e_dyn,
        e_leak=e_leak,
        e_scrub=e_scrub,
        ci_kgco2e_per_kwh=ci,
        embodied_kgco2e=embodied,
        basis="system",
    )
    esii = compute_esii(esii_inp)["ESII"]

    return {
        "code": code,
        "FIT": fit_post_sys,
        "fit_base": fit_base_sys,
        "ESII": esii,
        "carbon_kg": carbon_total,
        "E_dyn_kWh": e_dyn / 3_600_000.0,
        "E_leak_kWh": e_leak / 3_600_000.0,
        "E_scrub_kWh": e_scrub_kwh,
        "latency_ns": info.latency_ns,
        "latency_base_ns": 0.0,
        "area_logic_mm2": info.area_logic_mm2,
        "area_macro_mm2": area_macro_mm2,
        "notes": info.notes,
        "includes_scrub_energy": True,
        "fit_bit": fit_bit,
        "fit_word_post": fit_post.nominal,
        "flux_rel": flux,
    }


def select(
    codes: Iterable[str],
    *,
    weights: Mapping[str, float] | None = None,
    constraints: Mapping[str, float | None] | None = None,
    backend: str = "hazucha",
    mbu: str = "moderate",
    scrub_s: float = 10.0,
    alt_km: float = 0.0,
    latitude_deg: float = 45.0,
    flux_rel: float | None = None,
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
        ``node``, ``vdd`` and ``temp``.  Location specific parameters
        (``alt_km``, ``latitude_deg`` and ``flux_rel``) are exposed explicitly
        to allow scenarios to model installation sites.
    """

    if backend != "hazucha":  # pragma: no cover - defensive programming
        raise ValueError("Only 'hazucha' backend supported")

    # ``weights`` are retained for backwards compatibility but ignored by the
    # NSGA-II based recommendation logic.  Supplying them no longer influences
    # the outcome but allows existing callers to remain unchanged.
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
            alt_km=float(alt_km),
            latitude_deg=float(latitude_deg),
            flux_rel=float(flux_rel) if flux_rel is not None else None,
            mbu=mbu,
            scrub_s=float(scrub_s),
            lifetime_h=float(kwargs.get("lifetime_h", float("nan"))),
        )

        violations = []
        lat_max = constraints.get("latency_ns_max")
        if lat_max is not None and rec["latency_ns"] > lat_max:
            violations.append("latency_ns_max")
        carbon_max = constraints.get("carbon_kg_max")
        if carbon_max is not None and rec["carbon_kg"] > carbon_max:
            violations.append("carbon_kg_max")
        if violations:
            continue
        rec["violations"] = violations

        recs.append(rec)

    scenario = dict(kwargs)
    scenario.update(
        {
            "mbu": mbu,
            "scrub_s": float(scrub_s),
            "alt_km": float(alt_km),
            "latitude_deg": float(latitude_deg),
            "flux_rel": float(flux_rel) if flux_rel is not None else None,
        }
    )
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
            "candidate_records": [],
            "scenario_hash": scenario_hash,
        }

    _annotate_gs(recs, (0.6, 0.3, 0.1))

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

    # NSGA-II ranking
    fronts, crowd, mins, maxs, norm_vals = _nsga2_sort(recs)
    front_rank = {}
    for rank, f in enumerate(fronts):
        for idx in f:
            front_rank[idx] = rank
    for idx, rec in enumerate(recs):
        rec["front_rank"] = front_rank.get(idx, math.inf)
        rec["crowding"] = crowd.get(idx, 0.0)

    pareto_enum = _pareto_front(recs)
    f1 = [recs[i] for i in fronts[0]] if fronts else []
    f1.sort(key=lambda r: r["code"])
    evo_miss = {r["code"] for r in pareto_enum} != {r["code"] for r in f1}

    # Decision rule ------------------------------------------------------
    fit_max = constraints.get("fit_max")
    lat_max = constraints.get("latency_ns_max")
    carbon_max = constraints.get("carbon_kg_max")

    decision_mode = "knee"
    decision_params = {
        "fit_max": fit_max,
        "latency_max": lat_max,
        "carbon_max": carbon_max,
    }
    knee_index: int | None = None
    knee_distance: float | None = None

    feasible = [
        r
        for r in recs
        if (fit_max is None or r["FIT"] <= fit_max)
        and (lat_max is None or r["latency_ns"] <= lat_max)
    ]

    if fit_max is not None or lat_max is not None:
        decision_mode = "epsilon-constraint"
        if feasible:
            best = min(feasible, key=lambda r: (r["carbon_kg"], -r["NESII"]))
        else:
            best = min(recs, key=lambda r: (r["carbon_kg"], -r["NESII"]))
    else:
        if fronts and fronts[0]:
            front_records = [recs[i] for i in fronts[0]]
            k_idx, knee_distance = max_perp_norm(front_records)
            best = front_records[k_idx]
            knee_index = f1.index(best)
            nesii_best = max(f1, key=lambda r: r["NESII"]) if f1 else best
            if nesii_best["NESII"] > best["NESII"]:
                best = nesii_best
        else:
            best = recs[0]

    # Frontier quality metrics
    f1_pts = [
        (
            norm_vals[i]["FIT"],
            norm_vals[i]["carbon_kg"],
            norm_vals[i]["latency_ns"],
        )
        for i in fronts[0]
    ] if fronts else []
    hv = hypervolume(f1_pts)
    spacing = schott_spacing(f1_pts)

    cand_hash = hashlib.sha1(",".join(sorted(codes)).encode()).hexdigest()
    seed = int(
        hashlib.sha1((scenario_hash + cand_hash).encode()).hexdigest(), 16
    ) & 0xFFFFFFFF

    nsga_meta = {
        "pop": 64,
        "gens": 64,
        "pc": 0.9,
        "pm": 0.1,
        "seed": seed,
        "deb_constraint_domination": True,
        "crowding_bounds": {"mins": mins, "maxs": maxs},
        "constraints_active": [k for k, v in constraints.items() if v is not None],
        "evolutionary_frontier_miss": evo_miss,
    }

    decision_meta: Dict[str, object] = {"mode": decision_mode, "params": decision_params}
    if knee_index is not None and knee_distance is not None:
        decision_meta.update(
            {
                "knee_index": knee_index,
                "knee_distance": knee_distance,
                "knee_method": "max-perp-normalized",
            }
        )

    quality = {"hypervolume": hv, "spacing": spacing, "ref_point_norm": [1.0, 1.0, 1.0]}

    return {
        "best": best,
        "pareto": f1,
        "normalization": norm_meta,
        "candidates": list(codes),
        "candidate_records": recs,
        "scenario_hash": scenario_hash,
        "includes_scrub_energy": True,
        "quality": quality,
        "nsga2": nsga_meta,
        "decision": decision_meta,
    }


__all__ = ["select", "_pareto_front", "_nsga2_sort"]
