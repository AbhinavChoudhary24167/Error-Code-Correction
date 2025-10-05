"""SRAM bit error rate and ECC benchmarking utilities."""

from math import exp

from ecc_mux import compute_ecc_mux_params
from esii import ESIIInputs, compute_esii
from scores import compute_scores

# Baseline FIT rates per megabit at sea level for different technology nodes.
FIT_PER_MB = {
    "28nm": 74.0,
    "16nm": 5.0,
    "7nm": 0.4,
}

# Flux multipliers for various environments.
ENV_MULTIPLIERS = {
    "consumer": 1,
    "avionics": 300,
    "space": 50000,
}

HOURS_PER_YEAR = 365 * 24


def annual_error_count(fit_per_mb: float, capacity_mb: float, flux_multiplier: float) -> float:
    """Return expected number of bit errors per year.

    Args:
        fit_per_mb: FIT rate per megabit for the technology node.
        capacity_mb: Memory capacity in megabits.
        flux_multiplier: Environmental radiation multiplier.
    """
    total_fit = fit_per_mb * capacity_mb * flux_multiplier
    return total_fit * HOURS_PER_YEAR / 1e9


def max_capacity_without_ecc(fit_per_mb: float, fit_limit: float = 10) -> float:
    """Maximum memory capacity in megabits given a FIT limit."""
    return fit_limit / fit_per_mb


def soft_error_probability(fit_per_mb: float, capacity_mb: float, years: float) -> float:
    """Probability of at least one soft error over the given years."""
    rate = fit_per_mb * capacity_mb * (HOURS_PER_YEAR * years) / 1e9
    return 1 - exp(-rate)


# Error pattern distribution for Task 2
ERROR_DISTRIBUTION = {
    "single": 0.85,
    "double_adjacent": 0.12,
    "triple_adjacent": 0.02,
    "random_double": 0.01,
}

# Sustainability matrix parameters per ECC scheme.  Energies are in Joules and
# embodied carbon in kilograms of CO2e.
SUSTAINABILITY_PARAMS = {
    "Hamming_SEC": {"e_dyn": 2_000_000.0, "e_leak": 1_000_000.0, "ci": 0.3, "embodied": 1.0},
    "SEC_DED": {"e_dyn": 2_400_000.0, "e_leak": 1_200_000.0, "ci": 0.3, "embodied": 1.2},
    "TAEC": {"e_dyn": 2_800_000.0, "e_leak": 1_400_000.0, "ci": 0.3, "embodied": 1.5},
    "DEC": {"e_dyn": 3_200_000.0, "e_leak": 1_600_000.0, "ci": 0.3, "embodied": 1.8},
}


def residual_error_rate(scheme: str) -> float:
    """Residual uncorrectable error rate for a given ECC scheme."""
    d = ERROR_DISTRIBUTION
    if scheme == "Hamming_SEC":
        return d["double_adjacent"] + d["triple_adjacent"] + d["random_double"]
    if scheme == "SEC_DED":
        return d["double_adjacent"] + d["triple_adjacent"] + d["random_double"]
    if scheme == "TAEC":
        return d["random_double"]
    if scheme == "DEC":
        return d["triple_adjacent"]
    raise ValueError(f"Unknown scheme: {scheme}")


def _parity_bits_for_sec(k: int) -> int:
    p = 1
    while 2 ** p < k + p + 1:
        p += 1
    return p


def check_bits_required(scheme: str, data_bits: int = 64) -> int:
    """Return minimum number of check bits for the given scheme."""
    n = data_bits
    if scheme == "Hamming_SEC":
        return _parity_bits_for_sec(n)
    if scheme == "SEC_DED":
        return _parity_bits_for_sec(n) + 1
    if scheme == "TAEC":
        patterns = 1 + n + (n - 1) + (n - 2)
        p = 1
        while 2 ** p < patterns:
            p += 1
        return p
    if scheme == "DEC":
        patterns = 1 + n + n * (n - 1) // 2
        p = 1
        while 2 ** p < patterns:
            p += 1
        return p
    raise ValueError(f"Unknown scheme: {scheme}")


def hybrid_ecc_strategy() -> str:
    """Return a description of a hybrid ECC approach for space applications."""
    return (
        "Combine a TAEC inner code with interleaving and a lightweight outer "
        "SEC-DED code. TAEC handles the 90% of localized single, double- and "
        "triple-adjacent upsets while the outer code detects remaining random "
        "multi-bit patterns. Periodic memory scrubbing clears latent faults." )


def sustainability_benchmark(capacity_mb: float) -> None:
    """Print sustainability scores for each ECC scheme and technology node."""

    schemes = ["Hamming_SEC", "SEC_DED", "TAEC", "DEC"]
    # Ensure consistent ordering (largest geometry first) when reporting nodes.
    ordered_nodes = sorted(
        FIT_PER_MB,
        key=lambda node_label: int(node_label.rstrip("nm")),
        reverse=True,
    )

    for node in ordered_nodes:
        fit_base = FIT_PER_MB[node] * capacity_mb

        esii_inputs = {}
        esii_vals = []
        mux_metrics = {}
        for scheme in schemes:
            params = SUSTAINABILITY_PARAMS[scheme]
            uncorr = residual_error_rate(scheme)
            inp = ESIIInputs(
                fit_base=fit_base,
                fit_ecc=fit_base * uncorr,
                e_dyn=params["e_dyn"],
                e_leak=params["e_leak"],
                ci_kgco2e_per_kwh=params["ci"],
                embodied_kgco2e=params["embodied"],
            )
            esii_inputs[scheme] = inp
            esii_vals.append(compute_esii(inp)["ESII"])
            mux_metrics[scheme] = compute_ecc_mux_params(scheme)

        print(f"Sustainability scores for {node} node (16MB at sea level):")
        for scheme in schemes:
            latency, energy, area, fanin = mux_metrics[scheme]
            res = compute_scores(
                esii_inputs[scheme],
                latency_ns=latency,
                esii_reference=esii_vals,
            )
            print(
                f"  {scheme}: ESII={res['ESII']:.2f}, NESII={res['NESII']:.2f}, GS={res['GS']:.2f}" \
                f", mux latency={latency}, energy={energy}, area={area}, mux {fanin}:1"
            )
        print()


if __name__ == "__main__":
    # Task 1 calculations
    capacity_mb = 16 * 8  # 16 MB array
    print("Annual bit errors for 16MB SRAM array:")
    for node, fit in FIT_PER_MB.items():
        for env, mult in ENV_MULTIPLIERS.items():
            errors = annual_error_count(fit, capacity_mb, mult)
            print(f"  {node} at {env}: {errors:.3e} errors/year")
    print()

    print("Max SRAM without ECC for ASIL-D (10 FIT limit):")
    for node, fit in FIT_PER_MB.items():
        max_mb = max_capacity_without_ecc(fit)
        print(f"  {node}: {max_mb/8:.2f} MB")
    print()

    one_gb_mb = 1024 * 8
    prob = soft_error_probability(FIT_PER_MB["16nm"], one_gb_mb, years=3)
    print(f"Probability of ≥1 soft error in 1GB over 3 years: {prob:.2%}")
    print()

    # Task 2 calculations
    print("Residual uncorrectable error rates:")
    schemes = ["Hamming_SEC", "SEC_DED", "TAEC", "DEC"]
    for scheme in schemes:
        print(f"  {scheme}: {residual_error_rate(scheme)*100:.1f}%")
    print()

    print("Check bit overhead for 64-bit words:")
    for scheme in schemes:
        print(f"  {scheme}: {check_bits_required(scheme)} bits")
    print()

    print("Hybrid ECC strategy for space application:")
    print(hybrid_ecc_strategy())
    print()

    # Sustainability matrix benchmarking
    sustainability_benchmark(capacity_mb)
