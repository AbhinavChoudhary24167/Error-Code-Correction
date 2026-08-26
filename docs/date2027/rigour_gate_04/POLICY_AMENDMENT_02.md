# Gate 04 policy amendment 02 — cell-type predicate and attempt2 completion

`secded-comb-10ns-seed11-attempt2` completed the official RTL-to-GDS stages and produced every required physical artifact. Its runner then stopped before equivalence and power because an overbroad generic-cell predicate scanned escaped instance names. A legal SKY130 instance such as `sky130_fd_sc_hd__dfxtp_1 \dec_codeword_echo_o[0]$_SDFF_PN0_` contains Yosys lineage in its instance name but instantiates a technology-mapped SKY130 cell.

Amendment 02 anchors the predicate at cell-type position. It rejects module types beginning with `$_` or escaped `$`, while allowing arbitrary legal instance names. It does not change any netlist, RTL, physical artifact, source identity, SDC, seed, trace, hypothesis or threshold.

The amendment completes exact RTL-to-mapped and RTL-to-post-route equivalence, the three frozen activity-power analyses, and the full run validator on the already-preserved attempt2 physical outputs. Original attempt2 metadata and hashes remain unchanged; additive amendment metadata and a second raw-artifact hash manifest record the adjudication. No third physical run is performed for this administrative false positive.
