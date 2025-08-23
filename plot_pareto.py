import pandas as pd
import matplotlib.pyplot as plt
from ecc_selector import select


def main() -> None:
    """Generate a scatter plot for the Pareto frontier.

    The plot illustrates the trade-offs between FIT and carbon footprint for
    a small set of ECC codes.  Point colour encodes latency in nanoseconds.
    """
    params = {
        "node": 14,
        "vdd": 0.8,
        "temp": 75.0,
        "capacity_gib": 8.0,
        "ci": 0.55,
        "bitcell_um2": 0.040,
    }
    codes = ["sec-ded-64", "sec-daec-64", "taec-64"]
    result = select(codes, **params)
    pareto = result["pareto"]
    if not pareto:
        raise SystemExit("No Pareto frontier returned")
    df = pd.DataFrame(pareto)
    df.to_csv("pareto.csv", index=False)
    plt.figure()
    scatter = plt.scatter(
        df["FIT"], df["carbon_kg"], c=df["latency_ns"], cmap="viridis"
    )
    for _, row in df.iterrows():
        plt.annotate(
            row["code"],
            (row["FIT"], row["carbon_kg"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
        )
    plt.colorbar(scatter, label="Latency (ns)")
    plt.xlabel("FIT")
    plt.ylabel("Carbon (kg)")
    plt.title("Pareto frontier trade-offs")
    plt.tight_layout()
    plt.savefig("pareto_tradeoff.png", dpi=300)
    print("Plot saved as pareto_tradeoff.png")


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
