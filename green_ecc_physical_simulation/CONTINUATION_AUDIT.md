# GREEN-ECC-PHY continuation audit

**Date:** 2026-08-04 (Asia/Calcutta)  
**Scope:** additive multi-ECC exact-functional and analytical software simulation.

## Preserved checkpoint

No committed or uncommitted work was reset, restored, cleaned, stashed, committed, or pushed. The original Hsiao, conventional SECDED, bounded TAEC, bounded SEC-DAEC, and cyclic/BCH-labelled identities remain present. The historical cyclic implementation and SEC-DAEC implementation remain rejected with their earlier counterexamples. Hsiao/positional equivalence remains unestablished. The external repetition fixture remains excluded from scientific conclusions.

The earlier physical-capability decision is unchanged: there is no usable PDK/library/corner/activity-backed physical flow. Local Yosys is structural-only evidence. All physical metrics and the physical winner remain null.

## Repository-wide ECC search result

The scan covered RTL, Python, C/C++, manifests, generated matrices, tests, archived reports, and documentation. It found and classified 30 registered or grouped artifact candidates in the machine/human scope matrices. Fifteen distinct matrices/codeword sets are registered as mathematical specifications; 17 deployed implementation policies are registered.

Newly registered complete artifacts include four mathematically valid BCH specifications and eight archived SafeForge/CodeForge G/H plus syndrome-table policies. Grouped generated SECDED, TAEC, SEC-DAEC, BCH-labelled, and Polar RTL remains explicit in the inventory, with experimental/rejected/duplicate status and reasons. No (75,64)-I6/I7 construction was found. LDPC and Reed–Solomon appear only in documentation/literature references.

## Mathematical and functional changes

`green_ecc_phy/bch.py` adds primitive-field validation, generator construction from consecutive roots, systematic encoding, correct parent-coordinate shortening, GF syndromes, and a deterministic bounded locator. The valid BCH generator differs from the preserved invalid RTL polynomial.

The verification report now records malformed inputs, exact outcome counts and fractions, data-independence proof coverage, and implementation-specific capability claims. Results include:

- valid BCH (63,51,t=2): 2,016/2,016 masks corrected through weight two, exact d=5;
- shortened BCH t=1: 71/71;
- shortened BCH t=2: 3,081/3,081;
- shortened BCH t=3: 102,425/102,425, designed d>=7;
- TAEC: shared SECDED universe passes, adjacent triples 0/62 corrected and 62/62 silently miscorrected;
- SEC-DAEC: 302/2,556 double silent miscorrections and 53/63 adjacent-pair silent miscorrections;
- historical cyclic: 33/63 single silent miscorrections.

## Analytical study and evidence gates

The preregistered 192-scenario grid is deterministic and fully feasible. Five implementations win scenario regions, fixed baselines have non-zero analytical regret, and the worst swept energy-parameter model preserves 190/192 winner identities. The conclusion rule therefore returns `scenario_aware_selection_supported_within_analytical_model`.

The adaptive result is only a parameterized symbolic threshold because MUX, controller, metadata, transition, and re-encoding costs are absent. No actual or physical break-even is reported.

- `framework_and_extensibility_gate`: PASS.
- `functional_and_analytical_simulation_gate`: PASS.
- `physical_scientific_result_gate`: FAIL.

## Outputs

The catalogue builder deterministically emits schemas/manifests, BCH certificates, and the preregistration. The evaluation emits exact profiles, normalized metrics, capability and architecture matrices, 192 scenario records, Pareto/regret analysis, uncertainty/sensitivity results, plots, and three independent gate decisions under `green_ecc_physical_simulation/multi_ecc_evaluation`.

Required reproduction:

```text
python scripts/build_multi_ecc_catalogue.py
python scripts/run_multi_ecc_framework_evaluation.py
make
make test
python -m pytest -q
```
