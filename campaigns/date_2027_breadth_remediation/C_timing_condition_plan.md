# Workstream C timing-condition plan

Plan status: `FROZEN_BEFORE_5NS_PHYSICAL_EXECUTION`

```text
historical target = 10 ns
new target        = 5 ns
seeds             = {11,13,17,19,23}
architectures     = SECDED comb + SECDED pipe
```

## Controlled factor

Exactly one major physical-design condition changes: the clock target is tightened from 10.0 ns to 5.0 ns. The ABC clock period changes correspondingly from 10,000 ps to 5,000 ps. Input and output delays remain 10% of the selected clock period, following the unchanged parametric SDC methodology. No other technology, corner, RTL identity, floorplan, utilization, density, output load, worker, seed, or activity condition is changed.

The target is predeclared as a simple 2x tightening and will not be changed after results are observed. Repository and runtime inspection found no fundamental technical invalidity: the SDC is parameterized by `CLOCK_PERIOD`, the ORFS runner already passes `ABC_CLOCK_PERIOD_IN_PS`, and the frozen physical flow accepts a 5.0 ns target. Feasibility is an experimental result, not a reason to alter the target.

## Fixed identities

- Combinational implementation ID: `secded-rtl-combinational-72-64-v1`
- Combinational physical top: `gate04_secded_comb_72_64`
- Pipelined implementation ID: `secded-rtl-pipelined-72-64-v1`
- Pipelined physical top: `gate04_secded_pipe_72_64`
- Request latencies: one and three cycles, respectively
- Initiation interval: one cycle for both

No historical RTL or boundary source may be modified. The new campaign configuration will reference their protected hashes.

## Common physical policy

- Container: `openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e`
- ORFS commit: `56496f3980fb6e9e58f10c8aea4a98949c0fe5f2`
- OpenROAD commit: `ab6fd26351dc449e69059684dc6aa9ae9046eb36`
- Platform/corner: SKY130HD, `tt_025C_1v80`, 1.80 V, 25 C
- Core utilization: 35%
- Core aspect ratio: 1.0
- Core margin: 10 um
- Placement density: 0.55
- Input delay: 10% of 5.0 ns
- Output delay: 10% of 5.0 ns
- Output load: 0.05 pF
- Workers: one
- LEC: disabled, matching Revision-2
- Seeds: exactly 11, 13, 17, 19, 23, mapped identically to GPL, global-route, and ORFS seed variables
- Activity: same 100,000-operation II=1 no-error payload sequence and trace-generation semantics, at the declared 5 ns operating period

## Execution order and evidence gate

Generate ten fresh implementations, interleaved by seed: combinational then pipelined at seed 11, then the same ordering at 13, 17, 19, and 23. Do not reuse a 10 ns routed database for 5 ns STA. Do not retry a poor result or substitute a seed.

A 5 ns point is feasible only if the complete physical flow exits successfully, routing is complete, setup slack is nonnegative, setup violations are zero, hold is clean, and final physical checks are clean. Target-frequency power and energy are reported only for feasible points joined to their own final ODB/netlist, SPEF, SDC, 5 ns activity trace, seed, RTL/config hashes, and run identity.

Analysis will report within-5-ns matched comparisons and explicit 10-ns-versus-5-ns condition sensitivity. Historical and new physical identities remain separate. Descriptive statistics are limited to mean, median, sample standard deviation, minimum, maximum, range, paired percentage effects, and ordering/feasibility counts. No population inference is authorized.
