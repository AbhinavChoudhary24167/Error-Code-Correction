# Gate 07 reliability-semantics freeze

## Proven guarantees

| Implementation | W1 | W2 |
|---|---|---|
| Conventional SECDED, both microarchitectures | 72/72 corrected | 2556/2556 detected as DUE |
| Hsiao SECDED | 72/72 corrected | 2556/2556 detected as DUE |
| BCH `(78,64,t=2)` | 78/78 corrected | 3003/3003 corrected |

## Exhaustive weight-3 observations

| Code semantics | Coordinate universe | Total | SDC | DUE |
|---|---|---:|---:|---:|
| Conventional SECDED | all `C(72,3)` canonical masks | 59,640 | 45,304 (`809/1065`) | 14,336 (`256/1065`) |
| Hsiao SECDED | all `C(72,3)` canonical masks | 59,640 | 34,164 (`2847/4970`) | 25,476 (`2123/4970`) |
| BCH | all `C(78,3)` canonical masks | 76,076 | 13,780 (`265/1463`) | 62,296 (`1198/1463`) |

Conventional SECDED and Hsiao do **not** have different W3 universe sizes: both enumerate all 59,640 three-coordinate masks. Their displayed fraction denominators differ only because the raw count ratios reduce by different greatest common divisors. BCH has 76,076 masks because its codeword has 78 coordinates rather than 72.

These W3 values are observations outside the guaranteed correction universe. They are not FIT, SER, field reliability, operational failure probability, operational SDC rate, or a W3 correction guarantee. No fault distribution or physical bit/interleave mapping is applied.
