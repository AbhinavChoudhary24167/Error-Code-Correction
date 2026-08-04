# Reliability and error models

This repository contains two related but distinct reliability paths. The multi-ECC study uses exact decoder outcome fractions combined with a preregistered per-codeword fault-profile probability mass. The legacy CLI also exposes SER/FIT, MBU and scrub models. Their identifiers and assumptions are not automatically interchangeable.

## Code rate, redundancy and syndrome

For an `(n,k)` binary linear code,

\[
R = \frac{k}{n}, \qquad r=n-k.
\]

`R` is dimensionless; `r` is parity bits/codeword. Source: `green_ecc_phy/study.py::payload_normalization` and registry manifests. Exact functional range: registered binary systematic codes. Example: `(72,64)` gives `R=64/72=0.888888…` and `r=8`; one 64-bit information word becomes 72 encoded bits.

With parity-check matrix \(H\in GF(2)^{r\times n}\) and received vector \(y\),

\[
s = Hy^T \pmod 2.
\]

`s` is an `r`-bit syndrome. Source: generated matrices and adapters in `green_ecc_phy/matrices.py`/`adapters.py`. The syndrome identifies an action only through a specific decoder policy; collisions can produce abstention or silent miscorrection.

## Exact correction and detection universes

For class \(c\) with exact error-mask set \(\mathcal E_c\), the measured correction fraction is

\[
f_{c,\mathrm{corr}} = \frac{|\{e\in\mathcal E_c: D(E(0)\oplus e)=0\}|}{|\mathcal E_c|}.
\]

The DUE and SDC fractions replace the numerator with detected/abstained or silently wrong outcomes. Fractions are dimensionless and exact. Source: `green_ecc_phy/study.py::_pattern_summary` and `green_ecc_phy/verification.py`. Applicability requires the recorded data-independence proof or explicit payload enumeration.

Example: bounded SEC-DAEC has `f_corr=10/63` for its adjacent-double data universe and `f_SDC=53/63`; a family-level correction guarantee is disproved.

## Multi-ECC residual probabilities

For fault-profile class probabilities \(p_c\) and exact outcome fractions \(f_{c,o}\), the per-codeword outcome probability is

\[
p_{o,cw}=\sum_c p_c f_{c,o}.
\]

If a 64-bit payload uses \(m=\lceil64/k\rceil\) independent codewords, the study maps it to

\[
p_{o,64}=1-(1-p_{o,cw})^m.
\]

Probabilities are per access; evidence is `analytical_model` because the class PMF is assumed, while outcome fractions are exact. Source: `green_ecc_phy/study.py::_candidate_metrics`. The approximation treats codeword outcomes as independent and uses the fault-profile universe defined in `software-simulation-study-v1.json`.

## Hazucha–Svensson-style SER/FIT

The legacy reliability command implements

\[
FIT_{node}=C\,\Phi_{rel}\,A_{sens}\exp(-Q_{crit}/Q_s).
\]

`C` is a fitted technology constant, `Φ_rel` relative neutron flux (dimensionless), `A_sens` sensitive area in µm², and `Qcrit`/`Qs` are femtocoulombs; output is failures per \(10^9\) node-hours (FIT/node). Source: `ser_model.py::ser_hazucha`. This is an analytical fitted model, not radiation measurement. Altitude/latitude scaling is an empirical approximation or user override.

Worked interface (verified help; numerical inputs are illustrative):

```text
python eccsim.py reliability hazucha --qcrit 1.0 --qs 0.5 --area 1.0 --flux-rel 1.0
```

The same module includes a four-state voltage proxy, `SER=(ε1 ε2 ε3 ε4)/VDD^k` and `BER=1-(1-SER)^nodes`, valid only for `VDD >= 0.4 V`. It is separate from the multi-ECC fault grid.

## MBU probability model

`mbu.py` supplies tunable adjacent/non-adjacent PMFs for two- and three-bit upsets. A severity preset provides `p2` and `p3`; geometry sets an adjacent probability to zero if word or bitline width cannot contain that burst. Units are probabilities conditional on upset multiplicity. The presets are deliberately analytical and are not silicon-derived.

## Scrubbed residual FIT

The legacy `fit.py::compute_fit_post` combines uncovered instantaneous MBU rates with accumulated independent double errors:

\[
FIT_{post}=\sum_{m,a} FIT_{m,a}[1-C_{ECC}(m,a)]
+ {w\choose2}\lambda_1^2\tau\,10^9[1-C_{ECC}(2,nonadj)].
\]

`w` is bits/word; `λ1=FIT_bit/10^9` is upsets/hour/bit; `τ` is scrub interval in hours; `C_ECC` is dimensionless coverage. Output is FIT/word. Longer `τ` increases accumulated-double exposure. This legacy coverage factory contains nominal family assumptions, including TAEC/SEC-DAEC aliases; those assumptions must not override the multi-ECC exact negative verification.

## Voltage and temperature

In the multi-ECC scenario study, voltage scales dynamic bit/XOR energy with \(V^2\). Temperature linearly interpolates a configured leakage multiplier between 25 °C and 85 °C. Neither changes exact decoder behavior. In the legacy leakage model, current density approximately doubles every 15 °C. These are model assumptions with bounded configured ranges, not measurements.

## Notation

| Symbol | Meaning | Unit/evidence |
|---|---|---|
| `n`, `k`, `r` | Codeword, information and parity bits | bits, exact |
| `H`, `s` | Parity-check matrix and syndrome | GF(2), exact |
| `p_c` | Fault-class probability | probability/codeword access, analytical input |
| `p_SDC`, `p_DUE` | Residual silent/detected outcome probability | probability/64-bit access, analytical from exact fractions |
| FIT | Failures in time | failures/10⁹ hours, analytical unless measured source supplied |
| `τ` | Scrub interval | hours or seconds as stated |
| `C_ECC` | Coverage function | dimensionless analytical/verified mapping |
