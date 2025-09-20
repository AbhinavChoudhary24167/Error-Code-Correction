import pytest

from analysis.hv import hypervolume, schott_spacing


def test_better_frontier_has_higher_hv():
    worse = [(0.6, 0.6)]
    better = [(0.4, 0.4)]
    assert hypervolume(better) > hypervolume(worse)


def test_hypervolume_two_point_regression():
    points = [(0.2, 0.6), (0.6, 0.2)]
    # The dominated area is the union of the rectangles from each point to
    # the reference corner ``(1, 1)``.  Analytically, the union area is:
    #   (0.8 * 0.4) + (0.4 * 0.8) - (0.4 * 0.4) = 0.48
    assert hypervolume(points) == pytest.approx(0.48)


def test_clustered_points_reduce_spacing():
    spread = [(0.0, 0.0), (0.5, 0.1), (0.9, 0.2)]
    clustered = [(0.0, 0.0), (0.01, 0.01), (0.02, 0.02)]
    assert schott_spacing(clustered) < schott_spacing(spread)
