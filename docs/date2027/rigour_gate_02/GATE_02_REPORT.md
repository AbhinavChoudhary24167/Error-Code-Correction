# GREEN-ECC DATE 2027 Publication-Rigour Gate 02

## Executive verdict

Gate 02 is an additive mathematical/functional audit. Its final verdict is **CONDITIONAL PASS TO GATE 03** only for implementations explicitly listed as eligible; negative controls remain excluded. This is not publication readiness or physical validation.

The built-in catalogue independently resolves to 15 codes, 17 implementations and 17 architectures. Expected comparison values were 15 and 17; they were not used to force reconciliation.

Status counts: `{"CONDITIONAL PASS": 2, "FAIL": 0, "NOT ASSESSABLE": 0, "PARTIAL": 1, "PASS": 12, "REJECTED": 2}`. Distance evidence: 14 exact, 1 designed bound, 0 unresolved. The verifier evaluated 886966 exact mask cases across frozen universes in 278.493 seconds.

Independent C++ BCH equivalence: **PASS**. Complete registered RTL differential: **NOT ASSESSABLE**. All five registered RTL designs compiled in the bounded attempt; two simulations timed out and three hit a host `vvp` access violation without scientific output. These paths are retained as `NOT ASSESSABLE`, never inferred passes.

## Adjacency definition

Primary noncircular adjacency spans every logical stored codeword coordinate: data-data, data-parity, parity-data and parity-parity wherever present. An n-coordinate word has n-1 adjacent pairs and n-2 adjacent triples. Historical data-only adjacency is reported separately. Circular adjacency is a separate, undeclared universe. None is physical adjacency before Gate 03.

## Distance and construction boundary

Every exact record checks rank(H)=r, all 2^r dual selectors and distinct words, exact integer MacWilliams coefficients, non-negativity, 2^k primal sum, zero coefficients below d, and an explicit lexicographically smallest meet-in-the-middle witness. The `(85,64,t=3)` BCH reference retains only designed d>=7. The historical degree-12 `(63,51)` cyclic candidate remains distinct and has exact negative evidence.

## Decoder metrics

`detection_fraction` is safe detection coverage `(CORRECTED + DUE) / total_masks`; it never counts miscorrections. Raw detected/corrected/uncorrectable flags remain in witness records. `correction_fraction`, `due_fraction`, `safe_handling_fraction`, `detection_fraction`, and `sdc_fraction` are exact rational strings in per-implementation aggregates.

## Execution and portability verdict

Scientific-content hash portability is **PASS**: all ten LF/CRLF/CR, whitespace-significance, binary, migration and legacy-behaviour regressions pass, and the previously failing framework hash tests pass. The isolated focused suite completed with 37 passed tests.

The frozen-copy `make` build passed. `make test` completed with 355 passed and two `NOT ASSESSABLE` checks; the separate mandated `python3 -m pytest -q` run completed with 357 passed and the same two `NOT ASSESSABLE` checks. Both affected tests require repository Git metadata, which the permitted archive intentionally lacks: one received `repository_dirty = null`, and one received commit identity `unknown`. They are isolation limitations, not scientific failures, and neither command was retried. Raw transcripts are in `baseline/make.log`, `baseline/make_test.log`, `baseline/python3_pytest.log`, and `baseline/focused_tests.log`.

Compact artifact validation passed in its single 120-second attempt, including CSV headers and IDs, enums, complete aggregate arithmetic, evidence references, distance guards, witness coverage, artifact hashes and the independent recursive Gate-01 hash comparison.

The authorized change set is limited to `.gitattributes`, `Makefile`, the additive Gate-02 hashing/registry/verification/math modules and registry migration metadata, the catalogue builder's future scientific-hash behavior, the two Gate-02 runners, three focused test files, and `docs/date2027/rigour_gate_02/`. Gate 01 remains byte-identical to its recorded recursive hash manifest. No selector, physical model, existing result, figure, schema, public decode contract, or publication prose was changed.

## Gate-03 mathematical eligibility

- `forge-hotspot-8-4-v1-archived-table-decoder`
- `forge-spatial-hotspot-72-64-v1-archived-table-decoder`
- `forge-sram-portfolio-72-64-v1-geometry-filtered-joint-archived-table-decoder`
- `forge-sram-portfolio-72-64-v1-spatial-hotspot-joint-archived-table-decoder`
- `hsiao-generated-combinational-72-64-v1`
- `odd-column-secded-4-8-archived-table-decoder`
- `odd-column-secded-64-72-archived-table-decoder`
- `primitive-bch-63-51-t2-v1-reference-decoder`
- `safeforge-robust-72-64-mapping-v1-archived-table-decoder`
- `safeforge-robust-8-4-v1-archived-table-decoder`
- `secded-rtl-combinational-72-64-v1`
- `shortened-bch-71-64-t1-v1-reference-decoder`
- `shortened-bch-78-64-t2-v1-reference-decoder`
- `shortened-bch-85-64-t3-v1-reference-decoder`

## Known SDC/miscorrection implementations

- `cyclic-rtl-bounded-search-63-51-v1`
- `forge-hotspot-8-4-v1-archived-table-decoder`
- `forge-spatial-hotspot-72-64-v1-archived-table-decoder`
- `forge-sram-portfolio-72-64-v1-geometry-filtered-joint-archived-table-decoder`
- `forge-sram-portfolio-72-64-v1-spatial-hotspot-joint-archived-table-decoder`
- `hsiao-generated-combinational-72-64-v1`
- `odd-column-secded-4-8-archived-table-decoder`
- `odd-column-secded-64-72-archived-table-decoder`
- `primitive-bch-63-51-t2-v1-reference-decoder`
- `safeforge-robust-72-64-mapping-v1-archived-table-decoder`
- `safeforge-robust-8-4-v1-archived-table-decoder`
- `secdaec-rtl-bounded-72-64-v1`
- `secded-rtl-combinational-72-64-v1`
- `shortened-bch-71-64-t1-v1-reference-decoder`
- `shortened-bch-78-64-t2-v1-reference-decoder`
- `taec-rtl-bounded-72-64-v1`

Exact SDC-bearing universes:

- `cyclic-rtl-bounded-search-63-51-v1` — `cyclic-rtl-bounded-search-63-51-v1:weight-1`: 33/63 SDC
- `cyclic-rtl-bounded-search-63-51-v1` — `cyclic-rtl-bounded-search-63-51-v1:weight-2`: 1742/1953 SDC
- `cyclic-rtl-bounded-search-63-51-v1` — `cyclic-rtl-bounded-search-63-51-v1:weight-3`: 6066/39711 SDC
- `forge-hotspot-8-4-v1-archived-table-decoder` — `forge-hotspot-8-4-v1-archived-table-decoder:weight-2`: 15/28 SDC
- `forge-hotspot-8-4-v1-archived-table-decoder` — `forge-hotspot-8-4-v1-archived-table-decoder:weight-3`: 56/56 SDC
- `forge-hotspot-8-4-v1-archived-table-decoder` — `forge-hotspot-8-4-v1-archived-table-decoder:all-masks`: 210/256 SDC
- `forge-spatial-hotspot-72-64-v1-archived-table-decoder` — `forge-spatial-hotspot-72-64-v1-archived-table-decoder:weight-2`: 1014/2556 SDC
- `forge-spatial-hotspot-72-64-v1-archived-table-decoder` — `forge-spatial-hotspot-72-64-v1-archived-table-decoder:weight-3`: 32989/59640 SDC
- `forge-sram-portfolio-72-64-v1-geometry-filtered-joint-archived-table-decoder` — `forge-sram-portfolio-72-64-v1-geometry-filtered-joint-archived-table-decoder:weight-2`: 569/2556 SDC
- `forge-sram-portfolio-72-64-v1-geometry-filtered-joint-archived-table-decoder` — `forge-sram-portfolio-72-64-v1-geometry-filtered-joint-archived-table-decoder:weight-3`: 33980/59640 SDC
- `forge-sram-portfolio-72-64-v1-spatial-hotspot-joint-archived-table-decoder` — `forge-sram-portfolio-72-64-v1-spatial-hotspot-joint-archived-table-decoder:weight-2`: 455/2556 SDC
- `forge-sram-portfolio-72-64-v1-spatial-hotspot-joint-archived-table-decoder` — `forge-sram-portfolio-72-64-v1-spatial-hotspot-joint-archived-table-decoder:weight-3`: 34164/59640 SDC
- `hsiao-generated-combinational-72-64-v1` — `hsiao-generated-combinational-72-64-v1:weight-3`: 34164/59640 SDC
- `odd-column-secded-4-8-archived-table-decoder` — `odd-column-secded-4-8-archived-table-decoder:weight-3`: 56/56 SDC
- `odd-column-secded-4-8-archived-table-decoder` — `odd-column-secded-4-8-archived-table-decoder:all-masks`: 135/256 SDC
- `odd-column-secded-64-72-archived-table-decoder` — `odd-column-secded-64-72-archived-table-decoder:weight-3`: 45304/59640 SDC
- `primitive-bch-63-51-t2-v1-reference-decoder` — `primitive-bch-63-51-t2-v1-reference-decoder:weight-3`: 18900/39711 SDC
- `safeforge-robust-72-64-mapping-v1-archived-table-decoder` — `safeforge-robust-72-64-mapping-v1-archived-table-decoder:weight-2`: 685/2556 SDC
- `safeforge-robust-72-64-mapping-v1-archived-table-decoder` — `safeforge-robust-72-64-mapping-v1-archived-table-decoder:weight-3`: 6431/59640 SDC
- `safeforge-robust-8-4-v1-archived-table-decoder` — `safeforge-robust-8-4-v1-archived-table-decoder:weight-2`: 12/28 SDC
- `safeforge-robust-8-4-v1-archived-table-decoder` — `safeforge-robust-8-4-v1-archived-table-decoder:weight-3`: 31/56 SDC
- `safeforge-robust-8-4-v1-archived-table-decoder` — `safeforge-robust-8-4-v1-archived-table-decoder:all-masks`: 135/256 SDC
- `secdaec-rtl-bounded-72-64-v1` — `secdaec-rtl-bounded-72-64-v1:weight-2`: 302/2556 SDC
- `secdaec-rtl-bounded-72-64-v1` — `secdaec-rtl-bounded-72-64-v1:weight-3`: 45304/59640 SDC
- `secdaec-rtl-bounded-72-64-v1` — `secdaec-rtl-bounded-72-64-v1:logical-storage-noncircular-adjacent-2`: 55/71 SDC
- `secdaec-rtl-bounded-72-64-v1` — `secdaec-rtl-bounded-72-64-v1:historical-data-only-noncircular-adjacent-2`: 53/63 SDC
- `secded-rtl-combinational-72-64-v1` — `secded-rtl-combinational-72-64-v1:weight-3`: 45304/59640 SDC
- `shortened-bch-71-64-t1-v1-reference-decoder` — `shortened-bch-71-64-t1-v1-reference-decoder:weight-2`: 1395/2485 SDC
- `shortened-bch-71-64-t1-v1-reference-decoder` — `shortened-bch-71-64-t1-v1-reference-decoder:weight-3`: 31401/57155 SDC
- `shortened-bch-78-64-t2-v1-reference-decoder` — `shortened-bch-78-64-t2-v1-reference-decoder:weight-3`: 13780/76076 SDC
- `taec-rtl-bounded-72-64-v1` — `taec-rtl-bounded-72-64-v1:weight-3`: 45304/59640 SDC
- `taec-rtl-bounded-72-64-v1` — `taec-rtl-bounded-72-64-v1:logical-storage-noncircular-adjacent-3`: 68/70 SDC
- `taec-rtl-bounded-72-64-v1` — `taec-rtl-bounded-72-64-v1:historical-data-only-noncircular-adjacent-3`: 62/62 SDC

## Smallest capability counterexamples

- Historical cyclic `(63,51)`: canonical position `[30]`, mask `1073741824`, produces `SDC_MISCORRECTION` in the weight-1 universe.
- Bounded SEC-DAEC: canonical positions `[0,7]`, mask `129`, are the smallest weight-2 failure; logical storage-coordinate adjacent positions `[4,5]`, mask `48`, are the smallest complete-adjacency failure.
- Bounded TAEC: logical storage-coordinate adjacent positions `[0,1,2]`, mask `7`, are the smallest complete-adjacency failure.

Every failed universe has its own complete JSONL record in `MISCORRECTION_WITNESSES.jsonl`; the examples above do not substitute for the full witness set.

## Five principal blockers for Gate 03

1. Physical PPA remains uncharacterized; Gate 02 creates no measured or synthesized physical evidence.
2. Logical adjacency has no physical bit/interleave mapping yet.
3. Rejected cyclic and bounded SEC-DAEC controls must remain nonselectable.
4. Bounded TAEC remains partial and cannot represent universal TAEC.
5. Generated-width and RTL paths without complete independent executable equivalence remain explicitly non-assessable in the equivalence record.

## Mandatory verdict answers

1. **Yes**, built-in scientific text identity is stable across LF, CRLF and CR; binaries and unversioned registries remain raw-byte sensitive.
2. **15** mathematical codes have reconciled canonical identities.
3. **17** implementations match their registered mathematical-code identity; capability and executable-path status limitations remain binding.
4. **14 exact**, **1 designed-bound**, **0 unresolved** distance records.
5. Implementations passing every positive declared correction universe: forge-hotspot-8-4-v1-archived-table-decoder, forge-spatial-hotspot-72-64-v1-archived-table-decoder, forge-sram-portfolio-72-64-v1-geometry-filtered-joint-archived-table-decoder, forge-sram-portfolio-72-64-v1-spatial-hotspot-joint-archived-table-decoder, hsiao-generated-combinational-72-64-v1, odd-column-secded-4-8-archived-table-decoder, odd-column-secded-64-72-archived-table-decoder, primitive-bch-63-51-t2-v1-reference-decoder, safeforge-robust-72-64-mapping-v1-archived-table-decoder, safeforge-robust-8-4-v1-archived-table-decoder, secded-rtl-combinational-72-64-v1, shortened-bch-71-64-t1-v1-reference-decoder, shortened-bch-78-64-t2-v1-reference-decoder, shortened-bch-85-64-t3-v1-reference-decoder; two remain conditional only because complete RTL equivalence is not assessable.
6. SDC is observed for: cyclic-rtl-bounded-search-63-51-v1, forge-hotspot-8-4-v1-archived-table-decoder, forge-spatial-hotspot-72-64-v1-archived-table-decoder, forge-sram-portfolio-72-64-v1-geometry-filtered-joint-archived-table-decoder, forge-sram-portfolio-72-64-v1-spatial-hotspot-joint-archived-table-decoder, hsiao-generated-combinational-72-64-v1, odd-column-secded-4-8-archived-table-decoder, odd-column-secded-64-72-archived-table-decoder, primitive-bch-63-51-t2-v1-reference-decoder, safeforge-robust-72-64-mapping-v1-archived-table-decoder, safeforge-robust-8-4-v1-archived-table-decoder, secdaec-rtl-bounded-72-64-v1, secded-rtl-combinational-72-64-v1, shortened-bch-71-64-t1-v1-reference-decoder, shortened-bch-78-64-t2-v1-reference-decoder, taec-rtl-bounded-72-64-v1; the exact implementation/universe fractions are listed above and in `CAPABILITY_MATRIX.csv`, with smallest failed-capability witnesses in `MISCORRECTION_WITNESSES.jsonl`.
7. **No.** The historical `(63,51)` degree-12 cyclic candidate is not a valid BCH implementation.
8. **No universal promotion.** Bounded SEC-DAEC remains rejected and bounded TAEC remains partial under complete storage-coordinate adjacency.
9. **Yes.** Wrapper names and duplicate source paths exist; they do not increase registered counts. `SecDaec64.hpp` is an unregistered 73-bit implementation as written.
10. Gate-03 mathematical candidates: forge-hotspot-8-4-v1-archived-table-decoder, forge-spatial-hotspot-72-64-v1-archived-table-decoder, forge-sram-portfolio-72-64-v1-geometry-filtered-joint-archived-table-decoder, forge-sram-portfolio-72-64-v1-spatial-hotspot-joint-archived-table-decoder, hsiao-generated-combinational-72-64-v1, odd-column-secded-4-8-archived-table-decoder, odd-column-secded-64-72-archived-table-decoder, primitive-bch-63-51-t2-v1-reference-decoder, safeforge-robust-72-64-mapping-v1-archived-table-decoder, safeforge-robust-8-4-v1-archived-table-decoder, secded-rtl-combinational-72-64-v1, shortened-bch-71-64-t1-v1-reference-decoder, shortened-bch-78-64-t2-v1-reference-decoder, shortened-bch-85-64-t3-v1-reference-decoder.
11. Noneligible implementations: cyclic-rtl-bounded-search-63-51-v1, secdaec-rtl-bounded-72-64-v1, taec-rtl-bounded-72-64-v1.
12. **No.** Gate 02 supplies no physical, energy, FIT, carbon or publication-readiness evidence.

The next gate is **Gate 03 — common-flow physical PPA feasibility and hard no-go decision.**
