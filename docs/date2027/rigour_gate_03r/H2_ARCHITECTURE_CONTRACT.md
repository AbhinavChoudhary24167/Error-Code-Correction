# Gate 03R H2 architecture contract

Contract ID: `gate03r-h2-exact-identity-v1`. Frozen before Gate 03R RTL implementation.

## Mathematical identity

Both candidates implement `extended-hamming-secded-72-64-v1`, matrix identity
`40bc866e1a85aa0d8597f49fa6e97bc29a5e64d75631e13ba90ec2befcd3f749`.
Native codeword bits 0 through 70 are one-based positional Hamming locations 1
through 71 and native bit 71 is the overall even-parity bit. Data ordering,
parity placement, correction action, corrected codeword, and status semantics are
identical. Hsiao is a different mathematical identity. The bounded SEC-DAEC and
TAEC policies remain excluded controls.

## Implementations

| Implementation | Organization | Encoder latency | Decoder latency | Initiation interval |
| --- | --- | ---: | ---: | ---: |
| `secded-rtl-combinational-72-64-v1` | Existing parallel combinational codec | 0 | 0 | 1 |
| `secded-rtl-pipelined-72-64-v1` | Balanced/factored parity and syndrome networks with an internal register cut | 2 | 2 | 1 |

The pipelined production interface uses `clk_i`, `valid_i`, native payload or
codeword input, `valid_o`, and native results. It has no backpressure or reset.
Outputs are meaningful only when `valid_o` is asserted. Characterization shells
use the same input/output register convention for both candidates, with proof
alignment accounting for the declared core latency.

## Physical distinction

The existing candidate is one combinational cone. The new candidate registers
the first parity/syndrome phase and accepts a new word every cycle. This is a
normal high-throughput timing architecture, not a renamed or deliberately poor
strawman: it trades sequential area and latency for shorter combinational paths
and bounded activity per pipeline stage.

H2 is unresolved unless canonicalized generic and SKY130HD-mapped core graphs
differ after names and common characterization shells are removed. The evidence
must show different sequential cut sets and graph hashes. No `keep` attribute or
other artificial synthesis obstruction may be used to manufacture a difference.

## Exact behavior

- Clean input: data and codeword pass unchanged; all status flags are zero.
- Correctable single-bit input: corrected data and codeword equal the clean word;
  `detected=1`, `corrected=1`, `uncorrectable=0`.
- Detected double-bit input: no correction is applied; `detected=1`,
  `corrected=0`, `uncorrectable=1`.
- The new decoder must be universally equivalent to the existing conventional
  decoder for every 72-bit received word after temporal alignment.

