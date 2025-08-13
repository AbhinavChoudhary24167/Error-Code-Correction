"""Adjacent burst MBU model.

Provides a small helper to create probability mass functions (PMFs) over
adjacent multi bit upsets.  The distribution is controlled by a *burst
severity* preset and limited by simple word/bitline geometry knobs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict
import argparse
import json


# Severity presets.  Values indicate the base probability for adjacent
# 2-bit and 3-bit bursts respectively.  These are intentionally simple and
# not derived from silicon measurements – the goal is to provide a light
# weight model that can be tuned via CLI knobs.
_SEVERITY: Dict[str, Dict[str, float]] = {
    "light": {"p2": 0.1, "p3": 0.01},
    "moderate": {"p2": 0.3, "p3": 0.05},
    "heavy": {"p2": 0.8, "p3": 0.2},
}


@dataclass
class MBU:
    """Adjacent burst model returning a PMF for k-bit upsets."""

    severity: str
    word_bits: int = 64
    bitline_bits: int = 64
    p_adj2: float | None = None
    p_adj3: float | None = None

    def pmf(self) -> Dict[int, Dict[str, float]]:
        """Return a PMF distinguishing adjacent and non-adjacent bursts.

        The returned mapping has the form ``{k: {"adj": p, "nonadj": 1-p}}``
        for ``k`` in ``{2, 3}``.
        """

        base = _SEVERITY[self.severity]
        p2 = self.p_adj2 if self.p_adj2 is not None else base["p2"]
        p3 = self.p_adj3 if self.p_adj3 is not None else base["p3"]

        # Geometry limits: if the word or bitline are too short the
        # corresponding adjacent burst cannot occur.
        if self.word_bits < 2 or self.bitline_bits < 2:
            p2 = 0.0
        if self.word_bits < 3 or self.bitline_bits < 3:
            p3 = 0.0

        return {
            2: {"adj": p2, "nonadj": 1.0 - p2},
            3: {"adj": p3, "nonadj": 1.0 - p3},
        }


def pmf_adjacent(
    severity: str,
    word_bits: int = 64,
    bitline_bits: int = 64,
    p_adj2: float | None = None,
    p_adj3: float | None = None,
) -> Dict[int, Dict[str, float]]:
    """Convenience wrapper returning the PMF for ``severity``."""

    model = MBU(
        severity=severity,
        word_bits=word_bits,
        bitline_bits=bitline_bits,
        p_adj2=p_adj2,
        p_adj3=p_adj3,
    )
    return model.pmf()


def main() -> None:
    parser = argparse.ArgumentParser(description="Adjacent burst MBU model")
    parser.add_argument(
        "--mbu",
        choices=sorted(_SEVERITY.keys()),
        default="light",
        help="Burst severity preset",
    )
    parser.add_argument("--word-bits", type=int, default=64)
    parser.add_argument("--bitline-bits", type=int, default=64)
    parser.add_argument("--p-adj2", type=float, default=None)
    parser.add_argument("--p-adj3", type=float, default=None)
    args = parser.parse_args()

    dist = pmf_adjacent(
        args.mbu,
        word_bits=args.word_bits,
        bitline_bits=args.bitline_bits,
        p_adj2=args.p_adj2,
        p_adj3=args.p_adj3,
    )
    print(json.dumps(dist, indent=2))


if __name__ == "__main__":
    main()
