# GREEN Matrix 3.1 physical-population final report

## Outcome

This additive campaign preserves GREEN Matrix 3.0 at `affc8145b184803189dac36391cb486f00e7b4f8` and
adapts existing reproducible U0/E0 evidence into v3.1-compatible records.  It
adds **262** evidence records: {'E0': 110, 'E3': 42, 'E4': 110}.  No E5,
E6, or E7 quantity was established.  Equations and executable guards are
validated independently of parameter availability.

Final classification:
`GREEN_MATRIX_V3_1_PHYSICAL_POPULATION_PARTIAL_E4_E3_PHYSICAL_SDC_DUE_BLOCKED`.

The methodology is methodologically informed by publicly available imec
SSTS/imec.netzero bottom-up semiconductor sustainability methodology.  This is
not imec certification, compliance, endorsement, or standardization.

## Required questions

1. **Which v3 quantities became newly populated?** Five matched physical-flow
   observations per U0/E0 architecture now carry implementation, netlist,
   configuration, constraint, workload, and activity hashes; route area,
   wirelength, vias, setup/hold slack, vectorless power components, macro-level
   geometry, deterministic activity traces, one partial-annotation diagnostic
   energy/service value, and RTL service latency/II are populated.
2. **Which measurements reached E5?** None.  The E5 count is zero.
3. **Which remained E4/E3/E2/E1/E0?** New records contain E4 post-route
   diagnostics, E3 RTL/analytical service and activity semantics, 5 E2
   literature datasets in native mismatched boundaries, no E1 parameter values,
   and E0 structural missingness for physical rates, Qcrit, bitcell mapping,
   nontrivial interleaving, lifecycle carbon, CSCI, and MRCC.
4. **Was matched post-route energy established?** A matched seed-11 diagnostic
   energy per requested service was derived from partial-annotation post-route
   power and the 512-service/5.12 us trace.  Qualified activity-complete E5
   energy was not established.  Read, write, correction, retry, and scrub energy
   remain unavailable; the diagnostic total is not lifecycle energy.
5. **Was service latency established?** Yes at E3 inside the RTL service
   boundary: one synchronous 10 ns cycle for normal and corrected reads.  A
   post-route analog/service-latency distribution was not measured.
6. **Was initiation interval separately established?** Yes, one cycle at E3.
   The nominal initiation capacity is 100 million services/s and is not called
   maximum sustainable throughput.
7. **Was SRAM geometry established?** Only macro origin/orientation/extent and
   electrical array organization were established.  Bitcell xy coordinates and
   address/column-select-to-cell mapping remain unavailable.
8. **Was Qcrit estimated?** No.
9. **What exactly does Qcrit establish and NOT establish?** A defensible Qcrit
   would establish conditional circuit susceptibility at a declared node, PVT,
   state, and injection waveform.  It would not establish particle flux,
   spectrum, charge deposition/collection distribution, topology probability,
   SER, FIT, SDC, or DUE.
10. **Which SBU/MBU literature datasets were collected?** Pieper 5-nm SRAM,
    Perez-Celis/Wirthlin FPGA neutron MCU, Ibe CORIMS scaling, Yahagi 130/180-nm
    neutron MCU, and the NASA Kintex UltraScale heavy-ion report.
11. **Which are technology-matched?** None is independently matched to SKY130
    SRAM22 geometry/process/PVT.
12. **Which are technology-mismatched?** All 5 records.
13. **Was any literature numeric value transferred to SKY130?** No.
14. **Was any physical event-rate model qualified?** No.
15. **Can physical SDC now be calculated?** No: `PHYSICAL_SDC_DUE_BLOCKED`.
16. **Can physical DUE now be calculated?** No: `PHYSICAL_SDC_DUE_BLOCKED`.
17. **Can FIT now be calculated?** No.  Logical mask frequency is never used as
    an event rate.
18. **Was an interleaver physically implemented?** No nontrivial interleaver.
    I0 is the routed baseline; I1/I2 remain explicit proposals.
19. **What physical overhead did it incur?** I0 has zero added interleaver
    overhead by definition.  I1/I2 area, routing, buffers, energy, latency,
    timing, and congestion are unavailable.
20. **Can any reliability benefit be attributed to it?** No.
21. **What remains structurally missing?** Complete bitcell geometry/mapping,
    calibrated SKY130 SBU/DBU/MBU topology/rate data, Qcrit, activity-complete
    post-route power with disjoint operation attribution, saturated throughput,
    a routed interleaver, SKY130 manufacturing inventory, and lifetime policy.
22. **What is the new highest-value measurement?** A fluence-linked particle
    experiment on the matched SRAM implementation that releases event
    coordinates and is joined to a verified bitcell/logical mapping.
23. **Can CSCI now be populated?** No.
24. **Can MRCC now be populated?** No.
25. **Is any sustainability Pareto frontier qualified?** No.  The emitted exact
    front is `DIAGNOSTIC_FRONT` only.
26. **Is any architecture winner qualified?** No:
    `NO_GLOBAL_WINNER_QUALIFIED`.
27. **What claims are now appropriate for ISCAS?** An evidence-aware cross-layer
    method; a reproducible five-seed matched physical baseline; explicit power,
    energy, latency, and II separation; macro-geometry recovery; a physical
    topology-to-decoder interface; technology-mismatch guards; and exact gated
    diagnostic enumeration.
28. **What claims remain forbidden?** E5 energy, silicon/radiation validation,
    absolute SKY130 SDC/DUE/SER/FIT, Qcrit, physical interleaver benefit, absolute
    manufacturing/lifecycle carbon, CSCI/MRCC, a sustainability-qualified Pareto
    front, imec endorsement, or any global architecture winner.

## Scientific interpretation

The campaign advances population, not outcome certainty.  The correct causal
path remains physical event topology -> logical corruption -> ECC/interleaving
response -> correct service -> operational resource cost -> lifecycle scenario.
The first physical probability term is still missing, so downstream physical
reliability and sustainability selection remain blocked.
