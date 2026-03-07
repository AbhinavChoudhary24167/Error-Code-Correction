import csv
import json
import math
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "golden"


def _run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=REPO)


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

    if isinstance(expected, (float, int)) and isinstance(actual, (float, int, str)):
        assert math.isclose(float(actual), float(expected), rel_tol=rel_tol, abs_tol=abs_tol)
        return

    assert actual == expected


def test_golden_energy_default_stdout():
    res = _run(
        [
            sys.executable,
            "eccsim.py",
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
            "1000",
            "--lifetime-h",
            "10",
        ]
    )
    assert res.stdout == (FIXTURES / "energy_default.stdout.txt").read_text(encoding="utf-8")


def test_golden_carbon_default_stdout():
    res = _run(
        [
            sys.executable,
            "eccsim.py",
            "carbon",
            "--areas",
            "0.1,0.2",
            "--alpha",
            "120,140",
            "--ci",
            "0.55",
            "--Edyn",
            "0.01",
            "--Eleak",
            "0.02",
        ]
    )
    assert res.stdout == (FIXTURES / "carbon_default.stdout.txt").read_text(encoding="utf-8")


def test_golden_hazucha_default_stdout():
    res = _run(
        [
            sys.executable,
            "eccsim.py",
            "reliability",
            "hazucha",
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
        ]
    )
    assert res.stdout == (FIXTURES / "hazucha_default.stdout.txt").read_text(encoding="utf-8")


def test_golden_esii_json_stdout():
    res = _run(
        [
            sys.executable,
            "eccsim.py",
            "esii",
            "--fit-base",
            "1e-6",
            "--fit-ecc",
            "1e-9",
            "--e-dyn-j",
            "1e-3",
            "--e-leak-j",
            "2e-3",
            "--ci",
            "0.55",
            "--embodied-kgco2e",
            "0.25",
            "--basis",
            "per_gib",
        ]
    )
    got = json.loads(res.stdout)
    expected = json.loads((FIXTURES / "esii_default.json").read_text(encoding="utf-8"))
    got["provenance"] = {
        "git": "<git>",
        "tech_calib": "<tech_calib_hash>",
        "qcrit": "<qcrit_hash>",
    }
    _assert_close_obj(got, expected)


def test_cli_output_schema_contract_fields_remain_unchanged():
    with (FIXTURES / "reliability_report.json").open(encoding="utf-8") as fh:
        reliability = json.load(fh)
    assert set(reliability.keys()) == {
        "basis",
        "fit",
        "mbu",
        "scrub_s",
        "node_nm",
        "vdd",
        "tempC",
    }
    assert set(reliability["fit"].keys()) == {"base", "ecc"}

    with (FIXTURES / "target_choice.json").open(encoding="utf-8") as fh:
        target_choice = json.load(fh)
    assert {"status", "target_type", "target", "scrub_s", "provenance", "choice"}.issubset(
        set(target_choice)
    )
    assert {"git", "tech_calib", "scenario_hash"}.issubset(set(target_choice["provenance"]))

    with (FIXTURES / "select_candidates.csv").open(newline="", encoding="utf-8") as fh:
        candidate_fields = list(csv.DictReader(fh).fieldnames or [])
    assert candidate_fields == [
        "code",
        "scrub_s",
        "FIT",
        "carbon_kg",
        "latency_ns",
        "ESII",
        "NESII",
        "GS",
        "areas",
        "energies",
        "violations",
        "scenario_hash",
    ]

    with (FIXTURES / "target_feasible.csv").open(newline="", encoding="utf-8") as fh:
        feasible_fields = list(csv.DictReader(fh).fieldnames or [])
    assert feasible_fields == [
        "code",
        "fit_bit",
        "fit_word_post",
        "FIT",
        "carbon_kg",
        "ESII",
        "NESII",
        "GS",
        "scrub_s",
        "area_logic_mm2",
        "area_macro_mm2",
        "E_dyn_kWh",
        "E_leak_kWh",
        "E_scrub_kWh",
    ]
