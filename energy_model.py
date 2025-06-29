"""Simple energy model for error correction operations.

This module provides a function to estimate the energy consumed when reading a
code word protected by parity bits. The estimate uses basic constants for the
energy cost of XOR and AND gates.
"""

ENERGY_PER_XOR = 2e-12  # Joules
"""Energy consumed by a single XOR gate operation."""

ENERGY_PER_AND = 1e-12  # Joules
"""Energy consumed by a single AND gate operation."""


def estimate_energy(parity_bits: int, detected_errors: int) -> float:
    """Estimate the energy required to read a word.

    Parameters
    ----------
    parity_bits : int
        Number of parity bits evaluated using XOR gates.
    detected_errors : int
        Number of detected error bits which trigger AND gate checks.

    Returns
    -------
    float
        Estimated energy in joules for the read operation.
    """
    if parity_bits < 0 or detected_errors < 0:
        raise ValueError("Counts must be non-negative")
    return parity_bits * ENERGY_PER_XOR + detected_errors * ENERGY_PER_AND


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Estimate energy per read")
    parser.add_argument("parity_bits", type=int, help="Number of parity bits")
    parser.add_argument(
        "detected_errors", type=int, nargs="?", default=0,
        help="Number of detected error bits (default: 0)"
    )
    args = parser.parse_args()

    energy = estimate_energy(args.parity_bits, args.detected_errors)
    print(f"Estimated energy per read: {energy:.3e} J")
