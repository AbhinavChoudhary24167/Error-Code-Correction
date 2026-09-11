# Attempt10 activity and energy evidence

Classification: **RTL_ACTIVITY_COMPLETE_ENERGY_NOT_QUALIFIED**.

Eight deterministic workload families run the unchanged Attempt09 U0 and E0 physical
RTL tops against unchanged SRAM22 functional Verilog. Serialized operation traces,
addresses, payloads, clock and data fault masks are identical for each matched pair.
All 256 locations and the read output are initialized before measurement. The
measurement window contains exactly cycles × 10 ns, with initialization excluded.
CE is low in the idle workload but the clock continues toggling; this is not a
clock-gated or pure leakage experiment. Counts and payload/flag checks must pass.
No-error and all read/write operations are checked against the existing registered
Hsiao encoder/decoder. SDC is determined by comparison with the original payload,
not by trusting the correction flag. The idle payload input still toggles, so this
trace measures inactive memory with a live upstream data bus.

Faults flip actual behavioral SRAM mem[] data bits before the read edge and restore
them at the next falling edge. They represent isolated transient storage faults,
not persistent radiation rates or implemented scrubbing. The physical top ties
qualification_fault_mask off; no extra injection XOR hardware is simulated.
The injected DBU/MBU trace uses 2/3/4 logically consecutive payload bits. Physical
adjacency is unproven and is never inferred from Verilog bit numbering.

The VCD includes tb.dut and encoder, decoder and macro-interface signals. SRAM
internal transistors and analog switching are absent from the functional model.
The manifest reports raw and date-independent VCD hashes, unknown events, signal
count, duration, source hashes and observed correction/DUE/SDC read counts.

A seed-11 upstream-original post-route diagnostic has now read matched final ODB,
Liberty, SDC and SPEF artifacts and annotated the read-dominant trace at tb/dut.
Its coverage and tool estimates are recorded in POSTROUTE_ACTIVITY_DIAGNOSTIC.json.
Coverage is only 48.68% for U0 and 4.35% for E0; unmatched pins use default
activity, the VCD is RTL rather than glitch-aware gate activity, and the macro
power model has not been independently validated. The diagnostic therefore does
not qualify energy-per-access or architecture comparisons.

Qualification still requires five seeds for every original/corrected view,
retained annotated/unannotated net lists, and coverage reported separately for
clocks, inputs, sequential outputs, ECC logic and macro boundary/internal power
arcs. RTL-to-gate mapping and inferred/default toggles must be explicit. Sparse
RTL net annotation alone cannot qualify power or glitch energy.

Disjoint power groups are SRAM macro dynamic, ECC encoder, ECC decoder,
control/interconnect dynamic, and leakage. Their sum must equal the total within
declared numerical tolerance; shared nets must not be double counted. A validated
macro internal-power model, including read/write conditions and leakage PVT, is
required. Missing groups remain NOT_MEASURED.

For a measured window T, E_total = integral P(t)dt (or average P × T).
E_access = E_total/(N_read + N_write) only for a nonzero access count; idle energy
is reported as joules/window and leakage power, never divided by zero. Individual
E_read and E_write need isolated/matched measurements or a full-rank operation
mix regression with uncertainty; one aggregate power value cannot identify both.
E_encode and E_decode use attributed encoder/decoder energy and counted valid
operations. E_correct is incremental matched faulty versus clean decoder energy
per actual corrected read; subtract identical idle/background activity. Report
raw workload-average energy separately from these incremental quantities.

No numeric energy or carbon claim is supported by these RTL activity traces alone.
Original Liberty, research-corrected diagnostic Liberty and counterfactual physical
power results must stay separate. Existing postroute default-activity power is
not reused as if it belonged to these workloads. Historical Gate-3 remains FAIL.
