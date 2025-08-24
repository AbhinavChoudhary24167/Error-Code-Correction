import csv
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

def run_target(tmp_path, target):
    feasible = tmp_path / "feasible.csv"
    choice = tmp_path / "choice.json"
    cmd = [
        sys.executable,
        str(REPO / "eccsim.py"),
        "target",
        "--codes",
        "sec-ded-64,sec-daec-64,taec-64",
        "--node",
        "14",
        "--vdd",
        "0.8",
        "--temp",
        "75",
        "--mbu",
        "moderate",
        "--scrub-s",
        "10",
        "--capacity-gib",
        "8",
        "--ci",
        "0.55",
        "--bitcell-um2",
        "0.040",
        "--target-type",
        "uwer",
        "--target",
        str(target),
        "--feasible",
        str(feasible),
        "--choice",
        str(choice),
    ]
    subprocess.run(cmd, check=True, cwd=tmp_path)
    feas = list(csv.DictReader(open(feasible)))
    choice_data = json.load(open(choice))
    return feas, choice_data


def test_feasible_set_shrinks(tmp_path):
    feas1, _ = run_target(tmp_path, 9.5e-7)
    feas2, _ = run_target(tmp_path, 9.0e-7)
    set1 = {f["code"] for f in feas1}
    set2 = {f["code"] for f in feas2}
    assert set2 <= set1


def test_choice_is_min_carbon(tmp_path):
    feas, choice = run_target(tmp_path, 9.5e-7)
    carbons = {f["code"]: float(f["carbon_kg"]) for f in feas}
    min_code = min(carbons, key=lambda k: carbons[k])
    assert choice["choice"]["code"] == min_code
    assert float(choice["choice"]["carbon_kg"]) == min(carbons.values())
