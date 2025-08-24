import csv
import json
import subprocess
import sys
from pathlib import Path


def test_emit_candidates(tmp_path):
    script = Path(__file__).resolve().parents[2] / "eccsim.py"
    cand = tmp_path / "cand.csv"
    pareto = tmp_path / "pareto.csv"
    cmd = [
        sys.executable,
        str(script),
        "select",
        "--codes",
        "sec-ded-64,sec-daec-64,taec-64",
        "--constraints",
        "latency_ns_max=1.5",
        "--node",
        "14",
        "--vdd",
        "0.8",
        "--temp",
        "75",
        "--scrub-s",
        "10",
        "--capacity-gib",
        "8",
        "--ci",
        "0.55",
        "--bitcell-um2",
        "0.040",
        "--emit-candidates",
        str(cand),
        "--report",
        str(pareto),
    ]
    subprocess.run(cmd, check=True, text=True)
    assert cand.exists()
    assert pareto.exists()

    with cand.open() as fh:
        cand_rows = list(csv.DictReader(fh))
    with pareto.open() as fh:
        pareto_rows = list(csv.DictReader(fh))

    for row in cand_rows:
        assert float(row["latency_ns"]) <= 1.5 + 1e-9
        assert json.loads(row["violations"]) == []

    cand_codes = {r["code"] for r in cand_rows}
    pareto_codes = {r["code"] for r in pareto_rows}
    assert pareto_codes.issubset(cand_codes)

    cand_map = {r["code"]: r for r in cand_rows}
    for p in pareto_rows:
        c = cand_map[p["code"]]
        for key in ("FIT", "carbon_kg", "latency_ns"):
            assert abs(float(c[key]) - float(p[key])) <= 1e-8 + 1e-12
