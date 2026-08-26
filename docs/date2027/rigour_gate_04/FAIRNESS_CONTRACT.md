# Gate 04 fairness contract

All candidates carry 64 useful bits per accepted operation at initiation interval one. Encoder and decoder channels are independent, share the same registered boundary policy, receive identical useful schedules, use the same fractional I/O delays and output load, and expose no backpressure, test mux, or synthesizable fault-injection port. A common registered codeword-echo output keeps every decoder input-boundary bit physically observable in candidates and references; it is wrapper overhead, not codec functionality. Reset is a synchronous active-low boundary reset asserted for six clocks; invalid pipeline contents are ignored until valid emerges.

Combinational SECDED, Hsiao, exact BCH, and width-matched references have one boundary cycle. The pipelined same-code SECDED retains its two internal encoder/decoder stages and has three total boundary-to-boundary cycles. It must not be retimed into the combinational architecture.

The 72-bit and 78-bit boundary-only references are separately placed and routed at every clock and paired seed. Codec-only estimates may be derived by explicit reference subtraction, with negative or unsupported decompositions reported unresolved. Pipeline registers, parity/storage bits, wrapper overhead, and codec logic remain separate. Memory macro, controller, metadata, scrub, and migration costs are unresolved unless independent common evidence exists.

All power is post-route OpenSTA tool estimation from identical input activity traces. Direct VCD annotation and unannotated pin counts are retained; propagation is not mislabeled as measured internal switching. Physical adjacency, Qcrit, fault probabilities, scrub intervals, and workload distributions are assumptions.
