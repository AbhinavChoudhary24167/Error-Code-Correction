# Limits of certified availability recovery for production-compatible SRAM ECC

## Abstract

We test whether physical column placement and syndrome-level abstention can recover useful availability for a fixed conventional `(72,64)` Hsiao SEC-DED code under a system-derived silent-data-corruption constraint. We formulate exact finite-support robust policy compilation, independently verify its risk and optimality certificates, and enumerate 87 implementation-compatible data-column placements without changing the algebraic code. At a declared 1-system-SDC-FIT engineering point with 1000 relevant system event FIT, a `1e-5` outside-support bound, and TV radius 0.05, the modeled-support SDC budget is `0.0009900099`. The exact fixed-placement policy has worst-case DUE 1.0. Even/odd interleaving reduces it to `0.9810098871`, but the same placement is selected by an independent collision-isolation objective followed by policy compilation; joint co-design adds exactly zero over this strong sequential baseline. Synthetic held-out distributions also produce conditional SDC from 0.01875 to 0.234375 because they contain vectors outside the certificate universe. No raw bit-exact experimental archive and no characterized-library result for the decisive policy are available. The central positive hypothesis is therefore rejected in the evaluated domain. The result identifies support completeness, not optimizer quality, as the limiting resource for certified availability.

## 1. Research question

The desired outcome was a compiler that accepts a production ECC matrix, physical fault geometry, ambiguity set, and system SDC target, then emits a placed abstaining decoder with independently verifiable guarantees. We intentionally freeze the matrix. The 72 columns remain the conventional Hsiao/SEC-DED multiset, and equivalent permutations are treated as placements rather than code inventions.

Our central question is narrow: can joint placement-policy optimization substantially reduce DUE at a stringent system-derived SDC bound, survive distribution shift, and retain credible hardware cost? The answer for the declared experiment is no.

## 2. Method

We derive conditional decoder risk from explicit system event units. The primary point targets 1 system SDC FIT under an upper relevant-event exposure of 1000 FIT. The total conditional budget is 0.001. With outside-support mass `eta=1e-5` and worst-case tail SDC one, the modeled-support budget is `(0.001-1e-5)/(1-1e-5)=0.0009900099`. Neither the exposure nor tail value is claimed as empirical.

The finite universe contains 427 unique 72-bit vectors from four synthetic benchmark families. We group vectors by syndrome and allow abstention, modeled same-syndrome correction representatives, and a verified conventional fallback. A robust multiple-choice MILP minimizes worst-case DUE subject to worst-case SDC. Exact adversarial separation covers total variation, structured intervals, and declared geometry transport. At the primary TV radius, the SDC budget is below the radius; therefore only actions with zero SDC across all 427 vectors are feasible, giving a closed-form exact decomposition. The independent verifier reconstructs all loss vectors and checks the risk primal/dual witnesses and zero optimality gap.

Placement assigns the fixed 64 data-column multiset to physical data positions while leaving parity bits fixed. The finite library includes the conventional order, even/odd interleaving, cyclic assignments, adjacent swaps, and within-eight-bit rotations. We make no claim outside these 87 candidates.

## 3. Baselines and primary result

The conventional fixed decoder has worst-case conditional SDC 0.05 and DUE 0.70 under the TV set. After the declared tail conversion this projects to 50.0095 system SDC FIT, so it misses the 1-FIT target. The exact abstaining policy on conventional placement reduces modeled-support SDC to zero and projects to 0.01 FIT solely because of the assumed tail bound, but its worst-case DUE is 1.0.

Even/odd interleaving plus the exact policy has zero modeled-support SDC, nominal DUE `0.9310098871`, and certified worst-case DUE `0.9810098871`. This is an absolute 0.0189901129 DUE reduction relative to policy-only fixed placement. It is not a useful availability recovery: only about 1.9% worst-case event probability remains protected.

Most importantly, a placement-only objective that maximizes mass in syndrome-isolated groups selects the same even/odd map. Compiling its policy produces exactly the joint result. The joint-versus-sequential DUE reduction is 0.0, with zero optimality gap over the declared library. The intended co-design claim does not survive the strongest baseline.

## 4. Shift, tail, and external validity

No evidence level A raw bit-exact dataset or level B measurement-derived replay was located and licensed for ingestion. Five primary studies support only level C aggregate constraints in this repository. They do not provide a public physical/logical map and event vectors sufficient for a 72-bit replay.

Without retuning, three additional synthetic distributions yield conditional SDC of 0.01875 (temperature), 0.234375 (geometry-filtered), and 0.1319444444 (nonadjacent MBU). They contain respectively 69, 61, and 137 patterns outside the training/certificate support. These are sensitivity failures, not experimental validation.

The tail is decisive. With the declared `eta=1e-5`, the zero-support-SDC policy projects to 0.01 system FIT. With no tail bound, fail-closed projection is 1000 FIT. Thus the result cannot be deployed until event exposure and support completeness receive confidence-bounded measurement.

## 5. Hardware evidence

Prior SafeForge RTL replay executed 1,708 modeled 72-bit checks and generic Yosys/ABC synthesis. It reported 311 generic cells for a nominal table and 380 for a different robust mapping, with topological depths 38 and 40. Those values are structural—not physical PPA—and do not characterize the decisive even/odd policy. No open Liberty mapping, OpenSTA timing, OpenROAD placement/routing, switching power, leakage, memory-macro routing, or energy result was completed for this gate. Hardware practicality is therefore unproven, not estimated.

## 6. Interpretation

The exact compiler and verifier remove optimization uncertainty in the declared domain. They also make the negative result sharper: the availability collapse is not caused by a greedy policy. A TV shift larger than the system conditional SDC budget forces support-universal actions. Syndrome collisions across a broad finite universe then require abstention on most nominal events. Placement improves isolation modestly, but a strong sequential collision objective captures the entire benefit.

The scientifically defensible claim is therefore limited: for this fixed Hsiao code, 427-vector synthetic universe, 0.05 TV ambiguity, 87-placement library, and 1-FIT engineering conversion, exact joint co-design certifies DUE `0.9810098871` and gives no gain over sequential placement. This is a negative boundary result, not production validation.

## 7. What would change the conclusion

A top-grade archival submission needs a raw campaign with physical/logical mapping, device/voltage/source holdouts, a confidence-bound event rate and outside-support probability, and characterized synthesis/STA or placed routing for the exact generated policy. If those measurements shrink the ambiguity/tail while preserving the spatial placement advantage, the positive availability claim can be retested. Until then, GREEN-ECC scheduling remains downstream and should not mask the decoder-validity failure.
