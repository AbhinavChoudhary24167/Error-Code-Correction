from pathlib import Path

import numpy as np
import pytest

from parse_telemetry import compute_epc
from energy_model import estimate_energy


def test_compute_epc_sample():
    csv_path = Path(__file__).resolve().parent.parent / "data" / "sample_secdaec.csv"
    energy, epc_val = compute_epc(csv_path, 16, 0.7)

    expected_energy = estimate_energy(10000, 5000, node_nm=16, vdd=0.7)
    assert energy == pytest.approx(expected_energy)
    assert epc_val == pytest.approx(expected_energy / 100, abs=1e-15)
