from __future__ import annotations

"""CLI wrapper for strict factual Pareto plotting."""

import argparse
from pathlib import Path

from analysis.plot_pipeline import PlotRequest, generate_pareto_plot


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a factual Pareto plot from ECC artifacts")
    parser.add_argument("--from", dest="from_path", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--x", type=str, default="carbon_kg")
    parser.add_argument("--y", type=str, default="FIT")
    parser.add_argument("--x-objective", choices=["min", "max"], default="min")
    parser.add_argument("--y-objective", choices=["min", "max"], default="min")
    parser.add_argument("--codes", type=str, default=None)
    parser.add_argument("--node", type=int, default=None)
    parser.add_argument("--vdd", type=float, default=None)
    parser.add_argument("--temp", type=float, default=None)
    parser.add_argument("--scrub-interval-s", dest="scrub_interval_s", type=float, default=None)
    parser.add_argument("--capacity-gib", type=float, default=None)
    parser.add_argument("--target-ber", dest="target_ber", type=float, default=None)
    parser.add_argument("--show-dominated", action="store_true")
    parser.add_argument("--save-metadata", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--strict-scenario", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--error-on-empty", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--log-x", action="store_true")
    parser.add_argument("--log-y", action="store_true")
    args = parser.parse_args()

    req = PlotRequest(
        from_path=args.from_path,
        out_path=args.out,
        x=args.x,
        y=args.y,
        x_objective=args.x_objective,
        y_objective=args.y_objective,
        scenario_filters={
            "codes": args.codes,
            "node": args.node,
            "vdd": args.vdd,
            "temp": args.temp,
            "scrub_interval_s": args.scrub_interval_s,
            "capacity_gib": args.capacity_gib,
            "target_ber": args.target_ber,
        },
        show_dominated=args.show_dominated,
        save_metadata=args.save_metadata,
        strict_scenario=args.strict_scenario,
        error_on_empty=args.error_on_empty,
        log_x=args.log_x,
        log_y=args.log_y,
    )
    result = generate_pareto_plot(req)
    print(
        f"plot={result.out_path} rows_loaded={result.rows_loaded} "
        f"rows_filtered={result.rows_filtered} rows_plotted={result.rows_plotted}"
    )
    if result.metadata_path is not None:
        print(f"metadata={result.metadata_path}")


if __name__ == "__main__":  # pragma: no cover - manual entrypoint
    main()
