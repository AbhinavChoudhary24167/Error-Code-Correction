# Frozen SRAM22 output-transition audit

Classification: **UPSTREAM_SRAM22_OUTPUT_MAX_TRANSITION_MODEL_INCONSISTENCY**.

Attempt09 remains **FAIL / KEEP_GATE3_FAILED**. Its residual data-rstb failure is independent of the output-model discrepancy.

| Macro | PVT | Default (ns) | Table minimum (ns) | Table maximum / diagnostic bound (ns) | Max load (pF) | Outputs |
|---|---|---:|---:|---:|---:|---:|
| sram22_256x64m4w8 | ff_n40C_1v95 | 0.04 | 0.057383 | 2.57436 | 0.52 | 64 |
| sram22_256x64m4w8 | ss_100C_1v60 | 0.04 | 0.14844 | 4.86284 | 0.52 | 64 |
| sram22_256x64m4w8 | tt_025C_1v80 | 0.04 | 0.080573 | 3.25762 | 0.52 | 64 |
| sram22_256x8m8w1 | ff_n40C_1v95 | 0.04 | 0.05825 | 2.57477 | 0.52 | 8 |
| sram22_256x8m8w1 | ss_100C_1v60 | 0.04 | 0.151059 | 4.86023 | 0.52 | 8 |
| sram22_256x8m8w1 | tt_025C_1v80 | 0.04 | 0.081685 | 3.25718 | 0.52 | 8 |

All samples of all four supplied output-transition table types exceed the 0.04 ns global default in every frozen view. The JSON records full axes and tables, min-load columns, fastest-input rows, applicable pins, input capacitance, explicit/effective pin limits, and source hashes.

## Diagnostic bound and its limits

CORRECTED adds an explicit limit to each output pin equal to the largest supplied output-transition sample for that pin in that PVT view, across rise, fall, and retention slew tables. It preserves the upstream global attribute and every non-output constraint. The envelope admits all supplied characterization grid samples without selecting an arbitrary target such as 0.4 ns. It is a research-corrected characterization-consistent diagnostic view, **not a foundry correction or a demonstrated safe operating limit**. Output receivers retain their separate Liberty limits; output loads and input slews must still be checked against characterization axes. Values outside that domain are not qualified by this bound.

ORIGINAL is byte-identical to frozen source. PIN_SPECIFIC_OR_NO_GLOBAL_COUNTERFACTUAL removes only the global default after verifying explicit limits protect every non-output signal pin. In all views rstb remains **0.351 ns**. Complete timing/internal-power groups and non-output pin groups are byte-identical, and manifests list every exact insertion/deletion. GDS/LEF/RTL/SDC are not altered by this generator.

## Research consequences

The audit proves an inconsistency between a library-wide output constraint and its supplied transition samples. It does not prove that the default is a typo, reconstruct its intended value, waive an input requirement, or regenerate characterization. Full matched physical runs must distinguish optimization/PPA effects from report classification changes. No PPA, energy, reliability, carbon, or GREEN ranking improvement follows from this audit alone.

Reproduce from the repository root with `python campaigns/iscas_sustainability_extension/memory_compiler/gate3_attempt10_green_matrix_physical_model_validation/scripts/liberty_transition_audit.py`. The generator refuses to overwrite a differing generated Liberty. All source inputs are read from frozen Attempt09/source_checkout.
