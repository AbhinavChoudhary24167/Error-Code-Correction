# Use cases

Evidence strength is the highest defensible class for the named workflow, not a promise that every candidate reaches it.

| User | Question answered | Required inputs | Primary outputs | Evidence strength |
|---|---|---|---|---|
| ECC researcher | Does a new encoder/decoder satisfy its declared error universe? | Code and implementation manifests, factory, declared patterns, evidence hashes | Verification report, exact fractions, counterexamples | `exact_functional` |
| Decoder-policy designer | How do policies sharing one codeword set differ? | Same `code_spec_id`, separate `implementation_id`/`decoder_policy_id` records | Capability matrix and exact outcome profiles | `exact_functional` |
| Coding theorist | How do distinct mathematical codes compare at equal payload? | Separate code manifests and normalized payload view | Rate, redundancy, distance, exact profiles | `exact_functional` |
| Safety engineer | Where does a decoder silently miscorrect? | Golden-data harness and declared error generators | `MISCORRECTED` counts and representative masks | `exact_functional` |
| Memory-system engineer | Does an implementation satisfy a scenario reliability limit? | Verified implementation, fault profile, requirement limits, workload | Constraint flags, feasible set, no-winner state | exact + `analytical_model` |
| Architecture researcher | Does the preferred candidate vary by scenario? | Preregistered scenario grid and analytical parameter set | Pareto membership, winner regions, frequency | conditional `analytical_model` |
| System designer | Can a fixed policy be compared with an adaptive oracle? | Complete comparable scenario grid and hypothetical overhead | Fixed-baseline regret and parameterized threshold | conditional `analytical_model` |
| Robustness reviewer | Is the recommendation stable to named parameter scales? | Explicit uncertainty cases | Base-winner agreement and changed scenarios | conditional `analytical_model` |
| Instructor/student | How do correction, detection, abstention, and miscorrection differ? | Small/registered code and exact verification command | Machine-readable outcomes and counterexamples | `exact_functional` |
| RTL engineer | Is an RTL/reference candidate ready for physical work? | Passing verification, protocol/reset evidence, architecture compatibility | Eligibility decision and null-safe characterization record | functional + optional `structural_tool` |
| Thesis/artifact reviewer | Can the published study be reproduced? | Repository revision and documented toolchain | Hash-bound JSON/CSV/figures, tests, build summary | mixed, explicitly labelled |

## Do not use this framework for

- measured physical PPA claims without a real backend, process design kit (PDK), characterized libraries, constraints, and workload activity;
- silicon reliability or qualified-device failure-rate claims;
- radiation-validation claims;
- technology-independence claims for energy, timing, area, or winner identity;
- measured MUX/controller, transition, or re-encoding overhead;
- an actual adaptive break-even claim while those costs are null;
- replacing qualified memory-device reliability data or mission-specific fault characterization;
- treating `BCH`, `TAEC`, `SEC-DAEC`, or any other family label as a verified correction guarantee;
- converting generic Yosys structure, operation counts, or logic-depth proxies into physical cells, delay, power, or energy.

The [Claim Ledger](CLAIM_LEDGER.md) gives the current status of each tempting inference.
