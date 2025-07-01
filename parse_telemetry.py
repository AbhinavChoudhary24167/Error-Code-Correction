import argparse
from pathlib import Path

import pandas as pd

from energy_model import estimate_energy


def compute_epc(csv_path: str | Path, node_nm: int, vdd: float) -> tuple[float, float]:
    df = pd.read_csv(csv_path, names=["xor", "and", "corrections"])
    xor_cnt = df["xor"].sum()
    and_cnt = df["and"].sum()
    corrections = df["corrections"].sum()
    if corrections <= 0:
        raise ValueError("corrections must be positive")
    total_energy = estimate_energy(xor_cnt, and_cnt, node_nm=node_nm, vdd=vdd)
    return total_energy, total_energy / corrections


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse telemetry CSV and report energy")
    parser.add_argument("--csv", required=True, help="CSV file path")
    parser.add_argument("--node", type=int, required=True, help="Process node in nm")
    parser.add_argument("--vdd", type=float, required=True, help="Supply voltage")
    args = parser.parse_args()
    energy, epc = compute_epc(args.csv, args.node, args.vdd)
    print(f"Total energy: {energy:.3e} J")
    print(f"Energy per correction: {epc:.3e} J/bit")


if __name__ == "__main__":
    main()
