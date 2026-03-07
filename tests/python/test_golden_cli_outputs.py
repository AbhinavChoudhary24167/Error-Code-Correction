import csv
import json
import math
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "golden"
RUNTIME = FIXTURES / "runtime"


def _run(cmd, cwd: Path | None = None):
    return subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
        cwd=cwd or REPO,
    )


def _csv_rows(path: Path):
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def _json_obj(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _clean(paths):
    for p in paths:
        try:
            p.unlink()
        except FileNotFoundError:
            pass




def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _assert_close_obj(actual, expected, *, rel_tol=1e-12, abs_tol=1e-15):
    if isinstance(expected, dict):
        assert isinstance(actual, dict)
        assert set(actual.keys()) == set(expected.keys())
        for key in expected:
            _assert_close_obj(actual[key], expected[key], rel_tol=rel_tol, abs_tol=abs_tol)
        return

    if isinstance(expected, list):
        assert isinstance(actual, list)
        assert len(actual) == len(expected)
        for got, exp in zip(actual, expected):
            _assert_close_obj(got, exp, rel_tol=rel_tol, abs_tol=abs_tol)
        return

    if isinstance(expected, float):
        assert math.isclose(float(actual), float(expected), rel_tol=rel_tol, abs_tol=abs_tol)
        return

    exp_num = _as_float(expected)
    got_num = _as_float(actual)
    if exp_num is not None and got_num is not None:
        assert math.isclose(got_num, exp_num, rel_tol=rel_tol, abs_tol=abs_tol)
        return

    assert actual == expected


def test_golden_reliability_report_json():
    cmd = [
        sys.executable,
        str(REPO / "eccsim.py"),
        "reliability",
        "report",
        "--qcrit",
        "1.2",
        "--qs",
        "0.25",
        "--area",
        "0.08",
        "--alt-km",
        "2.0",
        "--latitude",
        "60.0",
        "--scrub-interval",
        "3600",
        "--capacity-gib",
        "1.0",
        "--basis",
        "per_gib",
        "--mbu",
        "none",
        "--node-nm",
        "14",
        "--vdd",
        "0.8",
        "--tempC",
        "75",
        "--json",
    ]
    res = _run(cmd)
    _assert_close_obj(json.loads(res.stdout), _json_obj(FIXTURES / "reliability_report.json"))


def test_golden_select_outputs():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    cand = RUNTIME / "select_candidates.actual.csv"
    pareto = RUNTIME / "select_pareto.actual.csv"
    _clean([cand, pareto])

    cmd = [
        sys.executable,
        str(REPO / "eccsim.py"),
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
    res = _run(cmd)
    assert res.stdout == (FIXTURES / "select.stdout.txt").read_text(encoding="utf-8")
    _assert_close_obj(_csv_rows(cand), _csv_rows(FIXTURES / "select_candidates.csv"))
    _assert_close_obj(_csv_rows(pareto), _csv_rows(FIXTURES / "select_pareto.csv"))


def test_golden_target_outputs():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    feasible = RUNTIME / "target_feasible.actual.csv"
    choice = RUNTIME / "target_choice.actual.json"
    _clean([feasible, choice])

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
        "9.5e-7",
        "--feasible",
        str(feasible),
        "--choice",
        str(choice),
    ]
    res = _run(cmd)
    assert res.stdout == (FIXTURES / "target.stdout.txt").read_text(encoding="utf-8")
    _assert_close_obj(_csv_rows(feasible), _csv_rows(FIXTURES / "target_feasible.csv"))

    got_choice = _json_obj(choice)
    exp_choice = _json_obj(FIXTURES / "target_choice.json")
    got_choice["provenance"]["git"] = "<git>"
    exp_choice["provenance"]["git"] = "<git>"
    got_choice["provenance"]["tech_calib"] = "<tech_calib_hash>"
    exp_choice["provenance"]["tech_calib"] = "<tech_calib_hash>"
    _assert_close_obj(got_choice, exp_choice)


def test_golden_legacy_ecc_selector_cli():
    cmd = [
        sys.executable,
        str(REPO / "ecc_selector.py"),
        "1e-6",
        "2",
        "0.6",
        "1e-15",
        "1",
        "--sustainability",
    ]
    res = _run(cmd)
    assert res.stdout == (FIXTURES / "ecc_selector_legacy.stdout.txt").read_text(encoding="utf-8")
    assert res.stderr == (FIXTURES / "ecc_selector_legacy.stderr.txt").read_text(encoding="utf-8")


def test_golden_energy_sanity_warning_text():
    cmd = [
        sys.executable,
        str(REPO / "eccsim.py"),
        "energy",
        "--code",
        "sec-ded",
        "--node",
        "7",
        "--vdd",
        "0.8",
        "--temp",
        "75",
        "--ops",
        "-5",
        "--lifetime-h",
        "10",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, check=True)
    assert res.stderr == (FIXTURES / "energy_sanity_warning.stderr.txt").read_text(encoding="utf-8")


def test_golden_energy_sanity_strict_error_text():
    cmd = [
        sys.executable,
        str(REPO / "eccsim.py"),
        "energy",
        "--code",
        "sec-ded",
        "--node",
        "7",
        "--vdd",
        "0.8",
        "--temp",
        "75",
        "--ops",
        "-5",
        "--lifetime-h",
        "10",
        "--strict-sanity",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, check=False)
    assert res.returncode == 2
    assert (FIXTURES / "energy_sanity_strict_error.txt").read_text(encoding="utf-8") in res.stderr
