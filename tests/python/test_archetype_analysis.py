from pathlib import Path

import pandas as pd
import yaml

from analysis.archetype import classify_archetypes, _load_archetypes


def create_data(tmp_path: Path) -> Path:
    df = pd.DataFrame(
        {
            "fit": [1e-16, 5e-13, 5e-12, 1e-12],
            "latency_ns": [3.5, 2.0, 1.0, 1.0],
            "carbon_kg": [0.9, 0.5, 0.2, 0.5],
        }
    )
    path = tmp_path / "pareto.csv"
    df.to_csv(path, index=False)
    return path


def test_archetype_classification(tmp_path: Path) -> None:
    pareto = create_data(tmp_path)
    out = tmp_path / "arch.json"
    result = classify_archetypes(pareto, out)
    assert result["counts"]["Fortress"] == 1
    assert result["counts"]["Efficiency"] == 1
    assert result["counts"]["Frugal"] == 1
    assert result["counts"]["SpeedDemon"] == 1
    assert "version" in result["provenance"]


def test_archetype_config_tweak(tmp_path: Path) -> None:
    pareto = create_data(tmp_path)
    out = tmp_path / "arch.json"
    result = classify_archetypes(pareto, out)
    assert result["counts"]["Efficiency"] == 1

    repo_root = Path(__file__).resolve().parents[2]
    cfg = yaml.safe_load((repo_root / "configs" / "archetypes.yaml").read_text())
    cfg["archetypes"]["Efficiency"]["fit_hi"] = 1e-13
    cfg_path = tmp_path / "arcs.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    out2 = tmp_path / "arch2.json"
    result2 = classify_archetypes(pareto, out2, cfg_path)
    assert result2["counts"].get("Efficiency", 0) == 0
    assert result2["counts"]["Unknown"] == 1


def test_confidence_monotone() -> None:
    _, arcs, _ = _load_archetypes()
    eff = arcs["Efficiency"]
    c = eff.center
    row_center = pd.Series(c)
    row_mid = pd.Series(c)
    row_mid["carbon_kg"] = c["carbon_kg"] + (eff.carbon_hi - c["carbon_kg"]) / 2
    row_edge = pd.Series({"fit": c["fit"], "latency_ns": c["latency_ns"], "carbon_kg": eff.carbon_hi})
    conf_center = eff.matches(row_center)
    conf_mid = eff.matches(row_mid)
    conf_edge = eff.matches(row_edge)
    assert conf_center > conf_mid > conf_edge

