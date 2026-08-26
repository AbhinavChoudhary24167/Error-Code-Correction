# Gate 06 DATE-ready paper tables

## Primary hardware table

| Architecture | Protection guarantee | Area µm² | ΔArea vs comb | Fmax MHz | 10 ns | Wirelength µm | Power W | Achievable energy/op pJ | Latency cycles |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|
| Conventional SECDED, combinational | W1 correct; W2 detect | 18644.1 | +0.000% | 243.881 | MEETS_10NS | 44609 | 0.0145747941 | 145.762516 | 1 |
| Conventional SECDED, pipelined | W1 correct; W2 detect | 25486.9 | +36.702% | 355.849 | MEETS_10NS | 49992 | 0.0110745076 | 110.756151 | 3 |
| Hsiao SECDED | W1 correct; W2 detect | PPA_UNAVAILABLE | PPA_UNAVAILABLE | PPA_UNAVAILABLE | PPA_UNAVAILABLE | PPA_UNAVAILABLE | PPA_UNAVAILABLE | PPA_UNAVAILABLE | 1 |
| BCH (78,64,t=2) | W1/W2 correct | 57303.7 | +207.356% | 67.6566 | FAILS_10NS | 183332 | 0.848764658 (diagnostic) | TARGET_CLOCK_INFEASIBLE | 1 |

Power is the no-error post-route OpenSTA estimate. BCH power is retained only as a target-constraint diagnostic. SECDED energy values are steady-stream energy per accepted comparison transaction under the verified Gate 05 normalization.

## Reliability table

| Architecture / ECC | Parameters | W1 behavior | W2 behavior | Weight-3 observations | Weight-3 SDC | Weight-3 DUE | Caveat |
|---|---|---|---|---:|---:|---:|---|
| Conventional SECDED, combinational | (72,64) | 72/72 corrected | 2556/2556 DUE | 59640 | 45304 (809/1065) | 14336 (256/1065) | shared code semantics |
| Conventional SECDED, pipelined | (72,64) | 72/72 corrected | 2556/2556 DUE | 59640 | 45304 (809/1065) | 14336 (256/1065) | exact-equivalent architecture |
| Hsiao SECDED | (72,64) | 72/72 corrected | 2556/2556 DUE | 59640 | 34164 (2847/4970) | 25476 (2123/4970) | PPA_UNAVAILABLE |
| BCH | (78,64,t=2) | 78/78 corrected | 3003/3003 corrected | 76076 | 13780 (265/1463) | 62296 (1198/1463) | weight-3 observation only |

Weight-3 columns are exhaustive canonical-coordinate observations, never operational probabilities, FIT/SER values, or correction guarantees.

## Effect-size table

| Comparison | ΔArea | ΔCells | ΔWirelength | ΔFmax | Timing deficit | ΔPower | ΔEnergy/op |
|---|---:|---:|---:|---:|---:|---:|---:|
| Pipelined vs combinational SECDED | +36.702% | +28.255% | +12.067% | +45.911% | 0 ns | -24.016% | -24.016% |
| BCH vs combinational SECDED | +207.356% | +243.732% | +310.975% | -72.258% | +4.78052 ns | NOT_APPLICABLE | TARGET_CLOCK_INFEASIBLE |
| BCH vs pipelined SECDED | +124.836% | +168.008% | +266.723% | -80.987% | +4.78052 ns | NOT_APPLICABLE | TARGET_CLOCK_INFEASIBLE |
