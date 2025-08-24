"""Knee point detection utilities.

This module provides a deterministic and normalised knee point finder based
on the maximum perpendicular distance criterion.  Points are first normalised
to the ``[0, 1]`` range on each axis.  The knee is then chosen as the point
furthest from the line joining the extreme points.  The extreme points are
never selected as the knee which makes the method robust against small
perturbations of the frontier.

The implementation is intentionally light‑weight and has no dependencies
outside the standard library.
"""

from __future__ import annotations

from typing import Sequence, Mapping, Tuple
import math


def max_perp_norm(
    records: Sequence[Mapping[str, float]],
    keys: Sequence[str] = ("FIT", "carbon_kg", "latency_ns"),
) -> Tuple[int, float]:
    """Return the index of the knee point and its distance.

    ``records`` should be an iterable of mappings containing the metrics
    specified by ``keys``.  The metrics are normalised individually to the
    ``[0, 1]`` range before the maximum perpendicular distance from the line
    connecting the extreme points is computed.  The first and last points are
    excluded from consideration which prevents trivial selections of the
    extremes as the knee.  The returned index refers to the position within the
    supplied ``records`` sequence.
    """

    n = len(records)
    if n <= 2:
        return 0, 0.0

    mins = {k: min(r[k] for r in records) for k in keys}
    maxs = {k: max(r[k] for r in records) for k in keys}

    def norm(rec: Mapping[str, float], key: str) -> float:
        span = maxs[key] - mins[key]
        if span <= 0:
            return 0.0
        return (rec[key] - mins[key]) / span

    pts = [tuple(norm(r, k) for k in keys) for r in records]

    # Sort by the second axis for deterministic orientation of the baseline.
    order = sorted(range(n), key=lambda i: pts[i][1])
    p0 = pts[order[0]]
    p1 = pts[order[-1]]
    ab = [p1[d] - p0[d] for d in range(3)]
    ab_len = math.sqrt(sum(v * v for v in ab)) or 1.0

    best_idx = order[1]
    best_dist = -1.0
    for idx in order[1:-1]:
        p = pts[idx]
        ap = [p[d] - p0[d] for d in range(3)]
        cross = (
            ap[1] * ab[2] - ap[2] * ab[1],
            ap[2] * ab[0] - ap[0] * ab[2],
            ap[0] * ab[1] - ap[1] * ab[0],
        )
        dist = math.sqrt(sum(c * c for c in cross)) / ab_len
        if dist > best_dist:
            best_dist = dist
            best_idx = idx

    return best_idx, best_dist


__all__ = ["max_perp_norm"]

