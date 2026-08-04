# Glossary

| Term | Definition |
|---|---|
| ECC | Error-correcting code: mathematical redundancy and/or a concrete mechanism that detects/corrects errors; context must specify which. |
| Code specification | Mathematical field, dimensions, codeword set, matrix/polynomial and transformations, identified by `code_spec_id`. |
| Encoder | Deterministic mapping from `k` information bits to an `n`-bit codeword. |
| Decoder policy | Rule mapping a received word/syndrome to correction, detection, abstention or invalid status. |
| Implementation | Concrete encoder/decoder adapter, reference or RTL plus protocol/latency/evidence metadata. |
| SEC / DED | Single-error correction / double-error detection. Detection does not restore data. |
| SECDED | Single-error-correcting, double-error-detecting behavior over a declared universe. |
| SEC-DAEC | Repository label for a bounded single-error/double-adjacent-error correction policy; its current full claim is rejected. |
| TAEC | Triple-adjacent-error correction claim/policy. The repository bounded policy fails its adjacent-triple claim. |
| BCH | Bose–Chaudhuri–Hocquenghem code. The label alone is not a valid polynomial/distance/capability proof. |
| Hsiao code | Odd-column-weight SECDED construction optimized for total ones; not assumed equivalent to positional Hamming. |
| SDC | Silent data corruption: decoder appears successful but returns wrong data. |
| DUE | Detected uncorrectable error, including explicit abstention where the study groups them. |
| MBU | Multi-bit upset; adjacency is defined over canonical codeword coordinates. |
| SER / FIT | Soft error rate / failures in time (failures per 10⁹ hours). |
| Scrubbing | Periodic memory read/check/correct/write process that limits accumulation time. |
| PDK | Process design kit providing technology-specific devices/rules/models. |
| PPA | Power, performance and area; physical claims require a characterized backend context. |
| Structural proxy | Technology-independent operation/table/depth count; not physical PPA. |
| Backend | Tool adapter plus availability, library/PDK/corner context and evidence class. |
| Workload | Access/activity/lifetime assumptions bound to energy/characterization. |
| Scenario | Hashed tuple of environment, fault profile, workload and reliability requirement. |
| Fairness view | Rule defining which dimensions or contexts are held equal before comparison. |
| Pareto frontier | Feasible points not dominated across declared objective directions. |
| Epsilon dominance | Dominance with per-objective tolerance; current study epsilon is zero. |
| Crowding distance | Normalized neighbor-spacing measure within a Pareto front. |
| Knee point | Plot-derived point farthest from the normalized extreme-point chord. |
| Hypervolume | Objective space dominated by a frontier relative to an explicit reference point. |
| Regret | Difference between a feasible fixed baseline and scenario winner under the same analytical metric. |
| OOD | Out of distribution; advisory machine learning falls back to deterministic selection. |
| ESII | Environmental Sustainability Improvement Index, a bounded reliability/energy/carbon utility. |
| GS | Green Score, a weighted geometric mean of bounded utilities. |
| NESII | Cohort-normalized ESII using 5th/95th percentile anchors. |
| `exact_functional` | Exact algebraic/enumerated behavior under the bound implementation and universe. |
| `analytical_model` | Equation/model output from explicit inputs; not measurement. |
| `structural_tool` | Generic tool output without a complete physical context. |
| `physical_characterization` | Backend/PDK/library/corner/workload-bound physical result. |
| `hardware_measurement` | Instrumented hardware/silicon observation with provenance. |
| `unsupported` | Missing, null, excluded or not scientifically computable. |
