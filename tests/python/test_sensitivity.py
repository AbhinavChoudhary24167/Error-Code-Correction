import json
import subprocess
import sys
from pathlib import Path


def _write_scenario(path: Path) -> Path:
    scenario = {
        "codes": ["sec-ded-64", "sec-daec-64", "taec-64"],
        "node": 14,
        "vdd": 0.8,
        "temp": 75.0,
        "scrub_s": 10.0,
        "capacity_gib": 8.0,
        "ci": 0.55,
        "bitcell_um2": 0.040,
    }
    scen_path = path / "scenario.json"
    scen_path.write_text(json.dumps(scenario))
    return scen_path


def _run(path: Path, scenario: Path, factor: str, grid: list[float], out: Path) -> dict:
    script = Path(__file__).resolve().parents[2] / "eccsim.py"
    cmd = [
        sys.executable,
        str(script),
        "analyze",
        "sensitivity",
        "--factor",
        factor,
        "--grid",
        ",".join(str(x) for x in grid),
        "--from",
        str(scenario),
        "--out",
        str(out),
    ]
    subprocess.run(cmd, check=True, text=True)
    return json.loads(out.read_text())


def test_sensitivity_deterministic(tmp_path: Path) -> None:
    scen = _write_scenario(tmp_path)
    out1 = tmp_path / "sens1.json"
    out2 = tmp_path / "sens2.json"
    data1 = _run(tmp_path, scen, "vdd", [0.72, 0.76], out1)
    data2 = _run(tmp_path, scen, "vdd", [0.72, 0.76], out2)
    assert data1 == data2


def test_feasible_set_monotone(tmp_path: Path) -> None:
    scen = _write_scenario(tmp_path)
    out = tmp_path / "sens_fit.json"
    grid = [1200.0, 1000.0, 900.0]
    data = _run(tmp_path, scen, "fit_max", grid, out)
    counts = [len(data["feasible"][str(g)]) for g in grid]
    assert counts[0] >= counts[1] >= counts[2]


def test_change_points_detected(tmp_path: Path) -> None:
    scen = _write_scenario(tmp_path)
    out = tmp_path / "sens_change.json"
    grid = [2000.0, 1000.0, 800.0]
    data = _run(tmp_path, scen, "fit_max", grid, out)
    cps = data["change_points"]
    assert cps and cps[0]["value"] == 1000.0
