# U0 Attempt06 route-failure root cause

The Attempt06 U0 failure signature was reproduced by a fresh replay and cross-correlation of its complete retained global-route, detailed-route, congestion, ODB and macro-LEF evidence before finalizing the new policy. This avoided modifying or replacing frozen Attempt06 artifacts. Global routing eventually reported zero overflow, but detailed routing did not converge: completed iterations contained 2,338, 1,784, 1,523, 886, 696, 632, 613, 602, 567, 549, 378, 278, 221, 203, 176, 150, 144 and finally 243 violations. The best observed iteration was therefore 144, not a clean route. Exact source paths and SHA-256 values are in `raw/root_cause/attempt06_u0_failure_trace.json`.

The primary mechanism was floorplan geometry expressed as macro pin accessibility and macro-to-boundary/IO/PDN interaction. The 690.12×291.64 µm data macro was at `(10.26, 21.18) MY`. Its signal pins, all on one LEF edge, faced the lower boundary with only about 21 µm to the die edge and about 11 µm to the core edge. Auto-distributed IO pins and the lower met3/met4 PDN structures forced dense pin escapes into this narrow strip. Violation inspection localized the persistent short/spacing/via conflicts to this integration-created escape region; representative congestion bounds were approximately x=510–558 µm, y=179–303 µm. The 205,137 µm global-route wirelength and only 458 vias did not indicate exhaustion of full-chip metal capacity.

The other hypotheses were checked as follows:

- placement density and total routing layers were not primary: global routing reached zero overflow and met1–met5 were available;
- the SRAM macro itself was functionally and interface qualified and no internal geometry changed;
- antenna was not the convergence blocker;
- clock routing was trivial because U0 has one macro clock sink;
- tap/endcap placement did not produce the persistent marker cluster;
- the common PDN did contribute an obstruction interaction locally, but only because the signal pins had insufficient escape depth;
- high fanout and generic global congestion were not the dominant pattern.

The controlled correction was not blind die enlargement. Attempt07 rotates the data macro to `MX`, moves it to `(30.36, 31.23)`, gives it a 20 µm halo, places all IO signal pins on the top edge, and provides open interior escape space. The same data-macro placement, IO rule, halo, PDN, placement target and routing algorithms are used in E0. With that policy U0 seed 11 reached zero final detailed-route DRC at 22,186 µm wirelength and 1,084 vias, and all five U0 seeds completed cleanly.

The surviving maximum-transition reports are timing/Liberty limitations, not route DRC. Raw Attempt06 reports remain frozen in the Attempt06 campaign; Attempt07 reproduction/configuration and final congestion/routing evidence are under `raw/openroad/work`.
