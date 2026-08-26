# Gate 04 power-precision adjudication

Status: `ERROR_CLASS_POWER_DIFFERENCE_RESOLVED_BELOW_PRIOR_SERIALIZATION_PRECISION`

This adjudication was completed before any Gate 04 final physical run. It reads the sealed Gate 03F reports and VCDs but does not rerun or modify Gate 03F.

## Reporting pipeline

- The qualified OpenSTA script emits a text report with `report_power -digits 12` and a native JSON report from `report_power -format json`.
- The text `Total` row retains twelve digits after the decimal in scientific notation.
- The native JSON retains only about three significant digits. Gate 03F analysis used that rounded JSON, which hid the small differences between error classes.
- Gate 04 preserves both outputs but treats the 12-digit text `Total` row as the authoritative extraction source. The VCDs, activity propagation, ODB, SDC, SPEF, corner, and power method are unchanged.

## Raw Gate 03F evidence

| Design | Trace class | Internal W | Switching W | Leakage W | Total W |
|---|---|---:|---:|---:|---:|
| Conventional SECDED | no error | 6.786616984755e-03 | 7.788169197738e-03 | 7.300083204598e-09 | 1.457479409873e-02 |
| Conventional SECDED | single error | 6.786080542952e-03 | 7.787120062858e-03 | 7.300063664673e-09 | 1.457320805639e-02 |
| Conventional SECDED | double error | 6.786448415369e-03 | 7.787812035531e-03 | 7.300062332405e-09 | 1.457426790148e-02 |
| BCH(78,64,t=2) | no error | 4.246733486652e-01 | 4.240913391113e-01 | 2.355694661560e-08 | 8.487646579742e-01 |
| BCH(78,64,t=2) | single error | 4.246717095375e-01 | 4.240891933441e-01 | 2.355699102452e-08 | 8.487609028816e-01 |
| BCH(78,64,t=2) | double error | 4.246803224087e-01 | 4.241002500057e-01 | 2.355696793188e-08 | 8.487805724144e-01 |

The native JSON rounds the SECDED totals to `1.46e-02 W` and the BCH totals to `8.49e-01 W`, making each triplet appear identical.

## Activity evidence

All traces have the same 400,025 total input value-change events because every accepted vector changes on the same schedule. Bit transitions differ because the decoder codewords differ:

| Family | No-error non-clock bit transitions | Single-error | Double-error |
|---|---:|---:|---:|
| Conventional SECDED | 6,797,261 | 6,796,329 | 6,796,735 |
| Hsiao SECDED | 6,797,821 | 6,797,849 | 6,797,341 |
| BCH(78,64,t=2) | 7,098,467 | 7,098,579 | 7,099,009 |

The full-precision OpenSTA internal and switching totals also differ while the design, clock, and corner are fixed. This establishes that propagated activity differs across error classes. `report_activity_annotation` reports identical annotation coverage counts because it reports sources/coverage, not equal toggle rates.

## Prospective interpretation rule

Gate 04 will:

1. retain all three activity classes separately;
2. parse and serialize the 12-digit text totals without reducing precision;
3. retain the rounded native JSON only as diagnostic evidence;
4. make no claim that a small resolved difference is practically important merely because it is numerically resolvable;
5. never average the incompatible activity classes or apply an assumed field error-rate weighting.

These remain post-route OpenSTA implementation/activity estimates, not silicon measurements.
