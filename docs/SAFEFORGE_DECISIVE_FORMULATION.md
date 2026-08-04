# Fixed-Hsiao placement and syndrome-policy formulation

## Scope and identities

The production code is the existing systematic `(72,64)` equal-redundancy odd-column SEC-DED artifact `odd-column-secded-64-72`. Its 64 data columns have odd Hamming weight and its eight parity columns are the binary basis. This is the conventional Hsiao construction used by the repository; a coordinate or row-basis permutation is not a new code.

A physical placement is a map from each of the 64 physical data-bit positions to one of those 64 logical parity-check columns. The multiset of columns is invariant, parity positions 64–71 are fixed, and no mapping crosses a 72-bit word. The evaluated library contains identity, even/odd interleaving, 15 cyclic assignments, 63 adjacent swaps, and seven within-eight-bit-bank rotations after duplicate removal: 87 placements. The result is exact only over this declared library, not over all `64!` permutations or movable parity bits. Index displacement is a routing proxy, not routed wirelength.

The executable error universe is the union of four synthetic 72-bit artifacts: spatial hot spots, distribution shift, voltage sensitivity, and mixed SBU/DBU/MBU. It contains 427 distinct nonzero vectors. Probability outside that set is never assigned zero by the compiler; it is handled separately by the system-tail model.

## System-rate conversion

Let `Lambda_E` be the upper bound on relevant decoder fault events per system-hour and `p_SDC` the total conditional SDC probability per relevant event. Under the declared constant-hazard model,

`Lambda_SDC <= Lambda_E * p_SDC`, and `FIT_SDC = 1e9 * Lambda_SDC`.

The implementation accepts four noninterchangeable exposure definitions:

- a direct system event rate or system event FIT;
- protected words times an event rate per word-hour;
- protected words times bits per word times an event rate per bit-hour;
- disjoint system-wide word access and scrub opportunities times an event probability per opportunity.

The access/scrub form is rejected unless the caller declares the opportunities disjoint. A persistent upset must be modeled as a first-detection hazard; counting it again on every later access would be invalid.

For a mission failure target `P_M` over `T` hours, the constant-hazard target rate is `-log(1-P_M)/T`. For a direct FIT target it is `FIT_target * 1e-9` failures/hour. Thus the total conditional budget is

`epsilon_total = min(1, Lambda_target / Lambda_E)`.

If at most `eta` of event probability lies outside the executable universe and tail SDC is bounded by `b`, then

`p_SDC <= (1-eta) * p_support + eta * b`.

When `eta < 1`, the compiler budget is therefore

`epsilon_support = (epsilon_total - eta*b)/(1-eta)`.

It is infeasible if the numerator is negative. If either tail bound is absent, system projection fails closed: the upper total conditional SDC is one. The primary engineering point declares a 1-system-SDC-FIT target, 1000 system event FIT, `eta=1e-5`, and `b=1`. It yields `epsilon_total=0.001` and `epsilon_support=0.0009900099000990008`. These are engineering sensitivities, not quoted server or safety standards.

## Fixed-matrix robust action problem

Let `E` be the finite error universe, `s(e)=H e^T` its syndrome, and `Q` the configured ambiguity set. For each observed nonzero syndrome `s`, the finite action set contains abstention, every declared same-syndrome representative present in `E`, and the conventional single-bit fallback when it is declared physically available. An action is accepted only if its correction mask recomputes to `s`.

For action `a`, binary losses `L_SDC(e,a)` and `L_DUE(e,a)` are obtained by executing the correction and inspecting the residual data bits. With binary selector `x_sa`, the robust problem is

```text
minimize    t
subject to  sum_a x_sa = 1                         for each observed syndrome s
            sup_q sum_e q_e L_SDC(e,x) <= epsilon
            sup_q sum_e q_e L_DUE(e,x) <= t
            sum_sa cost_sa x_sa <= optional budget
            x_sa in {0,1}.
```

Zero-syndrome data errors are fixed SDC terms. Syndromes absent from the universe abstain and are outside the finite-support risk measure.

### Proposition 1 — finite-domain certificate and convergence

For a fixed binary matrix, finite error universe, finite action set per syndrome, and ambiguity set admitting exact linear-risk separation, adversarial constraint generation returns a feasible policy with robust DUE upper bound `U` and master lower bound `L`. `U-L` is a valid a-posteriori absolute optimality gap over the declared action domain. If the master and separation solves are exact, constraint generation terminates after finitely many distinct policies and a zero gap proves optimality in that domain.

Proof sketch: every robust-feasible policy satisfies every scenario cut, so the restricted master is a relaxation and its dual bound is a lower bound. Exact separation either certifies the selected policy or returns a distribution that excludes its underestimated SDC/DUE value. A violating selected policy cannot recur once its cut is enforced. The number of deterministic syndrome policies is finite. At termination the selected policy supplies `U`, the master supplies `L`, and weak duality gives `L <= OPT <= U`.

The master is a multiple-choice binary program and is NP-hard in the general risk-budget form. Loss construction is `O(|A||E|)`. The implementation supports exact separation for total variation, structured source/region intervals, and the repository’s declared geometry-Wasserstein ground metric. The latter is defensible only when its geometry metadata matches the actual device mapping.

### Corollary 1 — stringent total-variation decomposition

For binary SDC loss under TV radius `delta`, any nonempty, nonuniversal loss set has worst-case risk `min(1, nominal_risk + delta)`. Consequently, when `epsilon < delta`, every deployable action combination must have zero SDC loss on the complete finite support. The optimum is obtained by selecting, independently for each syndrome, a zero-SDC correction when one exists and abstaining otherwise; worst-case DUE follows from the exact TV certificate. This branch is linear after loss construction and has no MILP trust dependency.

The primary point has `epsilon_support ≈ 0.00099 < delta=0.05`, so this corollary applies. The independent verifier rebuilds the action domain and losses, verifies that no zero-SDC correction was omitted, checks the TV primal/dual certificates without solver state, and re-derives the zero gap.

## Placement co-design and strong sequential baseline

For each allowed placement, SafeForge evaluates the conventional decoder and compiles the exact robust policy. Joint selection minimizes certified DUE, then nominal DUE, then displacement. Exact selection over 87 rows has zero library gap.

The strong sequential baseline first chooses a placement without choosing decoder actions: it maximizes nominal mass in syndrome groups that admit a support-universal representative, then applies the exact policy compiler. Under `epsilon < delta`, this placement-only collision objective is the same separable structure exposed by Corollary 1. It is deliberately strong and prevents a weak conventional-decoder placement tie from manufacturing a joint-design gain.

## Limitations

- The 427-vector universe and TV radius are synthetic engineering artifacts, not statistically calibrated experimental coverage.
- The `1e-5` tail bound and 1000-event-FIT exposure are declared sensitivities without measurement confidence.
- Global placement optimality, movable parity placement, routed displacement, memory-macro layout, and metadata-routing costs are unsolved.
- A policy certificate does not cover the outside-support tail; deployment requires the separately hashed system budget and tail statement.
- The formulation is new work in this phase; Hsiao coding theory, matrix equivalence, prior SafeForge ambiguity solvers, RTL generation, and scheduler gating are earlier work.
