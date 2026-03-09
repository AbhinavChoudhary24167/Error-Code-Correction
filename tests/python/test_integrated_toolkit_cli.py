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


def test_evaluate_generates_integrated_package(tmp_path: Path):
    outdir = tmp_path / "run1"
    res = _run(
        "evaluate",
        "--capacity",
        "1",
        "--word-length",
        "32",
        "--node",
        "14",
        "--vdd",
        "0.8",
        "--temp",
        "75",
        "--ber",
        "1e-9",
        "--altitude",
        "1.5",
        "--fault-modes",
        "sbu",
        "dbu",
        "mbu",
        "burst",
        "--ci",
        "0.55",
        "--outdir",
        str(outdir),
    )
    payload = json.loads(res.stdout)
    assert payload["rows"] > 0
    assert (outdir / "summary" / "integrated_report.json").exists()
    assert (outdir / "data" / "all_candidates.csv").exists()
    assert (outdir / "ml" / "ml_advisory_output.json").exists()


def test_compare_from_config(tmp_path: Path):
    outdir = tmp_path / "run2"
    cfg = {
        "sram_capacity_gib": 1.0,
        "word_length_bits": 32,
        "tech_node_nm": 14,
        "vdd_volts": 0.8,
        "temperature_c": 75.0,
        "ber": 1e-9,
        "fault_modes": ["sbu", "mbu"],
        "carbon_intensity_kgco2_per_kwh": 0.55,
    }
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    res = _run("compare", "--input-config", str(cfg_path), "--outdir", str(outdir))
    payload = json.loads(res.stdout)
    assert payload["evaluated_schemes"] >= 1
    assert (outdir / "tables" / "ecc_comparison_full.csv").exists()


def test_evaluate_populates_ecc_name_and_carbon_fields(tmp_path: Path):
    outdir = tmp_path / "run3"
    _run(
        "evaluate",
        "--capacity",
        "32",
        "--word-length",
        "16",
        "--node",
        "28",
        "--vdd",
        "0.75",
        "--temp",
        "100",
        "--ber",
        "1e-12",
        "--altitude",
        "5",
        "--fault-modes",
        "sbu",
        "dbu",
        "mbu",
        "burst",
        "--ci",
        "0.55",
        "--grid-score",
        "0.75",
        "--outdir",
        str(outdir),
    )
    rows = json.loads((outdir / "data" / "all_candidates.json").read_text(encoding="utf-8"))
    assert rows
    assert all(row.get("ecc_name") for row in rows)
    assert all(row.get("total_carbon_kgco2e") is not None for row in rows)
