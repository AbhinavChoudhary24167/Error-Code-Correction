# Research-question status

| RQ | Result | Classification |
|---|---|---|
| RQ1 wafer carbon vs node | Public imec evidence supports increasing fab electricity toward A14, but no common-boundary absolute wafer curve was recovered. | PARTIAL_QUALITATIVE |
| RQ2 carbon per good die | Gross-die geometry and Poisson, negative-binomial, and Murphy yield paths are executable; node-matched absolute results are unavailable. | PARAMETRIC_SENSITIVITY |
| RQ3 carbon per memory bit | No matched node density, SRAM area, yield, and wafer-carbon dataset exists. | UNANSWERED |
| RQ4 saturation of per-bit improvement | Cannot be inferred without RQ3. | UNANSWERED |
| RQ5 patterning share | The model separates route steps and keeps patterning as a diagnostic Scope-2 subset; numeric node shares are unavailable. | STRUCTURE_VALIDATED |
| RQ6 when EUV helps | imec supports the N7 direction: removal of multiple DUV deposition/etch/clean steps can outweigh higher scanner power. A universal crossover is not calibrated. | QUALITATIVE_SOURCE_SUPPORTED |
| RQ7 gases vs electricity | Current imec study-wide ranges are 6–8% Scope 1 and 52–65% Scope 2, not node-resolved production values. | BOUNDED_SOURCE_RANGE |
| RQ8 abatement sensitivity | Wafer Scope 1 is monotonically non-increasing with improved abatement; scenario magnitudes are parametric. | PROPERTY_TESTED |
| RQ9 electricity decarbonization | Scope 2 changes linearly with fab CI; fab CI is the largest normalized influence (0.3741) in the declared ensemble. | PARAMETRIC_SENSITIVITY |
| RQ10 mask NRE vs volume | Per-die mask NRE scales as `1/(product wafers × good dies/wafer)` and vanishes asymptotically; absolute maskset carbon is bounded only. | PARAMETRIC_SENSITIVITY |
| RQ11 yield and maturity | Lower yield raises good-die carbon; maturity changes only through explicit defect, line-yield, energy, gas, upstream, patterning, and abatement inputs. | PROPERTY_TESTED |
| RQ12 imec trend reproduction | Textual N28/A14 energy-sensitivity endpoints and qualitative route trends are reproduced structurally; a full absolute curve is not. | PARTIAL_VALIDATION |
| RQ13 ACT/ACT3 comparison | Independent ACT and GREEN paths agree exactly for matched algebra/units; absolute magnitude and ACT3 BOM comparison remain partial. | ALGEBRA_VALIDATED_MAGNITUDE_PARTIAL |
| RQ14 node uncertainty | A 4,096-sample normalized ensemble gives P05 0.6906 and P95 1.8382, but it is not a node-resolved confidence interval. | PARAMETRIC_ENSEMBLE |
| RQ15 ranking changes with node | No qualified GSE ranking exists at any node. | UNANSWERED |
| RQ16 ranking changes with fab cleanup | Fab scenarios are executable intervals, but ranking effects cannot be evaluated. | UNANSWERED |
| RQ17 stronger ECC benefit | E0 corrects all enumerated single-bit masks, but no physical event mix or lifecycle-carbon denominator is qualified. | LOGICAL_CONTROL_ONLY |
| RQ18 when SECDED dominates | No scientifically defensible dominance region is established. | UNANSWERED |
| RQ19 when stronger codes dominate | DAEC, TAEC, BCH, and comparable physical rows are not qualified in this campaign. | UNANSWERED |
| RQ20 interleaving effect | I0/I1/I2 mappings are bijective and tested; I1/I2 layout, cost, and physical upset redistribution are absent. | MAPPING_ONLY |
| RQ21 MBU spatial effect | Best/nominal/worst topology scenarios are bounded contracts without calibrated probabilities. | PARAMETRIC_ONLY |
| RQ22 scrubbing effect | In the four-step E0 control, scrub-on-correct changes success from 0.25 to 1.0; this is a finite sequence, not an event rate. U0 remains all SDC. | DERIVED_LOGICAL_CONTROL |
| RQ23 read/write-ratio effect | Component activity and macro read/write energy are insufficiently qualified. | UNANSWERED |
| RQ24 lifetime/grid dominance | The equations expose the crossover, but operational energy is unavailable, so no crossover is reported. | UNANSWERED |
| RQ25 legacy vs new selection | Formula-level disagreement and candidate-set effects are proven; actual U0/E0 selections cannot be compared. | FORMULA_ONLY |
| RQ26 metric defensibility | GSE/GCI respect service/carbon dominance and candidate independence; the legacy selector does not. Neither licenses a winner with missing evidence. | THEOREM_SUPPORTED |
