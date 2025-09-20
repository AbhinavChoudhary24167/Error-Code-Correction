from __future__ import annotations

"""Hypervolume and spacing metrics for Pareto frontiers."""

import math
from typing import Iterable, Sequence

import numpy as np


def normalize(points: Iterable[Sequence[float]]) -> np.ndarray:
    """Normalize points to the unit hypercube.

    Each dimension is scaled to ``[0, 1]`` based on the min and max across
    the provided points.  If a dimension has zero span the coordinate is kept
    at ``0`` for all points.
    """

    arr = np.asarray(list(points), dtype=float)
    if arr.size == 0:
        return arr
    mins = np.min(arr, axis=0)
    maxs = np.max(arr, axis=0)
    span = np.where(maxs - mins == 0, 1.0, maxs - mins)
    return (arr - mins) / span


def hypervolume(points: Iterable[Sequence[float]], ref: Sequence[float] | None = None) -> float:
    """Compute the hypervolume of ``points`` for minimisation problems.

    ``points`` are assumed to lie in the unit hypercube.  ``ref`` denotes the
    reference point in normalized coordinates and defaults to ``(1, …, 1)``.
    """

    pts = [tuple(p) for p in points]
    if not pts:
        return 0.0
    dim = len(pts[0])
    if ref is None:
        ref = (1.0,) * dim

    # ``dx`` is accumulated as ``prev - p[0]`` in the sweep below.  When points
    # are processed in ascending order of the first objective ``dx`` can become
    # negative (and subsequently shrink the accumulated dominated volume).
    # Sorting in descending order guarantees ``prev`` is monotonically
    # decreasing as points are processed, keeping each ``dx`` non-negative.
    pts.sort(key=lambda p: p[0], reverse=True)

    def _hv(slice_pts: list[tuple[float, ...]], r: Sequence[float]) -> float:
        if not slice_pts:
            return 0.0
        slice_pts = sorted(slice_pts, key=lambda p: p[0], reverse=True)
        prev = r[0]
        vol = 0.0
        for i, p in enumerate(slice_pts):
            dx = prev - p[0]
            if len(r) == 1:
                contrib = dx
            else:
                next_pts = [q[1:] for q in slice_pts[i:]]
                contrib = dx * _hv(next_pts, r[1:])
            vol += contrib
            prev = p[0]
        return vol

    return float(_hv(pts, ref))


def schott_spacing(points: Iterable[Sequence[float]]) -> float:
    """Compute Schott's spacing metric for ``points``.

    ``points`` are assumed to lie in the unit hypercube.
    """

    arr = np.asarray(list(points), dtype=float)
    n = len(arr)
    if n <= 1:
        return 0.0
    dists = []
    for i in range(n):
        diff = arr - arr[i]
        dist = np.linalg.norm(diff, axis=1)
        dist[i] = np.inf
        dists.append(np.min(dist))
    dists = np.asarray(dists)
    dbar = np.mean(dists)
    return float(math.sqrt(np.sum((dists - dbar) ** 2) / (n - 1)))


__all__ = ["normalize", "hypervolume", "schott_spacing"]
