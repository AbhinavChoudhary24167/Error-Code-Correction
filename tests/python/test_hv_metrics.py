from analysis.hv import hypervolume, schott_spacing


def test_better_frontier_has_higher_hv():
    worse = [(0.6, 0.6)]
    better = [(0.4, 0.4)]
    assert hypervolume(better) > hypervolume(worse)


def test_clustered_points_reduce_spacing():
    spread = [(0.0, 0.0), (0.5, 0.1), (0.9, 0.2)]
    clustered = [(0.0, 0.0), (0.01, 0.01), (0.02, 0.02)]
    assert schott_spacing(clustered) < schott_spacing(spread)
