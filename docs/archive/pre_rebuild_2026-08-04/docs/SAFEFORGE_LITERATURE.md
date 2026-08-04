# SafeForge literature position

SafeForge does not claim to invent Hsiao SECDED, MAP/coset-leader decoding, abstention, minimax decoding, distributionally robust optimization, Wasserstein ambiguity, or correction masking. Its contribution is an SRAM-oriented certifying compiler that joins an explicit physical fault uncertainty set, correction-or-abstention syndrome policy, synthesizable RTL, solver-independent risk certificate, and fail-closed deployment gate.

The exact `(8,4)` Forge matrix is extended-Hamming/Hsiao-equivalent. Its `0.97` nominal correction result is therefore attributed to representation/mapping and syndrome policy, not a new algebraic code. Large arbitrary-matrix `(72,64)` search is retained as a negative result; practical experiments use fixed established or already-generated matrices.

## Closest foundations

- M. Y. Hsiao, “A Class of Optimal Minimum Odd-weight-column SEC-DED Codes,” *IBM Journal of Research and Development* 14(4), 1970, DOI `10.1147/rd.144.0395`.
- L. Wei, Z. Li, M. R. James, and I. R. Petersen, “A Minimax Robust Decoding Algorithm,” *IEEE Transactions on Information Theory*, 2000, DOI `10.1109/18.841200`.
- P. M. Esfahani and D. Kuhn, “Data-driven distributionally robust optimization using the Wasserstein metric,” *Mathematical Programming*, 2018, DOI `10.1007/s10107-017-1172-1`.
- A. Perez-Celis and M. J. Wirthlin, “Statistical Method to Extract Radiation-Induced Multiple-Cell Upsets in SRAM-Based FPGAs,” *IEEE Transactions on Nuclear Science* 67(1), DOI `10.1109/TNS.2019.2955006`.
- “Correction Masking: A Technique to Implement Efficient SET Tolerant Error Correction Decoders,” *IEEE Transactions on Device and Materials Reliability*, DOI `10.1109/TDMR.2021.3132045`.

## Primary external evidence used in this phase

- N. J. Pieper et al., “Study of Multicell Upsets in SRAM at a 5-nm Bulk FinFET Node,” *IEEE Transactions on Nuclear Science*, 2023, DOI `10.1109/TNS.2023.3240318`.
- A. Perez-Celis and M. J. Wirthlin, neutron MCU classification above.
- B. Salami, O. S. Unsal, and A. C. Kestelman, “Evaluating Built-in ECC of FPGA On-chip Memories for the Mitigation of Undervolting Faults,” 2019, arXiv `1903.12514`.
- E. Soyturk et al., “Hardware Versus Software Fault Injection of Modern Undervolted SRAMs,” 2019, arXiv `1912.00154`.
- NASA, “Xilinx Kintex-UltraScale Field Programmable Gate Array Single Event Effects Heavy-Ion Test Report,” NTRS `20205007765`.

These works establish that multiplicity, locality, device family, voltage, and operating mode matter. They do not provide the bit-exact 72-bit logical traces and layout maps needed to call the executable SafeForge PMF measured. Source-specific aggregates are therefore encoded as structured interval constraints; they are never pooled into a fabricated distribution.

## Frozen claim boundary

The paper title is **“SafeForge: Certifying SRAM Error Correction Under Fault-Model Uncertainty.”** It claims finite-support risk certification and explicit tail accounting, not universal safety; achieved SDC-DUE operating points, not a globally optimal risk frontier; generic RTL/synthesis evidence, not characterized PPA; and literature-derived uncertainty sensitivity, not silicon validation.

The earlier shared-XOR result remains a negative ablation and is outside the central contribution.
