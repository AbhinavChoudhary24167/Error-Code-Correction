# Gate 03R BCH(78,64,t=2) contract

Contract ID: `gate03r-bch-78-64-t2-exact-v1`. Frozen before Gate 03R BCH RTL
implementation. The values below are provisional Gate 02 inputs until the
independent Gate 03R reconstruction passes.

## Frozen construction

- Mathematical code: `shortened-bch-78-64-t2-v1`.
- Gate 02 reference implementation: `shortened-bch-78-64-t2-v1-reference-decoder`.
- Parent: primitive narrow-sense binary BCH `(127,113,t=2)` over GF(2^7).
- Field polynomial: `x^7 + x + 1`, integer `0x83`; polynomial-basis bit 0 is the
  constant coefficient and `alpha` is integer 2.
- Defining roots: `alpha^1` through `alpha^4`; cyclotomic cosets
  `{1,2,4,8,16,32,64}` and `{3,6,12,24,48,96,65}`.
- Generator: `x^14+x^12+x^10+x^6+x^5+x^4+x^3+x^2+1`, integer 21629,
  binary `101010001111101` printed from degree 14 to degree 0.
- Shortening: parent data coordinates 64 through 112 are fixed to zero and
  parent native codeword coordinates 78 through 126 are removed.
- Canonical codeword: payload bits 0 through 63 followed by parity bits 64
  through 77. Canonical coordinate exponents are `14..77,0..13`.
- Frozen matrix SHA-256: `d518cab40c77da302afecab0e8199f3f0c4e0b2c095660d5d0df8a1e2dae4e89`.

The historical degree-12 cyclic RTL and generator `1000111101011` are prohibited
inputs and must not appear in a Gate 03R synthesis file list.

## Production interfaces and status

The encoder is combinational `data_i[63:0] -> codeword_o[77:0]` and emits
`{parity[13:0],data_i[63:0]}`. The decoder is combinational and emits decoded
data, corrected codeword, packed syndromes, correction mask, and explicit
`detected`, `corrected`, and `uncorrectable` flags.

Packed syndrome bits `[6:0]`, `[13:7]`, `[20:14]`, and `[27:21]` are `S1`,
`S2`, `S3`, and `S4`. The decoder computes the four shortened syndromes, solves
`sigma1=S1` and `sigma2=(S3 + S1^3)/S1`, performs a 78-coordinate Chien search,
and rechecks all four syndromes after correction.

- No error: all flags zero; outputs equal the input codeword and its data field.
- Corrected: `detected=1`, `corrected=1`, `uncorrectable=0`.
- Uncorrectable: `detected=1`, `corrected=0`, `uncorrectable=1`, correction mask
  zero, and received codeword/data pass through as explicitly invalid results.
- No fault-injection port or XOR belongs to production or characterization RTL.

## Proof boundary

The encoder requires symbolic full equivalence, independent linearity, zero,
all 64 basis messages, explicit mapping, and deterministic random vectors. The
decoder requires a symbolic 64-bit payload for each of all 3,082 weight-0/1/2
masks. Weight-3 observations are characterization only and cannot support a
correction claim.

