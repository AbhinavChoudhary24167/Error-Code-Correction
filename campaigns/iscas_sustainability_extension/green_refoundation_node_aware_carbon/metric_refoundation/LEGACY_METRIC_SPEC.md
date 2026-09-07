# Legacy metric specification

## Status and source priority

These definitions are frozen as `LEGACY_COMPATIBILITY_METRICS`; this document does not endorse them for selection. Executable source has priority over prose. `docs/ESII.md` still describes the pre-March-2026 ratio ESII and therefore conflicts with current `esii.py`.

## ESII generations

### ESII-v1: improvement per carbon

Source: `esii.py` at parent commit `b21e5c341c0767c9a7f86f3e626206a4dad3dcb4`, immediately before commit `fcb09edbe3cdf095152e26a7f41c1762b5da1412`.

Let

\[
C_{op}=CI\,(E_{dyn}+E_{leak}+E_{scrub})/3.6\times 10^6,
\quad C_{tot}=C_{op}+C_{emb},
\]

with energy in joules, grid intensity in kgCO2e/kWh, and carbon in kgCO2e. Then

\[
\Delta FIT=\max(FIT_{base}-FIT_{ecc},0),
\quad ESII_{v1}=\begin{cases}
0,&C_{tot}<10^{-12},\\
\Delta FIT/C_{tot},&\text{otherwise.}
\end{cases}
\]

Its units are FIT/kgCO2e, despite the name “index.” `docs/ESII.md` describes this generation.

### ESII-v2: current bounded utility

Source: current `esii.py`, SHA-256 `00df7bdf9d3e6bcb005b83f0a3cccbf4a1c7d358cc1c7e4c9302877006d9145a`, introduced by `fcb09ed`.

With `FIT_FLOOR=10^-30`, `h_R=2 decades`, `h_E=1 kWh`, and `h_C=1 kgCO2e`:

\[
d_R=\max[\log_{10}(FIT_{base}+10^{-30})-\log_{10}(FIT_{ecc}+10^{-30}),0],
\]

\[
U_R={d_R\over d_R+h_R},\quad
U_E={1\over 1+E_{tot,kWh}/h_E},\quad
U_C={1\over 1+C_{tot}/h_C},
\]

\[
ESII_{v2}=U_R(0.5U_E+0.5U_C).
\]

The output is clamped to `[0,1]`. The half-saturation anchors and equal burden weights are hard-coded hypotheses, not source-calibrated physical constants.

## NESII

Source: current `esii.py::normalise_esii`, introduced by `f54fc7c3391b621bf7d53cae9346313085aa8ee5`; selector fallback behavior is in `ecc_selector.py` SHA-256 `958c4dbc77cd79e8c76bf78bb78b0b1521a19b291b76c35e580958b8a274e0b8`.

For cohort ESII values `x`, define `p5` and `p95` from the cohort, clip each value to those anchors, and compute

\[
NESII(x)=100{\operatorname{clip}(x,p5,p95)-p5\over p95-p5+10^{-9}}.
\]

The selector instead uses cohort min-max normalization when `N<20` or the percentile anchors coincide. If the min-max span is zero, every score is forced to 50. The selector records `N`, method, anchors, and scope as metadata.

## GREEN Score generations

### GS-harmonic-v1 (historical)

Source: `gs.py` at commit `b21e5c341c0767c9a7f86f3e626206a4dad3dcb4`, Git blob `e2f40395f67be60fcacf857486a040123e536bdd`; introduced in `1b63b8d9c38162fcc5a16324e25eb9de5930e818`.

\[
r={\max(FIT_{base}-FIT_{ecc},0)\over FIT_{base}},\quad
S_r={r\over r+0.05},\quad
S_c={1\over1+C_{kg}/1},\quad
S_l={1\over1+\max(L-L_0,0)/10}.
\]

Negative weights are clamped to zero and all weights are normalized. With default weights `(0.6,0.3,0.1)` and `epsilon=10^-9`:

\[
GS_H=100\left(\sum_i{w_i\over\max(S_i,\epsilon)}\right)^{-1}.
\]

### GS-geometric-v2 (current)

Source: current `gs.py`, SHA-256 `5f13dc67750aa6a0baf31e0ff403cece7429ba669c917aef4a6990e51a9b9fb2`, introduced by `fcb09ed`.

Current utilities are `S_r=d_R/(d_R+2)`, `S_c=1/(1+C/1 kg)`, `S_l=1/(1+max(L-L0,0)/10 ns)`, and optional `S_o=1/(1+overhead/0.25)`. Active non-negative weights are normalized; defaults are `(0.6,0.25,0.1,0.05)`. The implementation computes

\[
GS_G=100\exp\left(\sum_i\bar w_i\log(\max(S_i,10^{-12}))\right).
\]

When carbon is `None`, carbon is treated as neutral and its weight is removed before renormalization. `scores.py` passes calculated carbon, but `ecc_selector.py::_annotate_gs` first clips carbon using the cohort maximum for `N<5` or cohort p95 otherwise; nearly identical cohort carbon is replaced by zero. The selector calls the 3-weight form `(0.6,0.3,0.1)`.

## EPC

Source: `energy_model.py::epc`, lines 360-389, originally commit `a663d92b`; current file SHA-256 `a23022ff13ae45026de8858cf9de41cddcba1833e587e840180f0b845352efa1`.

\[
EPC={E_{gate\ estimate}(N_{xor},N_{and},node,VDD)\over N_{corrected\ bits}}
\quad[J/corrected\ bit],
\]

defined only for a strictly positive correction count. It is an event-conditional energy diagnostic, not a lifecycle sustainability metric.
