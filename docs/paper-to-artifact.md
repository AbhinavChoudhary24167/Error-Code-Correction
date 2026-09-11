# Paper-to-artifact map

This map links manuscript claim classes to executable or inspectable evidence without inventing publication figure numbers. Manuscript-specific figure/table manifests remain authoritative.

| Claim or paper element | Artifact source | Reproduction/validation |
|---|---|---|
| Code/implementation identity and logical verification | `green_ecc_physical_simulation/registry/`, generated [ECC catalogue](ECC_CATALOGUE.md) | `python eccsim.py ecc list`; `python eccsim.py ecc verify --implementation ID` |
| Conditional reliability and qualification rules | `campaigns/iscas_sustainability_extension/green_matrix_v3_2/data/` | `make artifact-check`; campaign validators/tests |
| Matched 40-run physical population | [physical run results](../campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation/PHYSICAL_RUN_RESULTS.csv) and [final report](../campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation/FINAL_REPORT.md) | Inspect manifest/hashes; Level 3 environment for rerun |
| Fresh OpenRAM attempt and its limits | [OpenRAM provenance](../campaigns/iscas_sustainability_extension/green_v3_2_matched_openram_orfs_validation/OPENRAM_PROVENANCE.json) | Confirm timeout, exit 137, and incomplete DRC/LVS/characterization |
| E5 activity-qualified ECC-logic observations | [v3.3 status](../campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5/CAMPAIGN_STATUS.json) and additive matrix | `make artifact-check`; package validation records |
| DATE activity/energy manuscript tables and figures | [DATE revision-2 package](../campaigns/date_2027_activity_qualified_ecc_energy_rev2/README.md), its source-data and manifests | Run its read-only validation scripts; rebuild only in a prepared manuscript environment |
| ISCAS manuscript traceability | [ISCAS reproduction guide](../paper/iscas2027/REPRODUCE.md) | Use package validator and manuscript-local provenance table |
| Current blind manuscript source/PDF | `paper/date2027_revision/` and `output/pdf/DATE2027_MANUSCRIPT_REV2_BLIND.pdf` | Follow manuscript README/validation; compare generated PDF hash |
| Global-winner and lifecycle limitations | [Limitations](limitations.md), [evidence model](evidence-model.md), campaign status fields | Confirm `NO_GLOBAL_WINNER_QUALIFIED` and blocked operands |

The campaign data is primary. A plot, table, or prose sentence cannot elevate the qualification of its source quantity. Superseded figures are retained only where their package explicitly labels them as such.
