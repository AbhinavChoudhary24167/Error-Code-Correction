# DATE 2027 final physical environment

Status: `DATE_FINAL_PHYSICAL_ENVIRONMENT_FROZEN`

This is the authoritative physical-design environment for all newly generated DATE 2027 measurements. It was frozen at `2026-08-24T10:43:21Z`, before the first Gate 03F qualification run. Any change to an input byte, image digest, tool or platform identity, constraint, configuration, clock, placement setting, seed policy, or relevant environment variable invalidates the post-freeze physical dataset and requires a new environment identity and new run-root namespace.

Gate 03E, Gate 03E-R, Gate 03E-S, and all physical Gate 04 attempts that predate this freeze remain preserved historical exploratory or qualification evidence. Pre-freeze Gate 04 measurements are classified `PRE_GATE03F_EXPLORATORY` and are not DATE-final paper measurements.

## Execution identity

- Repository Git commit: `ceae4ad9b5a3ba612596fb7ac1a93dd144114409`.
- Exact source identity: the 16-file read-only snapshot listed with raw-byte SHA-256 hashes in `DATE_FINAL_PHYSICAL_ENVIRONMENT.json`. The dirty working-tree state is provenance only; execution uses the snapshot, not the mutable checkout.
- WSL distribution: `Ubuntu-24.04`, Ubuntu 24.04.4 LTS.
- WSL kernel: `Linux 6.18.33.2-microsoft-standard-WSL2 x86_64 GNU/Linux`.
- Docker client/server: `29.7.2` / `29.7.2`.
- Docker image: `openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e`.
- ORFS commit: `56496f3980fb6e9e58f10c8aea4a98949c0fe5f2`; tree `2b736d484fa7a26b38b1439f177aeb6c1f3e9d5a`.
- OpenROAD commit: `ab6fd26351dc449e69059684dc6aa9ae9046eb36`; version `26Q3-1080-gab6fd26351`; binary SHA-256 `2fc67d3a82df36014b615e710ce2e68600b592b27b051e4533c30248a2e2eb91`.
- Yosys: `0.68+post`; KLayout: `0.30.7`.
- External immutable evidence root: `/var/lib/green-ecc-date2027-final`.

The content-addressed Docker image is the primary execution identity. The ORFS commit records the source revision to which the executing image bytes were reconciled; the image contains no `.git` directory.

## Technology and corner

- Platform: `sky130hd`.
- Corner: `tt_025C_1v80` at the platform-defined 1.80 V, 25 C typical corner.
- Platform configuration: `/OpenROAD-flow-scripts/flow/platforms/sky130hd/config.mk`, SHA-256 `1a36b8fbd58ee4b6b961bc14f3ca44e7b44a4ea47faf6f116f827eb5177509d5`.
- Technology LEF: `sky130_fd_sc_hd.tlef`, SHA-256 `8e99b4e8b016db0713029ebcae6b2cc2aedd9c2c49682e2f23521dd0b1a2085e`.
- Standard-cell LEF: `sky130_fd_sc_hd_merged.lef`, SHA-256 `44180aaa0068b1fcb0789f128b090304c01ad48f511d3f7afa66c90b3e176ec5`.
- Liberty: `sky130_fd_sc_hd__tt_025C_1v80.lib`, SHA-256 `ec0e1067a35c8bf20b11e58d1e8ac53326067e4dac84a125cc1b917a3518d0d9`.
- RC setup: `setRC.tcl`, SHA-256 `6aeade350bf498177ea61506db8849a064a71848b05c18ad6a6e1fc5d62c962a`.

## Frozen RTL, constraints, and configurations

- GCD RTL in the image: SHA-256 `5009f224876d39e5e77e59ee1528cb0d2a03697251f0971b77cf3e8b0426dd3e`.
- Representative SECDED RTL: `scripts/gate03r/rtl/secded_characterization_tops.sv`, SHA-256 `560bc8092ba759f7dd3412a106d86a30a7498d88285298c721be2d5ef4dc440b`.
- BCH `(78,64,t=2)` RTL: `asic/rtl/bch/bch_78_64_t2_v1.sv`, SHA-256 `2cc8b0dd23f3cce9a091ea418a2c2d4fff5f016361228a66e6c151a7c49360e7`.
- Common ECC boundary RTL: `scripts/gate04/rtl/gate04_boundaries.sv`, SHA-256 `7de8e8d2933cdf17740ec5ec6f45a3654d5d54d9e419ed1c628ab29ca03308f8`.
- ECC SDC: SHA-256 `7d8c4f563ace74fa762c1a8df4593a68aa0ca285519962c8121504333ec8fb09`.
- GCD SDC: SHA-256 `36b996eab32fcbc177425befbc41e5191a0e931906a3b6bb7913a616573aa680`.
- GCD, SECDED, and BCH configuration hashes: `0d2133424aef47953b1224f62f3e12498510550f03f4c6b43a32809022eaf486`, `1736a717940ea9f6966e03bf0973c208a87fb473a09d5ad1ab93659b481e8f3d`, and `f3eaeab349ee6a694ddf017939bf811847d03cc44051d26f63eb38011936528a`.
- Frozen contract SHA-256: `b9860d076b68d68f45051235ba3a75ce29476285ddffe8b8cf8db12a8beb870f`.

The complete source and collateral inventory is machine-readable; this summary does not replace it.

## Common physical policy

- Clock period: `10.0 ns`; ABC period: `10000 ps`.
- Input delay: `10%` of the clock; output delay: `10%`; output load: `0.05 pF`.
- Core utilization: `35%`; aspect ratio: `1.0`; core margin: `10 um`; placement density: `0.55`.
- `NUM_CORES=1`; `LEC_CHECK=0`.
- Fixed physical seed: `11`.
- Available and fixed seed variables: `GPL_RANDOM_SEED=11`, `GRT_SEED=11`, and `OR_SEED=11`. Their use in the pinned ORFS scripts is captured by `seed-control-source-proof.txt` and source hashes in the machine manifest.
- Other relevant variables: `CLOCK_PERIOD=10.0`, `ABC_CLOCK_PERIOD_IN_PS=10000`.

GCD and ECC use port-appropriate SDC files with the same clock, fractional I/O delays, and output load. All three design configurations use the same platform and placement policy.

## Frozen qualification matrix

- GCD: `gcd-01`, `gcd-02`, `gcd-03`.
- Representative conventional SECDED `(72,64)`: `secded-01`, `secded-02`.
- BCH `(78,64,t=2)`: `bch78-01`, `bch78-02`.

Each run directory must be created once beneath `/var/lib/green-ecc-date2027-final/runs`, must never be reused, and becomes read-only with a raw-artifact SHA-256 inventory when its single attempt ends.

## Power and activity

Nine new deterministic VCDs were generated before physical execution: conventional SECDED, Hsiao, and BCH78, each under no-error, single-error, and double-error activity. Every trace contains exactly 100,000 useful operations at 10 ns, uses SplitMix64 payload seed `104375203646206`, and fault-schedule seed `7085774586302733229`. The trace-manifest SHA-256 is `5608b592deef797e5426430ce3b8ad83a0a5359ce452c87e4b54bfdaa9a9c9aa`.

Post-route OpenSTA reads the VCD into the final ODB/SDC/SPEF, propagates activity, and reports internal, switching, leakage, and total power. Energy is defined as `power_W * total_trace_time_ps / useful_operations`, yielding pJ per useful ECC operation. There is no arbitrary toggle rate or field-rate weighting. Power has a ten-minute nonblocking analysis limit; if the common method fails, the status is `POWER_DEFERRED` and physical qualification continues.

## Frozen measurement and interpretation policy

For every repeated numeric metric, report the mean, sample standard deviation, coefficient of variation, minimum, maximum, range, and maximum relative run-to-run difference. The relative difference is `(max-min)/max(abs(max),abs(min))`; equal zero values have zero observed difference. A zero mean has an undefined coefficient of variation and is reported as such.

Geometry, cell-count, utilization, and wirelength noise must not exceed `1%`; timing and Fmax noise must not exceed `2%`. Power noise must not exceed `2%` for power to be qualified, but power never blocks Gate 03F.

> A comparative ECC effect will be interpreted quantitatively only when its magnitude is at least 5× the measured reproducibility noise for that metric.

Noise magnitude is the observed repeated-run range in that metric's own units. If the observed range is zero, zero is reported; no positive tolerance is invented, and a future claimed effect must still be nonzero.

## Exact commands

Environment freeze:

```text
python3 scripts/gate03f/prepare_environment.py --repo /mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction
```

Seven-run matrix:

```text
python3 /var/lib/green-ecc-date2027-final/policy/repo_snapshot/scripts/gate03f/run_matrix.py
```

Per physical run, with the frozen design configuration substituted:

```text
source /OpenROAD-flow-scripts/env.sh
export LEC_CHECK=0 NUM_CORES=1 WORK_HOME=/date-final-run CLOCK_PERIOD=10.0 GPL_RANDOM_SEED=11 GRT_SEED=11 OR_SEED=11
cd /OpenROAD-flow-scripts/flow
make ABC_CLOCK_PERIOD_IN_PS=10000 DESIGN_CONFIG=/date-final-repo/scripts/gate03f/configs/CONFIG
```

Analysis after logical validation:

```text
python3 /var/lib/green-ecc-date2027-final/policy/repo_snapshot/scripts/gate03f/analyze_qualification.py --logical-validation PASS
```
