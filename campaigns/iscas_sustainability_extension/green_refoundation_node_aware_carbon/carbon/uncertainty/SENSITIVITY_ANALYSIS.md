# Uncertainty and sensitivity analysis

## Result and scope

The checked-in run uses 4,096 deterministic Latin-hypercube samples with seed
`20260908`. It evaluates a normalized good-die manufacturing-carbon index. The
constructed baseline equals one and uses a component split inside the broad
share ranges described by the 2023 imec study; it is not an absolute node
coefficient.

| Statistic | Normalized index |
|---|---:|
| Mean | 1.21749120303 |
| Median | 1.19324059674 |
| P05 | 0.690633691213 |
| P95 | 1.83824570130 |
| Minimum sampled stratum combination | 0.422233680094 |
| Maximum sampled stratum combination | 2.75319592585 |

These are `PARAMETRIC_UNCERTAIN` scenario-ensemble quantiles. They are not
confidence intervals and should not be compared to CarbonClarity's fitted KDE
percentiles as if the inference basis were equivalent.

## Screening sensitivity

Absolute Spearman rank correlations, normalized to sum to one, rank the
declared interval effects:

| Rank | Parameter | rho | Normalized absolute influence |
|---:|---|---:|---:|
| 1 | fab grid CI factor | +0.7735 | 0.3741 |
| 2 | defect density | +0.3938 | 0.1905 |
| 3 | abatement efficiency | -0.3006 | 0.1454 |
| 4 | fab energy factor | +0.2060 | 0.0997 |
| 5 | line yield | -0.1837 | 0.0888 |
| 6 | upstream factor | +0.1105 | 0.0535 |
| 7 | gas-use factor | +0.0996 | 0.0482 |

The signs agree with the equation: higher grid CI, defect density, energy, gas
use, or upstream burden increases carbon; improved abatement or line yield
decreases it. Ranking is conditional on the selected interval widths and does
not prove that grid CI dominates every fab or node. Spearman screening is not
a Sobol variance decomposition and interactions remain present.

## Distribution choice

CarbonClarity uses Gaussian-kernel KDE because it has multiple temporal and
geographic observations. This campaign lacks equivalent observation sets for
several parameters and therefore does not select normal, lognormal, beta, or
other probability families. Midpoints of equal-width strata cover each linear
interval once; a fixed seed controls only the pairing between parameters.

## Deferred uncertainty

Mask NRE stays in its separate log-scale sensitivity table because its absolute
carbon boundary is unavailable. Package allocation is not qualified. Lifetime,
use-phase grid CI, activity, SER, MBU geometry, and macro energy enter only when
the operational/reliability scenario layers are assembled. Consequently this
phase emits no lifecycle GSE distribution and no ECC ranking.

## Reproduction

Run:

`python -B carbon/uncertainty/run_uncertainty.py`

from the campaign directory. The test suite reruns the generator and requires
byte-identical result and sensitivity CSVs.
