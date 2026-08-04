# SafeForge observability and evidence novelty gate

**Decision date:** 2026-08-04  
**Gate outcome:** **FAIL -- preserve the negative study and stop implementation expansion.**

The proposed theory is useful as a code-independent organization of the SafeForge
negative result, but the central statements are direct specializations of established
syndrome decoding, Bayes decision with rejection, zero-error/confusability graphs,
linear-code separation, distributionally robust expectation, and exact rare-event
statistics. The literature audit found no theorem that is both nontrivial and stronger
than those foundations. Consequently, the conditional broad benchmark and phase-diagram
work in the brief is not authorized by this gate.

## 1. Corrected observability statement

Let the alphabet be `F_q`. Let `H : F_q^n -> F_q^r` be the syndrome
map, `D : F_q^n -> F_q^k` the data projection, `E` the declared
certification universe, and `P` a probability law on `E`. Errors and correction
masks are additive. At syndrome `s`, the decoder may choose an available mask
`a in A_s` or abstain. A pure correction mask returns data without a second
independent verification observation.

For errors in the same syndrome fiber, define

```text
e ~_D e'  iff  D(e - e') = 0.
```

This is action-independent correction-equivalence: a mask `a` corrects the data
for both errors exactly when `D(e-a)=D(e'-a)=0`. Thus each fiber
`E_s={e in E: He^T=s}` is partitioned into classes
`K_s,j` having a common data effect `D(e)`. A class is available-correctable if
some `a in A_s` has that data effect. Multiple masks with the same data effect
belong to the same decision class; their latency, energy, or recovery cost may differ,
but their observability does not.

### Proposition O1 -- deterministic zero-SDC capacity

If abstention is available, an accepted action has no post-correction verifier, and
zero SDC is required for every error in the declared certification set `E`, then

```text
C_safe^0(H,D,P,E,A)
  = sum over s for which E_s has exactly one correction-equivalence class
      and that class is available-correctable of P(E_s).
```

If safety is required only on `supp(P)`, replace `E_s` by its positive-mass
part. That weaker convention must be stated because zero-probability members of a
certification universe otherwise still constrain the decoder.

Proof: if a fiber has two data-inequivalent errors, any accepted mask corrects at most
one class and silently corrupts the other. A syndrome-only decoder cannot accept one
and abstain on the other. It must therefore abstain on the whole fiber. Conversely,
a mask for a singleton class safely accepts the whole fiber. Summing the accepted
fiber masses proves the result.

The identity proposed in the brief,

```text
sum_s max_j P(K_s,j),
```

is **not** zero-SDC safe-correction capacity. It is the maximum nominal probability
of a correct data decision when the decoder selects one class in every fiber and
miscorrections of all other classes are allowed. It is a finite Bayes/MAP accuracy
identity. It coincides with zero-SDC capacity only when every positive/safety-relevant
fiber has at most one class, or when an additional verifier can reject every losing
class after the attempted correction. The latter changes the observation model.

Example: a syndrome with class masses `0.98` and `0.02` contributes `0.98` to
the proposed sum, but contributes zero to zero-SDC capacity. Correcting the first class
causes SDC on the second; zero SDC requires rejecting the entire syndrome.

### Edge cases and scope

- **Zero syndrome.** A data-visible `e in ker(H)` is indistinguishable from a clean
  read. If clean reads are in the operational universe, accepting/no-op causes SDC on
  that error; a nonzero correction corrupts clean reads; and abstention makes every
  clean read a DUE. A fault-conditioned analysis that omits clean reads hides this
  availability cost.
- **Parity-only residuals.** They are exactly errors in `ker(D)` and share the
  no-data-change class. They are harmless only if that class is not mixed with a
  data-visible class in the same observation fiber. Systematic form alone should not
  be used as a substitute for checking `ker(H) intersect ker(D)`.
- **Multiple masks.** Masks are distinct for observability only through their data
  effects or through an independent outcome/verification signal. Merely adding more
  same-syndrome masks does not remove a collision.
- **Fallback.** Reread, CRC, erasure flags, analog confidence, or protected location
  information refine the observation to `(s,z)` and can change the theorem. A fallback
  that sees only `s` is just another action and cannot distinguish a fiber.
- **Nonbinary codes.** The statement holds over `F_q`; subtraction replaces XOR.
- **Nonbinary loss and recovery weighting.** O1 is a zero-one safety statement. With
  severity `l(e,a)` or recovery cost `w(e)`, optimize expected loss directly; probability
  mass alone is no longer the capacity metric.

### Proposition O2 -- randomized risk-coverage frontier

Let `p_sj=P(K_s,j)`. At syndrome `s`, let `x_sj` be the probability of
choosing the action for class `j`, let `u_s=sum_j x_sj`, and abstain with
probability `1-u_s`. For an error in class `k`,

```text
Pr(correct | s,k) = x_sk
Pr(SDC     | s,k) = u_s - x_sk
Pr(DUE     | s,k) = 1 - u_s.
```

These equations give the entire nominal frontier by a linear program, and a robust
frontier by replacing the two expected losses with the support functions of the chosen
ambiguity sets. Randomization cannot improve the zero-SDC point: in a fiber with two
or more positive/safety-relevant classes, all `u_s-x_sk` can be zero only when
`u_s=0`. For a positive SDC budget, however, randomized boundary decisions can
strictly interpolate or improve on deterministic points. It is therefore not valid to
dismiss randomization as categorically inappropriate; it must be included in the
frontier or excluded by an explicit implementation/safety standard.

This is a direct finite specialization of Bayes classification with rejection. Chow
derived the optimum error-reject tradeoff in 1970, and Franc, Prusa, and Voracek proved
in 2023 that bounded-risk and bounded-abstention formulations use a randomized Bayes
selection rule ([Chow 1970](https://research.ibm.com/publications/on-optimum-recognition-error-and-reject-tradeoff),
[Franc et al. 2023](https://www.jmlr.org/papers/v24/21-0048.html)).

## 2. DUE lower bounds and incomplete support

Let `B` be the union of fibers that O1 forces the decoder to reject, including
singleton fibers without an available safe action. With unit DUE loss, every
zero-SDC policy has nominal

```text
DUE(P) >= P(B),
```

with equality when every fiber outside `B` can be safely accepted. With recovery
weights, the corresponding bound is `E_P[w(e) 1_B(e)]`.

### Total variation

Use `TV(Q,P)=sup_A |Q(A)-P(A)|=(1/2)||Q-P||_1`. For a full TV ball of
radius `delta` over the same finite universe,

```text
sup_Q Q(B) = 0                              if B is empty,
             1                              if B = E,
             min(1, P(B) + delta)           otherwise.
```

Thus this is the exact worst-case DUE lower bound for binary unit loss. For a
deterministic binary SDC loss with a nonempty loss set, worst-case SDC is at least
`delta`. Therefore `epsilon < delta` forces zero SDC on every member of the declared
support.

That implication fails when the ambiguity set cannot move mass into the loss set;
when the decoder is randomized and per-error loss is fractional; for nonbinary or
severity-weighted loss; under the convention `||Q-P||_1<=delta` (which changes the
factor by two); when the tail is outside the TV universe; or when fallback supplies a
richer observation. It also says nothing about errors outside `E`.

### Structured intervals

For `l_i <= q_i <= u_i`, `sum_i q_i=1`, and no other constraints,

```text
sup_Q Q(B) = min(sum_{i in B} u_i,
                 1 - sum_{i not in B} l_i),
```

assuming the interval system is feasible. Source, device, region, multiplicity, or
other aggregate constraints require the exact linear program `max q(B)` subject to
all constraints. There is no universal scalar closed form. Recovery-weighted loss is
the same LP with coefficients `w_i 1_B(i)`.

### Geometry-Wasserstein uncertainty

For ground cost `d`, radius `rho`, and bounded loss `l`, Kantorovich/DRO duality gives

```text
sup_{Q: W_d(Q,P)<=rho} E_Q[l(e)]
 = inf_{lambda>=0} {
       lambda*rho
       + E_{e~P}[ sup_{e'} (l(e') - lambda*d(e,e')) ]
   }.
```

For `l=1_B`, this moves nominal mass into `B` in increasing order of its transport
distance. The answer depends on the declared geometry and is not `P(B)+rho` in
general. This is a direct instance of established Wasserstein DRO duality
([Mohajerin Esfahani and Kuhn 2018](https://optimization-online.org/wp-content/uploads/2015/05/4899.pdf)).

### Outside-support mass `eta`

If the conditional tail probability is at most `eta` and tail SDC is independently
bounded by `b`, then

```text
p_SDC <= (1-eta) p_SDC,support + eta*b.
```

Without a justified `b`, the worst tail is fully unsafe. More strongly, if the tail may
contain any vector and `ker(H)` contains a vector `v` with `D(v) != 0`, then every
accepted syndrome has an indistinguishable data-incompatible tail error: add `v` to
any representative. An adversary can put all tail mass on such an error. Hence an
unrestricted tail of mass `eta` contributes up to `eta` SDC to any policy that accepts
at least one reachable syndrome. Universal zero SDC requires abstaining on every
syndrome the tail can occupy; for an unrestricted additive tail, that is all syndromes.

The often-used fail-closed bound

```text
DUE >= (1-eta) P(B) + eta
```

is achievable only if tail membership or every tail-reachable observation can be
identified and rejected without also rejecting supported errors. A syndrome-only
decoder generally has no such membership oracle. Incomplete support is therefore not
just another scalar penalty; it can destroy selective availability.

## 3. Information deficit

Create one vertex for each correction-equivalence class `(s,j)`. Join two vertices
when they share the same existing observation and require incompatible corrections.
For the additive projection model, this graph is a disjoint union of cliques, one per
syndrome; more general action compatibility may require a hypergraph.

### Arbitrary protected side information

If a noiseless protected side label has `R` values, its labels must properly color the
conflict graph. Therefore

```text
R >= chi(G),                  b >= ceil(log2 chi(G)).
```

For target accepted mass `q`, the exact one-shot arbitrary-label lower bound is

```text
b_arb(q) = ceil(log2 min_{U: P(U)>=q} chi(G[U])),
```

where `U` ranges over the classes that will be accepted. This is the classical
zero-error confusability-graph reduction, not a new ECC theorem
([Witsenhausen 1976](https://doi.org/10.1109/TIT.1976.1055607)).

### Linear parity-row augmentation

Let

```text
V = {e-e' : e,e' in E, He^T=He'^T, D(e-e') != 0}
```

be the set of conflicting differences. Additional noiseless linear observations
`Ae^T` separate every declared conflict exactly when

```text
ker(A) intersect V = empty.
```

Writing `C=ker(H)`, the minimum number of independent extra linear observations is

```text
t_lin = min_A rank(A restricted to C)
        subject to ker(A) intersect V = empty

      = dim(C) - max_{K <= C, K intersect V = empty} dim(K).
```

For the complete ambient error universe, let `N=C intersect ker(D)`. Separating every
data-inequivalent pair is equivalent to `ker(A restricted to C) <= N`, and the exact
answer reduces to

```text
t_lin = dim(C/N) = rank(D restricted to C).
```

For a finite pattern set, candidate parity rows give a hitting-set formulation: a row
`a` covers conflict `v` when `a v^T != 0`; selected rows must cover all of `V`.
Locality/implementation restrictions make this a set-cover problem with a linear-matroid
rank condition. These are reformulations of standard syndrome separation and linear
algebra. A customizable-ECC tool already searches `H` so that all declared correctable
patterns have different syndromes ([Li et al. 2021](https://e-archivo.uc3m.es/rest/api/core/bitstreams/28d4ca47-276f-4d69-b382-609558aa04d9/content)).

The chromatic bound can be strictly weaker than the linear bound. With no initial
observation, take the 29 binary patterns of weight at most two in seven coordinates.
An arbitrary label needs five bits because `ceil(log2 29)=5`. A linear five-bit label
would have a two-dimensional kernel code of length seven and minimum distance at least
five, but such a binary `[7,2,5]` code violates the Griesmer bound. Six linear bits
suffice (the one-dimensional repetition kernel). This is a useful warning against
equating coloring with linear realizability, but it is a direct classical code-bound
example, not a new theorem.

Additional stored check bits are not automatically noiseless side information. If they
can fail, their physical positions and failure patterns must be added to `E` and the
conflict analysis repeated. Erasure/location metadata has value only to the extent that
it is observed and protected; error-and-erasure decoding already formalizes the benefit
of known locations ([Evain, Savin, and Gherman 2013](https://doi.org/10.1109/ETS.2013.6569371)).

For spatial interleaving, define a physical co-upset hypergraph whose vertices are cells
and whose hyperedges are possible single-event footprints. Assigning cells to words so
that no word receives more than its correction radius is a hypergraph coloring/packing
condition. No code-independent numeric region bound exists without the footprint and
layout model. A region identifier with `R` protected values supplies at most `log2 R`
bits and remains subject to the conflict-coloring bound.

Under a simultaneous coordinate permutation of `H`, `D`, `E`, `P`, available actions,
and the ground metric, the conflict graph is isomorphic and `C_safe`, `chi`, and
`t_lin` are invariant. Permuting logical columns while holding a physical fault law or
metric fixed is not such an isomorphism; it is a placement change and need not preserve
weighted capacity or Wasserstein bounds.

## 4. Evidence limit

### Exact conditional bounds

For `x` SDCs in `n` independent relevant fault events, the exact one-sided
Clopper-Pearson upper bound at confidence `1-alpha` is

```text
p_U = BetaQuantile(1-alpha; x+1, n-x).
```

For zero SDCs,

```text
p_U = 1 - alpha^(1/n),
n_min(p0,1-alpha) = ceil(log(alpha) / log(1-p0)).
```

The following is for one preregistered claim, a frozen support/policy, IID Bernoulli
events, and zero observed SDCs.

| Conditional upper limit | 90% confidence | 95% confidence | 99% confidence |
|---:|---:|---:|---:|
| `1e-3` | 2,302 | 2,995 | 4,603 |
| `1e-5` | 230,258 | 299,572 | 460,515 |
| `1e-6` | 2,302,584 | 2,995,731 | 4,605,168 |

This is established binomial confidence mathematics, originating with
[Clopper and Pearson 1934](https://doi.org/10.1093/biomet/26.4.404). It is not a
SafeForge novelty. If `M` policies, voltage points, or subgroup claims are selected or
reported simultaneously with Bonferroni familywise confidence, replace `alpha` by
`alpha/M`; preferably, select on discovery data and make one claim on a frozen holdout.

### Event rates, FIT, and mission probability

For `K` events in exposure `T` under a stationary Poisson process, the exact one-sided
Garwood upper rate is

```text
lambda_U = ChiSquareQuantile(1-alpha; 2(K+1)) / (2T).
```

At `K=0`, `lambda_U=-log(alpha)/T`. The corresponding exact lower endpoint for
`K>0` is `ChiSquareQuantile(alpha;2K)/(2T)`
([Garwood 1936](https://doi.org/10.1093/biomet/28.3-4.437)).

For a stationary marked-Poisson model,

```text
lambda_SDC = lambda_event * Pr(SDC | relevant event),
FIT_SDC    = 1e9 * lambda_SDC,
Pr(at least one mission SDC in T_m)
           = 1 - exp(-lambda_SDC*T_m).
```

Multiplying separate upper confidence limits is valid only when their simultaneous
coverage is controlled (for example by allocating the familywise `alpha`). Directly
counting SDCs per exposure is preferable when the detection process is complete. With
tail mass `eta` and tail loss bound `b`, use
`theta <= (1-eta) theta_support + eta b` before the FIT conversion.

### Unseen mass, dependence, and ambiguity calibration

- Freeze the discovered support before validation. Then "outside support" is a
  Bernoulli outcome on independent validation events and the exact zero-failure table
  applies. Reusing validation observations to expand the support invalidates that bound.
- Good-Turing estimates unseen probability from frequency-of-frequency counts; the
  leading missing-mass estimate is tied to singleton counts, and distribution-free
  concentration still assumes an IID source
  ([Good 1953](https://doi.org/10.1093/biomet/40.3-4.237),
  [McAllester and Ortiz 2003](https://www.jmlr.org/papers/v4/mcallester03a.html)).
  Unseen mass is not by itself a bound on unseen SDC severity.
- Repeated reads of one persistent cell fault are not independent events. Count the
  physical first detection once for event-rate inference; keep recurrences as a separate
  persistence process. Device, run, source, pattern, temperature, and voltage create
  clusters. Use device-level holdouts and a hierarchical/clustered analysis. With only
  three devices, uncertainty about device-to-device variability remains large and an
  asymptotic cluster bootstrap is not credible.
- On-die ECC itself can induce dependence among observed bit errors, as HARP formally
  and experimentally documents
  ([Patel et al. 2021](https://arxiv.org/abs/2109.12697)). Applying row-wise binomial
  bounds to correlated post-correction bits overstates evidence.
- An empirical within-domain TV radius can be obtained from an exact multinomial
  confidence region or a finite-alphabet concentration inequality. Its sample cost
  grows with alphabet size. It does not calibrate device, voltage, radiation-source, or
  temporal distribution shift. Those shifts require target-domain holdouts or a
  separately justified transport model
  ([Weissman et al. 2003](https://www.researchgate.net/publication/2935498_Inequalities_for_the_L1_Deviation_of_the_Empirical_Distribution)).
- A Wasserstein radius additionally requires a physically justified metric and its own
  concentration assumptions. Synthetic Hamming/layout distances are sensitivity
  parameters, not measured confidence radii.

Accelerated radiation counts estimate a cross-section using known fluence; field FIT
then integrates the energy/LET-dependent cross-section against the mission spectrum.
Flux, spectrum, dead time, part-to-part variation, voltage, temperature, multiplicity
classification, and the fitted response all contribute uncertainty. There is no
universal acceleration factor. Current AMD reliability reporting, for example, states
that neutron cross-sections are obtained at LANSCE under JESD89 methods and field rates
use separate real-time/standardized corrections
([AMD UG116, rev. 10.20](https://docs.amd.com/r/en-US/ug116/SEU-and-Soft-Error-Measurements)).

## 5. Primary-source novelty comparison

### Claim-by-claim theorem gate

| Proposed SafeForge theorem | Closest established result | Difference and strength | Specialized example beyond prior work? | Verdict |
|---|---|---|---|---|
| O1/O2: syndrome-fiber safe capacity and randomized SDC-DUE frontier | Chow's Bayes error-reject tradeoff; Franc et al.'s randomized Bayes selector | SafeForge labels observations as syndromes and wrong accepted decisions as SDC. The proof is a finite specialization. | The `0.98/0.02` collision corrects the proposed identity, but the reject theorem already predicts the outcome. | Direct corollary |
| TV/interval/Wasserstein/tail DUE bounds | Robust expectation and Wasserstein duality; minimax decoding with erasure | SafeForge uses finite binary losses and a memory-specific tail. The TV event formula and Wasserstein dual are standard. | `epsilon<delta` explains the repository's all-or-reject point, but follows immediately from the standard TV support function. | Direct corollary |
| Conflict coloring and linear augmentation | Witsenhausen zero-error coloring; parity-check syndrome separation; classical code bounds | Target-mass deletion and data projection are useful bookkeeping. Kernel avoidance is standard linear algebra. | The 29-pattern example separates five arbitrary bits from six linear bits, but Griesmer/code bounds already predict it. | Incremental reformulation |
| Evidence-to-FIT composition | Clopper-Pearson, Garwood, Good-Turing/missing-mass concentration | SafeForge composes conditional SDC, event exposure, tail, FIT, and mission time. | The sample table exposes infeasible evidence demands, but no statistical theorem is added. | Engineering synthesis |

No proposed theorem produced an example whose conclusion could not be obtained by
instantiating the closest established theorem plus ordinary syndrome algebra. That is
the decisive failure condition.

### Required field coverage

- **Hsiao SECDED.** Hsiao constructs minimum odd-weight-column SEC-DED codes and
  discusses triple-error miscorrection; a `(72,64)` construction is explicit
  ([Hsiao 1970](https://doi.org/10.1147/rd.144.0395)). SafeForge does not create a new
  code by permuting its columns.
- **Reduced triple-error miscorrection.** Richter et al. derive lower bounds and codes
  with reduced triple-bit miscorrection, including SEC-DED-DAEC behavior
  ([Richter et al. 2008](https://doi.org/10.1109/IOLTS.2008.27)). Collision counting
  by itself is established.
- **Spare columns/check bits.** Datta and Touba use spare columns for extra checks;
  Han, Touba, and Yang extend this to repaired columns and stored defect information
  ([Datta and Touba 2009](https://doi.org/10.1109/VTS.2009.52),
  [Han et al. 2017](https://users.ece.utexas.edu/~touba/research/tcad17b.pdf)).
- **SEC-DAEC, placement, and erasures.** Dutta and Touba construct selective-cycle-
  avoidance SEC-DED-DAEC codes; Evain et al. use known erasure locations to enable
  additional correction
  ([Dutta and Touba 2007](https://users.ece.utexas.edu/~touba/research/vts07a.pdf),
  [Evain et al. 2013](https://doi.org/10.1109/ETS.2013.6569371)).
- **Manufacturing-variation-aware ECC.** Post-manufacturing OLS customization selects
  parity rows using a chip defect map, while MVP ECC uses manufacturing characterization
  to give weak cells unequal protection
  ([Datta and Touba 2010](https://users.ece.utexas.edu/~touba/research/itc10.pdf),
  [Lee and Yang 2017](https://doi.org/10.23919/DATE.2017.7927105)).
- **Application-specific FEC synthesis.** McClurg et al. synthesize and verify Hamming
  FEC against user-provided properties and data formats
  ([McClurg et al. 2024](https://conferences.sigcomm.org/hotnets/2024/papers/hotnets24-245.pdf)).
  Li et al. already automate linear memory-code and placement construction for arbitrary
  declared correctable/detectable pattern sets.
- **Minimax and compound decoding.** Robust decoding under uncertain noise, minimax
  universal decoding with erasure, and universal erasure/list tradeoffs are established
  ([Wei et al. 2000](https://doi.org/10.1109/18.841200),
  [Merhav and Feder 2007](https://arxiv.org/abs/cs/0604069),
  [Moulin 2009](https://arxiv.org/abs/0801.4544)).
- **Reject option and distribution shift.** Optimal rejection is classical and the
  randomized frontier is explicit by 2023. Recent work also studies selective
  classification under deployment shift
  ([Liang, Peng, and Sun 2025](https://pubmed.ncbi.nlm.nih.gov/41019465/)).
- **DRO.** Wasserstein ambiguity, performance guarantees, and tractable robust
  expectation reformulations are established by Mohajerin Esfahani and Kuhn.
- **Fault-aware/empirical memory ECC.** Custom pattern ECC, bit-exact recovery of opaque
  on-die ECC, HARP error profiling, and current fault-aware adaptive on-die ECC all use
  fault information or empirical behavior
  ([Li et al. 2021](https://doi.org/10.1109/TETC.2019.2953139),
  [BEER 2020](https://arxiv.org/abs/2009.07985),
  [HARP 2021](https://arxiv.org/abs/2109.12697),
  [FADE 2026](https://doi.org/10.1109/TVLSI.2025.3640215)).
- **Information-theoretic erasure/list decoding.** Forney derives the error-erasure-list
  tradeoff and optimal decision structure; Witsenhausen gives the zero-error graph
  formulation
  ([Forney 1968](https://www.itsoc.org/publications/papers/exponential-error-bounds-for-erasure-list-and-decision-feedback-schemes),
  [Witsenhausen 1976](https://doi.org/10.1109/TIT.1976.1055607)).

The audit therefore triggers every relevant failure warning in the brief: the surviving
results are a corrected Bayes/reject identity, standard robust-expectation formulas,
syndrome collision/separation, graph coloring, classical code bounds, and ordinary
zero-failure statistics. No coordinate permutation is a contribution.

## 6. Acquisition plan (no fabricated measurements)

This plan is evidence work, not authorization to expand the decoder.

1. Use at least three separately identified FPGA devices, preferably from multiple
   boards and recorded lots. Characterize at nominal voltage and at least three lower
   voltage points, plus a preregistered near-failure point; hold temperature fixed for
   the primary sweep and repeat selected points at controlled low/high temperatures.
2. Disable built-in ECC where raw BRAM/SRAM visibility permits it. Freeze and hash the
   logical-to-physical mapping before discovery. Each logical event must contain the
   complete 72-bit XOR vector, address/word, pattern, timestamp, device, run, voltage,
   temperature, source, and whether it is a first occurrence or a persistent repeat.
3. Record denominators, not just failures: word-hours and bit-hours, read/write/scrub
   opportunities, beam fluence and live time when irradiated, dead time, and excluded
   intervals. Preserve raw logs and immutable transformation manifests.
4. Use devices/voltages assigned to discovery to freeze the support, ambiguity model,
   policy, and all evaluation code. Hold out at least one entire device and one voltage
   condition. Report leave-one-device-out sensitivity; do not treat millions of reads
   from three devices as millions of independent device samples.
5. Preregister the primary SDC/DUE definitions, persistent-fault deduplication, support
   discovery cutoff, tail estimator, multiplicity rules, stopping rule, confidence
   level, and multiple-comparison family. Evaluate the frozen policy exactly once on
   the primary holdout.
6. Bound outside-support mass on the frozen holdout with exact binomial bounds and also
   report Good-Turing/missing-mass diagnostics on discovery data. Translate to system
   FIT only after separately confidence-bounding the event rate and controlling joint
   coverage.

The controller RTL, mapping hash, pattern generation, readback, 72-bit vector extraction,
exposure accounting, provenance checks, frozen-policy replay, and statistical reports
can be automated. Physical undervolting requires FPGA boards and a programmable power
supply; defensible temperature sweeps require temperature control and sensing. Physical
radiation FIT claims require a calibrated radiation facility or accepted field exposure.
Controlled pattern injection can validate the digital correction/abstention path but
cannot estimate physical event distributions or radiation FIT. No fabrication is
required, and no measurements may be synthesized or back-filled.

## 7. Eight-question decision

1. **Is there a genuinely new theorem?** No. The corrected statements are useful,
   code-independent specializations, but none passes the primary-source novelty gate.
2. **What is its exact mathematical statement?** There is no claimable new theorem.
   The strongest correct statement is O1: zero-SDC deterministic capacity is the mass
   of uniquely correction-equivalent, available-correctable observation fibers, not
   `sum_s max_j P(K_s,j)`. O2 gives the standard randomized frontier.
3. **Which prior theorem is closest?** Chow's Bayes reject rule and the randomized
   Bayes selector of Franc et al.; for side information, Witsenhausen's zero-error
   coloring plus standard parity-check separation is closest.
4. **What nontrivial consequence does it add?** It makes the SafeForge failure easy to
   diagnose: incomplete observation, not decoder search quality, forces DUE. The
   five-bit-color/six-linear-bit example and unrestricted-tail collapse are useful
   consequences, but both follow from established theory.
5. **Does it generalize beyond Hsiao and TV uncertainty?** Yes as a specialization: O1
   holds for additive linear codes over `F_q`; interval and Wasserstein bounds follow
   from standard robust expectation; tail behavior follows from observation fibers.
   Generality is not the same as novelty.
6. **What evidence would falsify it?** A counterexample in the stated pure
   syndrome-only model that safely accepts two data-incompatible members of one fiber
   would falsify O1. Empirical results can falsify the relevance of a declared support,
   metric, tail bound, IID model, or event-rate model, but cannot overturn the algebra.
   The novelty decision could change only with a stronger result not derivable from
   reject-option, zero-error graph, or classical linear-code theory.
7. **Publication level?** Thesis chapter only in the present form. With real multi-
   device evidence it could support a short negative/methods paper, but not a full
   archival theory paper on the current theorem set.
8. **Should implementation continue?** No. Freeze the positive placement-policy
   failure and all existing artifacts. Do not add a decoder, score, scheduler,
   heuristic, ambiguity set, metadata architecture, code search, broad benchmark, or
   phase diagram. Proceed only with the preregistered acquisition campaign or with a
   genuinely stronger theorem that survives a new primary-source audit.

