# Gate 04 policy amendment 04 — line-local generic-cell validation

`secded-comb-10ns-seed29-attempt1` completed the official RTL-to-GDS flow, exact RTL-to-mapped and mapped-to-post-route equivalence, and all frozen activity-power cases. Its final Python validator then rejected the legal final netlist while reporting no offending token.

The cause is language-specific: Python regular-expression `\s` includes newline characters. The predicate `^\s*(?:\$_|\\\$)` could therefore begin on a blank line, cross the newline, consume indentation and cell-type text, and reach `$` inside a legal escaped instance name such as `\dec_codeword_echo_o[0]$_SDFF_PN0_`. The shell predicate fixed by amendment 02 used POSIX horizontal matching and passed the same artifact.

Amendment 04 changes the Python prefix from `\s*` to `[ \t]*`, making the test strictly line-local. A focused regression proves that a SKY130 technology cell with a Yosys-derived escaped instance name passes, while actual generic `$_...` and escaped `$...` cell types fail. Existing status-99 attempts are revalidated in place from their preserved physical, equivalence and power artifacts; their original metadata and raw manifests remain unchanged and additive amendment records are created. No RTL, physical artifact, SDC, seed, trace, hypothesis, threshold or selection rule changes.
