import csv
import subprocess
import sys
from pathlib import Path


def test_surface_analysis(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[2] / "eccsim.py"
    cand = tmp_path / "cand.csv"
    pareto = tmp_path / "pareto.csv"
    cmd = [
        sys.executable,
        str(script),
        "select",
        "--codes",
        "sec-ded-64,sec-daec-64,taec-64",
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

    surface_csv = tmp_path / "surface.csv"
    surface_png = tmp_path / "surface.png"
    cmd = [
        sys.executable,
        str(script),
        "analyze",
        "surface",
        "--from-candidates",
        str(cand),
        "--out-csv",
        str(surface_csv),
        "--plot",
        str(surface_png),
    ]
    subprocess.run(cmd, check=True, text=True)

    assert surface_csv.exists()
    with open(pareto) as fh:
        pareto_rows = list(csv.DictReader(fh))
    with open(surface_csv) as fh:
        surface_rows = list(csv.DictReader(fh))

    surface_codes = {r["code"] for r in surface_rows}
    pareto_codes = {r["code"] for r in pareto_rows}
    assert pareto_codes.issubset(surface_codes)

    frontier_codes = {r["code"] for r in surface_rows if r.get("frontier", "").lower() in ("true", "1")}
    assert frontier_codes == pareto_codes

    for r in surface_rows:
        nesii = float(r["NESII"])
        assert 0.0 <= nesii <= 100.0

    hashes = {r["scenario_hash"] for r in surface_rows}
    assert len(hashes) == 1 and list(hashes)[0]
