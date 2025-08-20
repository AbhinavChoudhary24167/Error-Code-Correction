import numpy as np
from esii import normalise_esii


def test_nesii_monotonic():
    esii_vals = [1.0, 2.0, 3.0, 4.0]
    scores, p5, p95 = normalise_esii(esii_vals)
    assert np.argsort(scores).tolist() == np.argsort(esii_vals).tolist()


def test_nesii_invariance_scaling():
    esii_vals = [1.0, 2.0, 3.0]
    scores1, _, _ = normalise_esii(esii_vals)
    scaled = [v * 0.5 for v in esii_vals]
    scores2, _, _ = normalise_esii(scaled)
    assert np.argsort(scores1).tolist() == np.argsort(scores2).tolist()
