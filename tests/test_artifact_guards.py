import csv
from pathlib import Path

from ecc_selector import select


def _default_params():
    return {
        "node": 14,
        "vdd": 0.8,
        "temp": 75.0,
        "capacity_gib": 8.0,
        "ci": 0.55,
        "bitcell_um2": 0.040,
    }


def _emit_pareto_csv(pareto, path: Path) -> None:
    """Write Pareto frontier records to ``path`` in CSV format."""
    fieldnames = [
        "code",
        "scrub_s",
        "FIT",
        "carbon_kg",
        "latency_ns",
        "ESII",
        "NESII",
        "p5",
        "p95",
        "N_scale",
        "area_logic_mm2",
        "area_macro_mm2",
        "E_dyn_kWh",
        "E_leak_kWh",
        "E_scrub_kWh",
        "notes",
    ]
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for rec in pareto:
            writer.writerow(rec)


def test_artifact_guards(tmp_path):
    codes = ["sec-ded-64", "sec-daec-64", "taec-64"]
    params = _default_params()

    res1 = select(codes, **params)
    res2 = select(codes, **params)

    # (c) identical outputs for the same scenario hash
    assert res1["scenario_hash"] == res2["scenario_hash"]
    assert res1["pareto"] == res2["pareto"]
    assert res1["best"] == res2["best"]

    # (d) hypervolume and spacing present
    quality = res1["quality"]
    assert "hypervolume" in quality and "spacing" in quality

    # (e) scrub energy is explicitly included
    assert res1["includes_scrub_energy"] is True

    # Emit Pareto frontier to CSV to apply file-level guards
    pareto_csv = tmp_path / "pareto.csv"
    _emit_pareto_csv(res1["pareto"], pareto_csv)

    with pareto_csv.open() as fh:
        rows = list(csv.DictReader(fh))

    # (a) no epsilon-dominated point present
    eps = 1e-9
    metrics = ["FIT", "carbon_kg", "latency_ns"]
    for i, a in enumerate(rows):
        for j, b in enumerate(rows):
            if i == j:
                continue
            if all(float(b[m]) <= float(a[m]) + eps for m in metrics) and any(
                float(b[m]) < float(a[m]) - eps for m in metrics
            ):
                raise AssertionError("epsilon dominated point found in pareto.csv")

    # (b) NESII within [0,100] and normalisation stats present
    for row in rows:
        nesii = float(row["NESII"])
        assert 0.0 <= nesii <= 100.0
        for key in ("p5", "p95", "N_scale"):
            assert row[key] != ""
