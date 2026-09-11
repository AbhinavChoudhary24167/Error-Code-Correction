# Slew provenance classification

| Design | A | B | C | D | E | F | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| U0 original | 0 | 1 | 64 | 0 | 0 | 0 | 65 |
| E0 original | 3 | 4 | 72 | 0 | 1 | 0 | 80 |

Class A is the single E0 standard-cell net `_055_` reported at three pins. Class B is U0 data `rstb`, E0 data `rstb`, data `din[56:57]`, and ECC `rstb`. Class C is every SRAM output (64 U0; 64 data plus 8 ECC in E0). Class E is the E0 data-macro clock input. There are no Class-D primary-IO rows and no Class-F rows whose rule source cannot be located.

The 136 original Class-C rows also carry a secondary upstream provenance defect: the explicit inherited 0.04 ns rule contradicts their own output tables. They remain Class C because the violating object is an SRAM output; no warning is waived. After repair E0 has B2/C72/E1 and U0 remains B1/C64. The explicit, out-of-characterization-range B/E rows prevent the provenance-limited exception.
