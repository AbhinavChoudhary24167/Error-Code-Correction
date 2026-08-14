# Gate-03 fairness and constraint contract

Contract ID: `gate03-pilot-contract-v1`. This contract was frozen before comparative physical results.

- Technology/corner: SKY130HD, `sky130_fd_sc_hd__tt_025C_1v80`, TT, 1.80 V, 25 °C; acceptance requires validation from the pinned Liberty bytes.
- Pilot clock: 100 MHz (10 ns); uncertainty 0.5 ns; input/output delays 1 ns; input transition 0.2 ns; output load 0.05 pF.
- Limits: fanout 16, transition 1 ns, capacitance 0.2 pF.
- Floorplan: utilization 40%, aspect ratio 1.0, core margin 10 µm, placement density 0.55; exposed randomized-stage seed 42.
- Boundaries: clean registered-input/registered-output encoder, decoder, and direct encoder-to-decoder combined shells; identical valid treatment; no reset; one combinational codec stage; initiation interval one.
- Wrapper control: a direct wrapper-only control must report wrapper standard-cell area. Codec, wrapper, total, post-route cells, allocated core, and allocated die are separate quantities.
- Workloads: seed `0x475245454E454343`, 256 warm-up cycles, 8,192 measured cycles, VCD only during measurement. `normal-clean-random-v1` is primary. Single and double error energy are conditional only. `verification-stress-v1` (80/10/10) is verification-only and may not populate primary power.
- Timing misses: negative slack is `TIMING_ANALYZED_TARGET_MISS`, not automatic impossibility. A routed 10 ns layout may yield only a DERIVED `1000 / critical_path_delay_ns`; it is not called Fmax. A frequency sweep reruns the complete optimized flow per period.
- Physical checks are called ORFS/open-PDK checks, never foundry-signoff DRC/LVS.

These are bounded Gate-03 feasibility assumptions, not final paper constraints. No autotuning or result-dependent relaxation is allowed.
