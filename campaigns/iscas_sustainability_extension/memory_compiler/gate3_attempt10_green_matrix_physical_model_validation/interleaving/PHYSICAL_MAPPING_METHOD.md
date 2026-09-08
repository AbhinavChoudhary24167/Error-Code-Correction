# Physical interleaving and reliability

Classification: PHYSICAL_TOPOLOGY_MAPPING_INCOMPLETE. I0 macro placement is
extracted from each of the five frozen final DEFs and SRAM dimensions from LEF.
SPICE explicitly connects storage instances to electrical wordlines/bitlines:
data = 64 rows x 256 columns, ECC = 32 rows x 64 columns. This is physical memory
organization evidence; it is not a qualified bitcell coordinate/address map.
The data and parity macros use different column multiplexing factors (m4/m8).
I0 means no added external interleaver, not zero intrinsic column multiplexing.

I1/I2 specify two/four physical macro banks and a bijective word-group/bit-lane
transpose. These are implementable architecture contracts, not completed layouts.
They require RMW/group buffering because the data macro has byte write masks.
Their exact extra macro area budgets use unchanged LEF dimensions. Controller
area, routing, latency and energy overhead remain NOT_MEASURED. No improvement
in adjacent-upset coverage is claimed until internal bit placement is joined.

The optional --geometry/--events adapter requires a complete map with word/bit,
bank, macro instance, GDS instance path, x/y in um and source hashes. It rejects
missing/stale provenance, incomplete coverage, duplicate logical bits, unknown
upset sites and invalid radii. A disk or explicit-cell fault maps to cell IDs,
then per-codeword masks, then the repository's existing Hsiao decoder. SDC checks
the returned payload against truth even when correction_applied is asserted.
This creates conditional outcomes; calibrated event probabilities and time are
still required for SER, FIT, SDC/DUE rates and physical coverage fractions.

Logical SBU/all-DBU/consecutive-3/consecutive-4 controls and persistent fault
scrubbing examples are explicitly separate. They are not spatial DBU/MBU tests.
Scrub writeback follows the real correction flag and can preserve a miscorrection;
the model never uses an oracle to decide that hardware should scrub. Periodic
intervals are in functional steps until an access/time model is supplied.

PracticalSRAMSimulator.cpp has index-based adjacent/row/column models; these are
not imported as physical xy geometry. The registered green_ecc_phy decoder is
reused because it identifies the exact frozen Hsiao (72,64) implementation.
Existing latitude/altitude and Qcrit scaling APIs remain unchanged and available;
their empirical defaults do not calibrate this macro's physical upset process.

Original/research-corrected Liberty have identical logic and macro geometry;
no reliability distinction is inferred from a constraint-only diagnostic copy.
Energy/carbon and GREEN rankings remain gated on qualified source evidence.
