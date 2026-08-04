# Bit-exact FPGA/SRAM acquisition protocol

No hardware measurement is fabricated in this repository. The exact human experiment still required is:

1. Choose a board/device and freeze the bitstream, BRAM/SRAM instance, ECC mode, 72-bit word definition, and physical-to-logical/interleave map. Record part, board serial, tool/bitstream hashes, memory coordinates, and ownership/license terms.
2. Predeclare voltage points, temperature points, radiation source/fluence or controlled injection mode, repetitions, write patterns, scrub/read period, event-association window, and independent grouping by device/run/source.
3. For each trial, write the known pattern, establish the condition, read and timestamp the complete memory, compare with the golden image, record every flipped cell before correction, restore state, and repeat. Do not merge persistent reads into independent events.
4. Store one CSV row per flipped bit using `data/fault_evidence/fault_map_template.csv`. `trial_id,event_id,word_address` define one 72-bit event vector. Physical coordinates and logical bit positions are both mandatory.
5. Copy and complete `configs/experimental_campaign.template.json`. Use explicit redistribution terms; do not label a restricted dataset redistributable.
6. Validate and hash the campaign:

   `python scripts/prepare_safeforge_campaign.py --csv RAW.csv --campaign CAMPAIGN.json --outdir OUT --holdout-field device_id`

The adapter rejects out-of-range bits, non-flips, duplicate bits within an event/word, mixed campaign IDs, and changing event metadata. It emits a conditional nonzero-event PMF, exact Clopper–Pearson/Bonferroni intervals, controlled replay vectors, input/content hashes, and leave-one-device/source/independence-group-out splits with retuning disabled.

The adapter does not estimate event FIT or the unobserved tail. Those require exposure denominators: device-hours or fluence, number of protected words/bits, access/scrub opportunities where relevant, detection efficiency, zero-event trials, and a sampling model. The primary scientific rerun must replace the 1000-FIT and `1e-5` engineering assumptions with upper confidence bounds derived from those denominators.

For controlled replay, load each emitted `positions` vector into the declared word through the board-specific injector, decode with the frozen generated policy, and record corrected/DUE/SDC plus latency. Keep injected replay (evidence level B) separate from naturally observed raw events (level A). Train/compile on all but one device/voltage/source group; evaluate the held-out group once without target, radius, placement, or policy retuning.
