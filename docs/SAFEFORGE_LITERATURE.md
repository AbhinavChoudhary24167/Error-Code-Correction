# SafeForge literature position

SafeForge does not claim to invent maximum-likelihood decoding, coset leaders, minimax decoding, abstention, or distributionally robust optimization.

Hsiao's 1970 construction establishes optimal minimum odd-weight-column SECDED matrices. The existing exact `(8,4)` Forge result is in that known class. Classical MAP/ML or coset-leader decoding selects the most probable error in each syndrome under one assumed model; it does not by itself certify SDC under a neighborhood of PMFs.

Robust and universal decoding are established subjects. The closest conceptual antecedents include minimax robust decoding for uncertain channels, competitive minimax/universal decoding, mismatched decoding, and compound-channel coding. Wasserstein distributionally robust optimization supplies tractable worst-case expectations and dual certificates. Existing ECC work also suppresses miscorrection or masks correction under selected fault mechanisms, and SRAM ECC work constructs SEC-DAEC/TAEC matrices for physical adjacency.

The narrow contribution tested here is:

> A certifying compiler for short-block SRAM ECC that configures or searches a parity matrix and an abstaining syndrome policy under an explicit physical fault-distribution ambiguity set, emits synthesizable RTL, and produces a solver-free checkable worst-case SDC envelope used as a deployment gate.

This phase demonstrates exact finite-support certification and exact scoped `(8,4)` co-synthesis. It does not establish a new code family, a new minimax theorem, global optimality at `k=64`, measured fault coverage, or physical PPA.

## Closest references

- M. Y. Hsiao, “A Class of Optimal Minimum Odd-weight-column SEC-DED Codes,” IBM Journal of Research and Development 14(4), 1970, DOI `10.1147/rd.144.0395`.
- L. Wei, Z. Li, M. R. James, and I. R. Petersen, “A Minimax Robust Decoding Algorithm,” IEEE Transactions on Information Theory, 2000, DOI `10.1109/18.841200`.
- P. M. Esfahani and D. Kuhn, “Data-driven distributionally robust optimization using the Wasserstein metric,” Mathematical Programming, 2018, DOI `10.1007/s10107-017-1172-1`.
- A. Pérez-Celis and M. J. Wirthlin, “Statistical Method to Extract Radiation-Induced Multiple-Cell Upsets in SRAM-Based FPGAs,” IEEE Transactions on Nuclear Science 67(1), DOI `10.1109/TNS.2019.2955006`.
- G. Tsiligiannis et al., “Multiple Cell Upset Classification in Commercial SRAMs,” IEEE Transactions on Nuclear Science 61(4), DOI `10.1109/TNS.2014.2313742`.
- “Correction Masking: A Technique to Implement Efficient SET Tolerant Error Correction Decoders,” IEEE Transactions on Device and Materials Reliability, DOI `10.1109/TDMR.2021.3132045`.

The paper framing is **GREEN-ECC SafeForge: Certifying SRAM Error Correction Under Fault-Model Uncertainty**. The negative shared-XOR result—369 gates for joint co-synthesis versus 350 for independent generation plus shared CSE, without Yosys/ABC or physical PPA—is retained as an ablation and is not the central contribution.
