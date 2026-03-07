import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "eccsim.py"


def _run(*args: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO,
    )


def test_sram_simulate_json_contract(tmp_path: Path):
    out_csv = tmp_path / "sram_sim.csv"
    res = _run(
        "sram",
        "simulate",
        "--size-kb",
        "64",
        "--word-bits",
        "8",
        "--scheme",
        "sec-ded",
        "--iterations",
        "20",
        "--seed",
        "7",
        "--json",
        "--out-csv",
        str(out_csv),
    )
    payload = json.loads(res.stdout)
    assert "backend" in payload
    assert "scenario_hash" in payload
    assert payload["records"]
    row = payload["records"][0]
    for key in (
        "codec",
        "size_kb",
        "word_bits",
        "reliability_success",
        "energy_proxy",
        "latency_proxy",
        "redundancy_overhead_pct",
        "utility",
    ):
        assert key in row
    assert out_csv.exists()


def test_sram_compare_includes_requested_schemes_json():
    res = _run(
        "sram",
        "compare",
        "--size-kb",
        "128",
        "--word-bits",
        "16",
        "--schemes",
        "sec-ded,taec,bch,polar",
        "--iterations",
        "20",
        "--seed",
        "9",
        "--json",
    )
    payload = json.loads(res.stdout)
    codecs = {str(r["codec"]).lower() for r in payload["records"]}
    assert len(codecs) >= 4


def test_sram_select_deterministic_path(tmp_path: Path):
    report = tmp_path / "sram_select.json"
    candidates = tmp_path / "sram_candidates.csv"
    res = _run(
        "sram",
        "select",
        "--size-kb",
        "256",
        "--word-bits",
        "32",
        "--schemes",
        "sec-ded,taec,bch,polar",
        "--node",
        "14",
        "--vdd",
        "0.8",
        "--temp",
        "75",
        "--ci",
        "0.3",
        "--bitcell-um2",
        "0.08",
        "--report",
        str(report),
        "--emit-candidates",
        str(candidates),
    )
    assert "sram-" in res.stdout
    assert report.exists()
    data = json.loads(report.read_text(encoding="utf-8"))
    assert "best" in data
    assert candidates.exists()
