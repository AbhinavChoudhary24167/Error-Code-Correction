# GREEN-ECC / SafeForge code-equivalence audit

This audit is a claim boundary, not a novelty argument. A parity-check matrix is not called a new ECC merely because its rows, columns, physical placement, or syndrome table differ.

The machine-readable audit is `reports/safeforge_study/all_code_equivalence_audits.json`; reproduce it with:

```text
python scripts/run_code_equivalence_audit.py
```

## Equivalence groups and invariants

For each unique generated matrix discoverable in `reports/**/*.json`, the checker records rank, exact dual weight enumerator, exact primal weight enumerator via the binary MacWilliams transform, minimum distance, column-weight multiset, syndrome collisions, corrected coset leaders, unmapped/detect-only syndromes, and the physical bit-to-column assignment.

For redundancy `r <= 4`, it exhaustively enumerates every element of `GL(r,2)` and decides equivalence under:

1. invertible parity-check row operations plus arbitrary column permutations;
2. row operations plus separate data-column and parity-column permutations;
3. row operations plus the identity/reversal automorphisms of a physical path;
4. row operations plus every rectangle automorphism (reflections, and rotations/transposes when square).

For `r = 8`, exhaustive `GL(8,2)` enumeration is computationally inappropriate. Those reports therefore use exact algebraic invariants and family criteria, and mark permutation-equivalence undecided instead of treating invariant agreement as proof. Geometry is the declared 8-by-9 physical layout. Linear adjacency is the declared bit order `0..n-1`.

## Results

Ten distinct matrices are retained in the current generated reports.

| Matrix / role | Parameters | Exact d | Classification | Relation to equal-redundancy reference | Novelty conclusion |
|---|---:|---:|---|---|---|
| `odd-column-secded-4-8` | (8,4) | 4 | extended Hamming; minimum-total-ones Hsiao SECDED | reference | known code |
| `forge-hotspot-8-4-v1` | (8,4) | 4 | extended Hamming; minimum-total-ones Hsiao SECDED | exactly equivalent under row operations plus arbitrary columns and under separate data/parity permutations; not equivalent under the declared path or 2-by-4 geometry groups | **not a new linear code** |
| `safeforge-robust-8-4-v1` | (8,4) | 3 | shortened-Hamming SEC matrix with abstaining policy; not SECDED | exactly inequivalent to the (8,4,4) reference, including arbitrary columns | different shortened code, but no code-family novelty claim |
| `odd-column-secded-64-72` | (72,64) | 4 | odd-column SECDED; not minimum-total-ones Hsiao because it includes heavier columns while lighter odd columns are unused | reference | known construction |
| `safeforge-robust-72-64-mapping-v1` | (72,64) | 4 | physical permutation of the odd-column SECDED reference with an abstaining table | large-`r` algebraic equivalence undecided by the bounded checker; construction records the permutation origin | known construction/mapping heuristic |
| spatial hardware-aware portfolio matrix | (72,64) | 4 | minimum-total-ones Hsiao SECDED | large-`r` equivalence undecided; exact enumerators retained | known construction class |
| geometry hardware-aware portfolio matrix | (72,64) | 4 | minimum-total-ones Hsiao SECDED | large-`r` equivalence undecided | known construction class |
| spatial joint portfolio matrix | (72,64) | 4 | minimum-total-ones Hsiao SECDED | large-`r` equivalence undecided | known construction class |
| one-general portfolio matrix | (72,64) | 4 | minimum-total-ones Hsiao SECDED | large-`r` equivalence undecided | known construction class |
| `forge-spatial-hotspot-72-64-v1` | (72,64) | 3 | shortened-Hamming SEC matrix; not odd-column SECDED | large-`r` equivalence undecided | no code-family novelty claim |

All ten have block length different from the repository's BCH(63)-derived implementation, so they are not equivalent to that code by block length. None satisfies SEC-DAEC or TAEC correction separation under the current linear physical adjacency. The exact capability checks and decoder-coverage flags are in the machine report.

### Exact (8,4) finding

The generated columns are `[11,14,7,13,1,2,4,8]`; the baseline columns are `[7,11,13,14,1,2,4,8]`. Both contain all eight odd-weight four-bit columns. Both have primal weight enumerator

```text
1 + 14 z^4 + z^8
```

and minimum distance four. The exact `GL(4,2)` checker finds equivalence immediately with the identity row transform and a data-column permutation. This confirms the suspected extended-Hamming/Hsiao equivalence.

The nominal zero-SDC corrected probability rises from `0.48` for the conventional baseline table to `0.91` for the generated artifact on the small synthetic PMF. That gain is attributable to:

- physical/data-column placement within a known code;
- a probability-aware syndrome-to-error table that adds selected double-error coset leaders;
- the finite modeled error universe and its PMF.

It is not attributable to a new linear code. Exhaustively optimizing the known Hsiao code's four data-column placements recovers the generated ordering `[11,14,7,13]`; under the robust abstaining policy this changes nominal correction from `0.11` to `0.55` and worst-case DUE from `0.99` to `0.55` at TV radius 0.1. This is a physical mapping/policy result.

### Robust co-synthesis finding

SafeForge's exact small-code search selects an `(8,4,3)` shortened-Hamming matrix with a zero-SDC abstaining policy. It is exactly inequivalent to extended Hamming under arbitrary column permutations, but that does not establish a new family: shortened-Hamming SEC codes are known. Its value here is the certified syndrome partition for a declared support, not algebraic novelty.

## Improvement attribution rule

Every reported improvement must use exactly one of these labels:

- `inequivalent_linear_code`, only after the relevant exact group says false;
- `known_code_permutation`;
- `physical_column_mapping`;
- `syndrome_policy_change`;
- `probability_aware_coset_leader_selection`;
- `different_error_universe_or_pmf`;
- `invalid_comparison`, when experiment identifiers differ.

The current SafeForge claim relies on policy certification, physical mapping, and a verified small matrix-policy search. It does not claim a new ECC family.

## Limits

- `r=8` arbitrary-column equivalence remains undecided unless a dedicated canonical binary-matroid isomorphism implementation is added.
- Weight enumerators are exact but are not sufficient equivalence proofs.
- Physical equivalence depends on the declared SRAM layout and adjacency graph.
- No BCH derivation is inferred from a matching spectrum alone.
