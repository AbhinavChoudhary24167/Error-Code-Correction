# Class-C counterfactual diagnostic

This read-only diagnostic loaded the canonical final seed-11 ODB/SDC/SPEF and unchanged timing tables, propagation delays, loads, netlist, placement, and routing. Separately labelled diagnostic Liberty copies changed only the library-level `default_max_transition` from 0.04 to the standard-cell-level 1.50 ns, thereby excluding the inherited SRAM-output rule. Production Liberty remained byte-identical before/after, as recorded in `raw/diagnostics/class_c_counterfactual/diagnostic_liberty_manifest.json`; the copies were never used to generate production results.

U0 counterfactual residual rows: 1, `u_data/rstb`. E0 counterfactual residual rows: 1, `u_protected_memory.u_data/rstb`. Thus Class C disappears without any physical or timing-table change, but each design's genuine data-macro `rstb` violation remains. There are no other canonical external max-transition violations. This supports the Class-C causal disposition but cannot make Attempt09 pass.
