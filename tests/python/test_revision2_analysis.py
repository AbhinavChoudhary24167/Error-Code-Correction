import importlib.util
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("revision2_analysis", ROOT / "scripts/revision2/analyze_results.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_revision2_sample_statistics_and_percent_delta():
    summary = MODULE.stat_summary({11: 1.0, 13: 2.0, 17: 3.0, 19: 4.0, 23: 5.0})
    assert summary["mean"] == 3.0
    assert summary["median"] == 3.0
    assert math.isclose(summary["sample_standard_deviation"], math.sqrt(2.5))
    assert summary["minimum"] == 1.0
    assert summary["maximum"] == 5.0
    assert summary["range"] == 4.0
    assert MODULE.percent_delta(125.0, 100.0) == 25.0


def test_revision2_dominance_respects_frequency_direction_and_latency():
    comb = {"area": 10.0, "latency": 1.0, "energy": 5.0, "frequency": 100.0}
    pipe = {"area": 12.0, "latency": 3.0, "energy": 4.0, "frequency": 150.0}
    assert not MODULE.dominates(comb, pipe)
    assert not MODULE.dominates(pipe, comb)
    worse = {"area": 13.0, "latency": 4.0, "energy": 6.0, "frequency": 90.0}
    assert MODULE.dominates(comb, worse)
