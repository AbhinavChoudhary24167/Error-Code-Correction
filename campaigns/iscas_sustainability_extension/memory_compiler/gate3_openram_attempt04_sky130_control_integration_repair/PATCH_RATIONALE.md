# Patch rationale

The only tested repair family is exact upstream SRAM commit `8dccd8d8ddb0a9de1b02207b2cd0c0d697807aa9`, whose subject is “update cells with lvs fixes.” This was the narrowest evidence-backed candidate after primitive bisection. It was applied only to copies of OpenRAM under the Attempt04 external work root; the installed PDK and baseline OpenRAM tree remained untouched.

P1 normalized eight LVS views. In the bitcell/dummy/replica views, commented PFET properties change from `w=0.07u l=0.095u` to `w=0.14u l=25n`. In `colend`/`colenda`, the special NFET changes from `w=0.07u l=0.21u` to `w=0.14u l=0.14u`. These exact upstream edits were necessary to test whether Netgen's device-property normalization was preventing equivalence.

P2 completed the exact upstream commit. It removed six `locali` and two `obsli1` rectangles from the dummy maglef and synchronized the ordinary bitcell SPICE's two commented PFET properties. These two files were necessary to ensure the negative result was not caused by testing only a subset of the upstream fix.

Both runs were negative. DRC remained 2,140; LVS remained FAIL; device/net counts were unchanged; and P1/P2 LVS reports are byte-identical. Therefore these edits are preserved as diagnostic patches, not accepted as a repair. No speculative edits followed.

Exact originals, patched files, unified diffs, and hashes are under `raw/patches/`. The local source copies were:

- `/var/lib/green-ecc-iscas-sustainability/gate3_openram_attempt04_sky130_control_integration_repair/source/OpenRAM-p1`
- `/var/lib/green-ecc-iscas-sustainability/gate3_openram_attempt04_sky130_control_integration_repair/source/OpenRAM-p2`
