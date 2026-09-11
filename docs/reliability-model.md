# Reliability model

GREEN separates conditional logical response from physical event occurrence.

For an error class or mask `m`, exact verification provides

```text
P(o | m, a) = N(o, m, a) / N(m, a)
```

where `o` is a service outcome (correct, corrected, detected-uncorrectable, silent corruption, or implementation-specific status), `a` is a bound implementation/decoder policy, and `N` is an exact count over the declared finite universe. This is dimensionless and implemented for registered verification universes.

An absolute outcome rate would additionally require

```text
lambda_o [events/hour] = sum_m lambda_m [events/hour] * P(o | m, a)
FIT_o [failures/10^9 device-hours] = 10^9 * lambda_o
```

The conditional factor is available for selected logical classes. A qualified physical `lambda_m` for the routed SRAM population is not; therefore physical SDC, DUE, SER, and FIT are blocked.

## Scrubbing model

For a Poisson upset rate `lambda` and scrub interval `T_s` in hours, the assumed count probability is

```text
P(K=k) = exp(-lambda*T_s) * (lambda*T_s)^k / k!
```

The command-line reliability report combines declared assumptions such as Qcrit, sensitive area, flux multiplier, capacity basis, word width, ECC family, and scrub interval. Its result is a model output, not a radiation measurement. Run `python eccsim.py reliability report --help` before supplying units and basis.

## Fault populations

- SBU: one flipped logical bit in the declared codeword.
- DBU: two flipped logical bits; “arbitrary” and “adjacent” are distinct universes.
- MBU: a declared multi-bit topology or PMF. Logical adjacency is not physical adjacency unless a verified mapping establishes it.

Interleaving benefits require a physical-to-logical bit map and a physical event footprint distribution. Both remain blocked for the current absolute reliability claim.

## Implemented, modelled, and planned

| State | Content |
|---|---|
| Implemented/validated | Registered code identity checks, exact declared-universe verification, retained counterexamples, seeded simulation |
| Implemented as conditional model | Qcrit/flux/area/scrub parameter calculations and logical fault PMFs |
| Blocked | Routed-population physical SDC/DUE/SER/FIT, measured Qcrit, radiation calibration, interleaver reliability |

The [evidence model](evidence-model.md) controls whether any particular result may be used in a claim.
