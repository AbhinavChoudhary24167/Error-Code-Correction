# Gate 1 infrastructure incident — attempt 01

## Classification

`INFRASTRUCTURE_FAIL_BEFORE_OPENROAD_POWER_ANALYSIS`

The first declared matrix namespace is preserved at
`/var/lib/green-ecc-iscas-sustainability/gate1_activity_power`. All 20
container invocations exited before the ORFS `make ... run` command and before
any `read_db`, `read_spef`, `read_vcd`, or `report_power` operation.

The shared command encoded the trace list as an unquoted shell value containing
`|`. Bash interpreted both separators as pipelines. The diagnostic signature
was identical for all seeds and architectures: exit code 126 in approximately
0.9 seconds, with attempts to execute the VCD paths as commands.

No scientific power point was produced, no frozen input was writable, and no
seed-specific physical outcome exists to replace. Attempt 02 changes only the
orchestration quoting around the exact same frozen trace-specification value.
The failed namespace is neither deleted nor excluded from the final evidence
audit.

## Attempt 02 validator incident

Attempt 02 corrected the quoting issue and OpenROAD completed W1 and W2 power
reports. Seven invocations were sealed by the runner, but were labelled `FAIL`
because the first version of the report parser required component-to-total
agreement within `2e-9` relative. The frozen W0 reports and new reports exhibit
ordinary independently accumulated report differences of order `1e-8`
relative, so this check was stricter than the inherited evidence format.

The runner was interrupted after the eighth OpenROAD completion marker to
avoid generating more false failures. That eighth run has both complete power
reports but was interrupted before runner metadata/sealing. Attempt 03 admits
these eight completed invocations by durable report hash and OpenROAD
completion marker and executes only the remaining twelve invocations. None of
the sixteen completed W1/W2 power points is rerun.
