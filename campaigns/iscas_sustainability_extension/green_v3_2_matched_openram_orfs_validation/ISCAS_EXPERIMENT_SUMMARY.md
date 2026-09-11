# ISCAS experiment summary

## Experimental Setup

The included population is U0, SECDED, HSIAO_SECDED, BCH_78_64_T2. Every design stores 256 ×
64 user payload bits. Physical redundancy is included rather than normalized
away. The pinned flow is ORFS `56496f3980fb6e9e58f10c8aea4a98949c0fe5f2`
using OpenROAD `26Q3-1080-gab6fd26351`, SKY130HD TT/25 °C/1.8 V, common 10 ns
and 5 ns constraints, and seeds 11, 13, 17, 19, and 23. Fresh OpenRAM status
is `TIMEOUT`; inherited SRAM22 macros are explicitly
separate evidence.

## Functional Validation

Four architectures pass fresh deterministic RTL and memory-model regressions.
SEC-DAEC fails its declared adjacent-pair space and is excluded. Exact/formal
depth is identified per architecture in `ARCHITECTURE_AUDIT.json`.

## Physical Implementation Results

Completed run records: 40; clean external routes:
40; GDS outputs: 40.
Setup constraints are met in 20 runs and both
setup and hold are met in 14 runs;
RTL-to-GDS completion is not described as timing closure.
Multi-seed area, cell count, wirelength, via, timing, vectorless power, and
available congestion statistics are in `SEED_STATISTICS.json` and CSV. With
only five seeds, intervals are descriptive.

| Architecture | Clock ns | Total instance area µm² | Wirelength µm | Vias | Setup WNS ns | Vectorless power W |
|---|---:|---:|---:|---:|---:|---:|
| U0 | 10 | 206791 ± 0 | 21082.4 ± 7.47 | 1223.2 ± 45.8 | 3.96271 ± 0.00445 | 0.000801186 ± 1.6e-07 |
| SECDED | 10 | 273980 ± 46 | 73141.2 ± 1.12e+03 | 5595.2 ± 18.7 | 0.433752 ± 0.18 | 0.00228818 ± 2.05e-05 |
| HSIAO_SECDED | 10 | 274217 ± 36 | 76134 ± 164 | 6063 ± 45.8 | 0.677443 ± 0.146 | 0.00197349 ± 6.93e-06 |
| BCH_78_64_T2 | 10 | 379596 ± 1.27e+03 | 296299 ± 1.64e+03 | 36519.6 ± 277 | -11.112 ± 0.143 | 0.0612421 ± 0.00224 |
| U0 | 5 | 206693 ± 0 | 21055.2 ± 7.66 | 1191.2 ± 45.8 | 0.288042 ± 0.00431 | 0.00159469 ± 3.1e-07 |
| SECDED | 5 | 277136 ± 184 | 75788.8 ± 316 | 6149.6 ± 24.2 | -3.18143 ± 0.0783 | 0.00450958 ± 2.46e-05 |
| HSIAO_SECDED | 5 | 277699 ± 244 | 78549.4 ± 718 | 6370 ± 9.92 | -2.83509 ± 0.0227 | 0.00395011 ± 9.05e-06 |
| BCH_78_64_T2 | 5 | 380694 ± 624 | 295151 ± 2.96e+03 | 36768.2 ± 165 | -15.7141 ± 0.136 | 0.112983 ± 0.0103 |

## Evidence Qualification

Analytical/formal evidence remains E3 only where independently established.
Fresh routed quantities are E4. Vectorless power is `E4_DIAGNOSTIC`, not E5.
Missing reliability, Qcrit, manufacturing, lifecycle, and activity-complete
evidence remains blocked.

## GREEN Analysis

The additive adapter supplies 40 new M_E records and
8 aggregate M_P records. It supplies no M_S rule and
the combined additive view is M_E=601,
M_P=10, and M_S=2.
It does not alter v3.2 admissibility. Qualified Pareto remains blocked and the
global result remains `NO_GLOBAL_WINNER_QUALIFIED`.

## Limitations

There is no silicon validation, particle-beam validation, qualified physical
event rate, physical FIT, Qcrit, exact bitcell-to-codeword topology map, E5
energy, or qualified SKY130 manufacturing inventory.
