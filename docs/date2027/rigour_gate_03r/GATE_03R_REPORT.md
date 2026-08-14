# GREEN-ECC DATE 2027 Gate 03R report

## Verdict

`REMEDIATION_FAILED`

The original 11 August 2026 AoE deadline was missed and is recorded without backdating. The authorized replacement milestones are environment freeze by 15 August, Gate 03R completion by 19 August, and separate Gate 03 re-entry by 21 August 2026 AoE.

## Results

The exact SECDED implementations are `secded-rtl-combinational-72-64-v1` and `secded-rtl-pipelined-72-64-v1`, both bound to `extended-hamming-secded-72-64-v1`. Exact encoder and universal decoder equivalence pass after applying Gate 02's frozen canonical-to-positional coordinate map. Generic normalized structures are distinct and the pipelined cores retain registers; SKY130HD-mapped graph comparison is blocked.

The independent BCH reconstruction produced matrix hash `d518cab40c77da302afecab0e8199f3f0c4e0b2c095660d5d0df8a1e2dae4e89`. All 3,082 required weight-0/1/2 jobs passed with a 64-bit symbolic payload and zero counterexamples. All 76,076 zero-payload weight-3 masks plus 1,024 deterministic payload/mask samples were characterized against the frozen Gate 02 reference with no weight-3 correction claim.

All eight requested generic synthesis tops passed. This is structural evidence only. No PPA, timing, energy, FIT, carbon, selector, figure, or publication result was generated.

Final regressions passed: `make`, `make test` (381 passed, 3 warnings), and `python3 -m pytest -q` (383 passed). Both working-tree and staged whitespace checks passed.

## Mechanical blockers

1. WSL2 Ubuntu 24.04 and Docker Engine CE were not installed because the UAC elevation was cancelled. The repository and previous-gate bytes were unchanged.
2. Therefore `openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e`, the full official ORFS commit for `56496f398`, internal OCI revision, `flow`/`sky130hd` hashes, Liberty/LEF bytes, and the pinned corner could not be reconciled.
3. The supplied `sky130hd/gcd` RTL-to-GDS smoke and all candidate SKY130HD technology-mapped synthesis runs were not executed.

## RTL runtime note

Icarus elaborated the new RTL but its copied Windows runtime did not terminate during bounded attempts. Those failures are preserved. The independent Verilator route subsequently built and executed both the pipelined SECDED and BCH compiled smoke tests successfully.

Because every original acceptance criterion is mandatory, Gate 03 re-entry is not authorized by this result. If a complete re-entry has not passed by the 21 August hard stop, the paper-core verdict is `NO_GO_FOR_DATE_2027_REGULAR_PAPER_CORE`.
