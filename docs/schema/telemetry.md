# Telemetry Schema

This document freezes the schema for telemetry logs consumed by the tooling in
this repository. Each record represents a single workload run and must provide
all of the following fields. Units are fixed and encoded in the field names.

| Field          | Type    | Units | Description |
|----------------|---------|-------|-------------|
| `workload_id`  | string  | –     | Identifier for the workload being measured. |
| `node_nm`      | integer | nm    | Process technology node. |
| `vdd`          | number  | V     | Supply voltage. |
| `tempC`        | number  | °C    | Operating temperature. |
| `clk_MHz`      | number  | MHz   | Clock frequency. |
| `xor_toggles`  | integer | count | Number of XOR gate toggles. |
| `and_toggles`  | integer | count | Number of AND gate toggles. |
| `add_toggles`  | integer | count | Number of adder toggles. |
| `corr_events`  | integer | count | Number of correction events. |
| `words`        | integer | count | Total words protected by ECC. |
| `accesses`     | integer | count | Memory accesses issued. |
| `scrub_s`      | number  | s     | Interval between scrub operations. |
| `capacity_gib` | number  | GiB   | Memory capacity. |
| `runtime_s`    | number  | s     | Runtime of the workload. |

Telemetry data may be provided as CSV or JSON. The canonical CSV form orders
columns as shown above. The accompanying
[`telemetry.schema.json`](telemetry.schema.json) file encodes these constraints
using [JSON Schema](https://json-schema.org/) and is used by the validator in
`parse_telemetry.py`.
