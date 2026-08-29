# DATE 2027 breadth-remediation repository audit

Audit status: `COMPLETE_BEFORE_EXPERIMENT_IMPLEMENTATION`

Audit date: 2026-08-26 (Asia/Calcutta)

## Repository state

- Repository root: `C:/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction`
- Baseline commit: `b51291442bbd04346dac939dea6ba7d532b9c5c4`
- Baseline branch: `main`
- Baseline upstream: `origin/main`
- Baseline working tree before tests: clean
- Baseline working tree after removal of uniquely identified test by-products: clean
- Additive campaign branch: `codex/date-2027-breadth-remediation`
- Destructive Git operations: none
- Tracked repository files at audit: 2,240
- Files visible with `rg --files -uu` at audit: 73,525; this larger count includes `.git`, caches, generated fixtures, and ignored runtime products.

The mandatory baseline build regenerated `PracticalSRAMSimulator.exe` and the two Python runs created eight UUID-named runtime ML fixture directories. Those exact audit-created by-products were removed, and only the regenerated executable was restored to its exact HEAD bytes. No pre-existing uncommitted user change was present or altered.

## Existing campaign and experiment layout

The DATE 2027 evidence is organized under `docs/date2027/` as `rigour_gate_01`, `rigour_gate_02`, `rigour_gate_03`, `rigour_gate_03e`, `rigour_gate_03er`, `rigour_gate_03es`, `rigour_gate_03f`, `rigour_gate_03r`, `rigour_gate_04`, `rigour_gate_04_final`, `rigour_gate_05`, `rigour_gate_06`, `rigour_gate_07`, and `revision2`.

Related executable infrastructure is organized under `scripts/gate03*`, `scripts/gate04*`, `scripts/gate05`, `scripts/gate06`, `scripts/gate07`, and `scripts/revision2`. The Revision-2 manuscript is isolated under `paper/date2027_revision2`. General characterization data and registries live under `green_ecc_physical_simulation/`; general analyses live under `analysis/`; repository-wide Python tests live under `tests/python/`.

The qualified Revision-2 campaign has:

- 71 tracked repository files across `docs/date2027/revision2`, `scripts/revision2`, and `paper/date2027_revision2`;
- an external immutable root at `/var/lib/green-ecc-date2027-revision2` inside WSL Ubuntu 24.04;
- 2,366 external files totaling 2,289,079,197 bytes at audit;
- read-only policy, qualification, and run directories (`0555`);
- 20 immutable matched-seed run directories: four qualified identities at seeds 11, 13, 17, 19, and 23;
- final ODB, Verilog netlist, SDC, SPEF, DEF, GDS, reports, logs, power reports, trace policy, run manifests, and raw hash manifests.

The complete frozen inventory is `00_baseline_inventory.sha256`. It covers the 71 tracked Revision-2 files, eight protected qualified source identities, and all 2,366 files under the external Revision-2 root. Duplicate paths are de-duplicated by canonical inventory key.

## Qualified implementation identities (names unchanged)

### Conventional/combinational SECDED (72,64)

- Implementation ID: `secded-rtl-combinational-72-64-v1`
- Physical top: `gate04_secded_comb_72_64`
- Core modules: `gate03r_secded_baseline_encoder` and `gate03r_secded_baseline_decoder`
- Core source: `scripts/gate03r/rtl/secded_characterization_tops.sv`
- Transaction boundary: `scripts/gate04/rtl/gate04_boundaries.sv`
- Revision-2 config: `scripts/revision2/configs/secded_comb.mk`
- Request latency: one cycle
- Initiation interval: one cycle

### Pipelined SECDED (72,64)

- Implementation ID: `secded-rtl-pipelined-72-64-v1`
- Physical top: `gate04_secded_pipe_72_64`
- Core modules: `secded_pipelined_72_64_v1_encoder` and `secded_pipelined_72_64_v1_decoder`
- Core source: `asic/rtl/secded/secded_pipelined_72_64_v1.sv`
- Transaction boundary: `scripts/gate04/rtl/gate04_boundaries.sv`
- Revision-2 config: `scripts/revision2/configs/secded_pipe.mk`
- Request latency: three cycles
- Initiation interval: one cycle

### Algorithmic Hsiao SECDED (72,64)

- Code ID: `hsiao-secded-72-64-v1`
- Implementation ID: `hsiao-algorithmic-combinational-72-64-rev2-v1`
- Physical top: `gate04_rev2_hsiao_72_64`
- Encoder: `hsiao_secded_72_64_v1_encoder`
- Syndrome generator: `hsiao_secded_72_64_v1_syndrome`
- Qualified algorithmic decoder: `hsiao_secded_72_64_v2_algorithmic_decoder`
- Sources: `green_ecc_physical_simulation/rtl/hsiao_secded_72_64/`
- Transaction boundary: `scripts/revision2/rtl/rev2_hsiao_boundary.sv`
- Request latency: one cycle
- Initiation interval: one cycle
- Qualification: exhaustive Yosys SAT over arbitrary 72-bit received words, recorded as `HSIAO_EXACT_IDENTITY_PASS`.

### BCH (78,64,t=2)

- Implementation ID: `shortened-bch-78-64-t2-v1-rtl-syndrome-chien-v1`
- Physical top: `gate04_bch_78_64`
- Core modules: `bch_78_64_t2_v1_encoder` and `bch_78_64_t2_v1_decoder`
- Core source: `asic/rtl/bch/bch_78_64_t2_v1.sv`
- Transaction boundary: `scripts/gate04/rtl/gate04_boundaries.sv`
- Revision-2 config: `scripts/revision2/configs/bch78.mk`
- Request latency: one cycle
- Initiation interval: one cycle
- The breadth-remediation campaign does not alter, optimize, or rerun this implementation.

## Infrastructure audit

### Formal verification

Formal infrastructure includes `scripts/gate03/formal`, `scripts/run_gate02_equivalence.py`, `scripts/run_code_equivalence_audit.py`, the Gate-03R exact proof matrices, `scripts/gate04/mapped_equivalence*.sh`, and the Revision-2 Hsiao SAT miter/qualification script. Local Yosys is available; the frozen ORFS image also contains the qualified Yosys environment.

### ORFS/OpenROAD

The qualified backend is available through Docker inside WSL Ubuntu 24.04. The frozen image is `openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e`, with ORFS commit `56496f3980fb6e9e58f10c8aea4a98949c0fe5f2` and OpenROAD commit `ab6fd26351dc449e69059684dc6aa9ae9046eb36`. The platform/corner is SKY130HD `tt_025C_1v80` at 1.80 V and 25 C. Revision-2 uses 35% core utilization, aspect ratio 1.0, 10 um margin, placement density 0.55, one worker, no LEC, 10% input/output delay, and 0.05 pF output load.

### Power analysis

Revision-2 power uses OpenSTA on the final routed ODB/SDC/SPEF, reads the frozen no-error VCD at scope `gate04_trace_top`, propagates activity, and emits `report_power -digits 12`. All five matched combinational and pipelined SECDED runs contain full-precision text reports with internal, switching, leakage, and total power. Native JSON is rounded and is not the precision authority. The frozen trace contains 100,000 useful operations at II=1.

### Analysis and tests

Revision-2 extraction and descriptive paired analysis are in `scripts/revision2/analyze_results.py`; publishing is in `scripts/revision2/publish_results.py`; repository tests include `tests/python/test_revision2_analysis.py` and `tests/python/test_revision2_hsiao.py`. The root `Makefile` defines `make`, `make test`, and the C++ `gtest` target. `pytest.ini` selects `tests` and excludes runtime/cache trees.

## Candidate selection

The cleanest second exact-equivalent structural pair is the qualified algorithmic Hsiao identity. Its decoder currently realizes a flat set of 72 independent 8-bit syndrome comparisons. The additive identity can share high- and low-nibble decode terms and construct each column match hierarchically, while byte-reusing the qualified encoder and syndrome generator and keeping the same registered boundary. This is a correction-selection-network transformation, not a temporal transformation, and therefore directly addresses implementation identity beyond combinational-versus-pipelined SECDED.

The candidate is lower risk than changing conventional SECDED parity equations because the code matrix, syndrome network, encoder, interface, boundary registers, latency, and II can remain byte-identical, while the intended structural change is isolated to a formally enumerable combinational decoder relation.

## Audit verdict

`G0_REPOSITORY_BASELINE_PRESERVED = PASS` at Stage 0. Final PASS remains conditional on the post-campaign hash revalidation.
