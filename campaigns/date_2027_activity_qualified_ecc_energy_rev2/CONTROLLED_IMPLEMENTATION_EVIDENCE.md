# Controlled Implementation Evidence

## Q1 - Hardware identity

The conventional combinational/pipelined SECDED pair implements the same systematic (72,64) transaction relation after a two-cycle response alignment. Request latency is one versus three cycles and II is one for both. At 10 ns, the paired mean changes are area +37.201864%, signed-slack timing metric +46.629355%, and energy/op -23.419005%; all three directions hold in 5/5 seeds.

The flat/hierarchical Hsiao pair holds matrix, interface, latency, and II fixed. Hierarchical minus flat means are area -0.564121549%, detailed wire +3.867151613%, vias +3.918160539%, timing +2.655650761%, and energy +1.328394690%. The mixed small changes are a counterexample to any assumption that distinct implementation identities must have large effects.

## Q2 - Implementation condition

At 5 ns, the same temporal pair has mean area +36.721137579%, timing +68.629653158%, and energy -19.336605983%; directions hold in 5/5 seeds. These are fresh implementations of the temporal pair. They do not replicate the current conventional/Hsiao activity study at 5 ns.

## Feasibility boundary

The evaluated BCH(78,64,t=2) syndrome/Chien realization provides W1/W2 correction but meets the common 10-ns target in 0/5 matched implementation attempts. The result is identity-scoped and is not a claim about BCH as a family.

## Interpretation

Implementation identity determines what must be measured separately; it does not predict the magnitude or sign of the resulting physical displacement. These controls justify freezing hardware identity and physical condition before Q3 substitutes the activity model.
