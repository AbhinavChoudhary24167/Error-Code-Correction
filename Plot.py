from __future__ import annotations

"""Legacy plotting script.

This module is retained only as an explicit demo generator. Production plotting
must use ``eccsim.py plot pareto`` so all points come from factual artifacts.
"""

import argparse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _run_demo() -> None:
    # Demo-only hardcoded data retained for historical documentation.
    bers = [1e-15, 1e-14, 1e-13, 1e-12, 1e-11, 1e-10, 1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2]
    selection = [
        None,
        None,
        None,
        None,
        None,
        None,
        "Hamming_SEC-DED",
        "TAEC",
        "TAEC",
        "TAEC",
        "TAEC",
        "TAEC",
        "TAEC",
        "TAEC",
    ]
    energy_per_read = [
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        1.080e-15,
        9.750e-16,
        9.750e-16,
        9.750e-16,
        9.750e-16,
        9.750e-16,
        9.750e-16,
        9.750e-16,
    ]

    df = pd.DataFrame({"BER": bers, "Selected_ECC": selection, "Energy_per_read_J": energy_per_read})

    df_sel = df.dropna(subset=["Energy_per_read_J"])
    plt.figure()
    plt.scatter(df_sel["BER"], df_sel["Energy_per_read_J"])
    for _, row in df_sel.iterrows():
        plt.annotate(
            row["Selected_ECC"],
            (row["BER"], row["Energy_per_read_J"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
        )
    plt.xscale("log")
    plt.xlabel("BER (log scale)")
    plt.ylabel("Energy per read (J)")
    plt.title("Demo: Selected ECC Energy vs BER (VDD=0.8)")
    plt.tight_layout()
    plt.savefig("ecc_energy_vs_ber_vdd0p8.png", dpi=300)

    ecc_to_idx = {"Hamming_SEC-DED": 1, "TAEC": 2}
    y_vals = [ecc_to_idx.get(x, np.nan) for x in df["Selected_ECC"]]
    plt.figure()
    plt.plot(df["BER"], y_vals, marker="o")
    plt.xscale("log")
    plt.yticks([1, 2], ["Hamming_SEC-DED", "TAEC"])
    plt.xlabel("BER (log scale)")
    plt.ylabel("Selected ECC")
    plt.title("Demo: ECC Switching vs BER (VDD=0.8)")
    plt.tight_layout()
    plt.savefig("ecc_selection_vs_ber_vdd0p8.png", dpi=300)

    df_vdd_compare = pd.DataFrame(
        {
            "VDD": [0.8, 0.9],
            "Selected_ECC": ["TAEC", "Hamming_SEC-DED"],
            "Energy_per_read_J": [9.750e-16, 1.080e-15],
        }
    )
    plt.figure()
    plt.plot(df_vdd_compare["VDD"], df_vdd_compare["Energy_per_read_J"], marker="o")
    for _, row in df_vdd_compare.iterrows():
        plt.annotate(
            row["Selected_ECC"],
            (row["VDD"], row["Energy_per_read_J"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
        )
    plt.xlabel("VDD (V)")
    plt.ylabel("Energy per read (J)")
    plt.title("Demo: ECC Selection vs VDD at BER=1e-8")
    plt.tight_layout()
    plt.savefig("ecc_selection_vs_vdd_ber1e-8.png", dpi=300)


def main() -> None:
    parser = argparse.ArgumentParser(description="Legacy demo plotting script")
    parser.add_argument(
        "--demo-data",
        action="store_true",
        help="Run historical hardcoded demo plots. Production use is not supported here.",
    )
    args = parser.parse_args()

    if not args.demo_data:
        raise SystemExit(
            "Plot.py no longer supports production plotting. Use: python3 eccsim.py plot pareto ... "
            "or pass --demo-data to generate legacy demonstration figures."
        )

    _run_demo()


if __name__ == "__main__":  # pragma: no cover - manual entrypoint
    main()
