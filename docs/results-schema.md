# Results and schema guide

Machine-readable contracts live under `schemas/`, registry-local schema references, and campaign-specific `schema/` directories. The exact schema attached to a file is authoritative. Existing field names and default CLI formatting are compatibility contracts.

## Common identity fields

| Field concept | Meaning |
|---|---|
| `schema_version` | Contract version, not evidence strength |
| code/implementation/architecture IDs | Bound mathematical, executable, and deployment identity |
| backend/tool/commit/image | Producer identity |
| PDK/library/macro/PVT | Technology boundary |
| workload/operation/fault model | Stimulus population |
| seed | Random or physical seed; null only when not applicable |

## Quantity fields

Every measured or modelled quantity should carry a value or explicit null, unit, direction where optimized, source, measurement/model boundary, uncertainty or population note, evidence tier/kind, qualification state, and permitted/forbidden use. `0` is a measured/modelled zero; `null` is not available; `BLOCKED` explains why it cannot be qualified.

## Outcome vocabulary

Logical decoders distinguish correct/no-error, corrected, detected-uncorrectable, silent corruption, and implementation-specific ambiguous/rejected states. Physical flows distinguish completion from timing, DRC, LVS, and signoff. Sustainability results distinguish ECC logic, SRAM macro, whole-memory, use phase, manufacturing, and lifecycle boundaries.

## Provenance

A reproducible result normally records repository commit and dirty state, configuration and scientific-source hashes, full command, tool versions, environment/container identity, seed, timestamps, budget/timeout, source paths, output hashes, and parent evidence. Historical absolute paths may occur in these fields and must not be interpreted as current defaults.

## Compatibility and migrations

Readers should ignore additive unknown fields but must not reinterpret an existing field. If meaning changes, add a new field/schema version and an explicit migration. Scientific hash migrations are recorded in the registry rather than concealed through reserialization.

Run `python scripts/check_artifact.py` for high-value guard checks; use the schema-specific validators for a full package.
