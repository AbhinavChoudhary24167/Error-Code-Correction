# DATE 2027 breadth-remediation campaign status

| Gate | Status | Evidence |
|---|---|---|
| `G0_REPOSITORY_BASELINE_PRESERVED` | PASS | Stage-0 audit recorded clean `main` at `b51291442bbd04346dac939dea6ba7d532b9c5c4`; work proceeded on `codex/date-2027-breadth-remediation`. |
| `G1_STRUCTURAL_PAIR_PLAN_FROZEN` | PASS | `A_structural_pair_plan.md` SHA-256 is frozen in `00_plan_freeze.sha256` and matches. |
| `G2_STRUCTURAL_PAIR_FORMAL_EQUIVALENCE` | PASS | Arbitrary-word exhaustive decoder SAT and registered-boundary temporal induction both pass with zero alignment. |
| `G3_STRUCTURAL_PAIR_SYNTHESIS_DISTINCTNESS` | PASS | Common-policy mapped cell histograms, graph signatures, netlist hashes, and cell counts differ; register counts are equal. |
| `G4_STRUCTURAL_PAIR_5SEED_PHYSICAL_CAMPAIGN` | PASS | Ten fresh, interleaved routes over exactly seeds 11, 13, 17, 19, and 23 completed; both identities are feasible 5/5 and have joined power evidence. |
| `G5_POWER_DECOMPOSITION_REPRODUCES_BASELINE` | PASS | All ten historical power records are hash-joined; published total power and energy/op reproduce; displayed component/group arithmetic is within the declared 1e-8 W precision bound. |
| `G6_SECOND_TIMING_TARGET_PLAN_FROZEN` | PASS | `C_timing_condition_plan.md` predeclares 5 ns and its SHA-256 in `00_plan_freeze.sha256` matches. |
| `G7_SECOND_TIMING_TARGET_5SEED_CAMPAIGN` | PASS | Ten fresh, interleaved 5 ns implementations completed without retries or substitutions; both architectures are setup/hold/route feasible 5/5 and power-eligible. |
| `G8_EXISTING_TEST_SUITE_PRESERVED` | PASS | Final `make test`: 484/484; final repository-wide pytest: 486/486; counts equal Stage 0. |
| `G9_HISTORICAL_REV2_HASH_INTEGRITY` | PASS | Final SHA-256 audit matches all 2,445 protected files with zero changed, missing, or added protected paths. |

