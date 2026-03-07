import json
import subprocess
import sys
import uuid
from pathlib import Path

from ml.dataset import build_dataset
from ml.train import train_models


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
    assert "ml_requested" not in data
    assert candidates.exists()


def _prepare_model(tag: str) -> Path:
    base = REPO / "tests" / "fixtures" / "runtime_ml_tests" / f"sram_{tag}_{uuid.uuid4().hex}"
    dataset_dir = base / "dataset"
    model_dir = base / "model"
    dataset_dir.parent.mkdir(parents=True, exist_ok=True)
    build_dataset(REPO / "reports" / "examples", dataset_dir, seed=1)
    train_models(dataset_dir, model_dir, seed=1)
    return model_dir


def test_sram_select_ml_advisory_fields_present(tmp_path: Path):
    model_dir = _prepare_model("advisory")
    report = tmp_path / "sram_select_ml.json"
    _run(
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
        "--ml-model",
        str(model_dir),
        "--report",
        str(report),
    )
    data = json.loads(report.read_text(encoding="utf-8"))
    for key in (
        "ml_requested",
        "ml_used",
        "fallback_used",
        "baseline_choice",
        "advisory_choice",
        "advisory_confidence",
        "advisory_ood_score",
        "advisory_policy",
        "final_choice",
        "final_choice_reason",
    ):
        assert key in data
    assert data["ml_requested"] is True
    assert data["baseline_choice"] == data["final_choice"]


def test_sram_select_ml_fallback_on_low_confidence(tmp_path: Path):
    model_dir = _prepare_model("low_conf")
    report = tmp_path / "sram_select_low_conf.json"
    _run(
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
        "--ml-model",
        str(model_dir),
        "--ml-confidence-min",
        "0.9999",
        "--report",
        str(report),
    )
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["fallback_used"] is True
    assert data["ml_used"] is False
    assert data["final_choice"] == data["baseline_choice"]


def test_sram_select_ml_fallback_on_ood(tmp_path: Path):
    model_dir = _prepare_model("ood")
    report = tmp_path / "sram_select_ood.json"
    _run(
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
        "--ml-model",
        str(model_dir),
        "--ml-ood-max",
        "0.01",
        "--report",
        str(report),
    )
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["fallback_used"] is True
    assert data["ml_used"] is False
    assert data["final_choice"] == data["baseline_choice"]
