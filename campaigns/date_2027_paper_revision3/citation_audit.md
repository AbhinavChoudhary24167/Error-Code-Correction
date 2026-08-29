# Revision-3 citation audit

The manuscript contains six citation-bearing paragraphs. The table below splits compound paragraphs into the individual propositions supported by each citation group. All 27 bibliography entries are cited; no citation is used for the repository's experimental numbers.

| Location / supported proposition | Citation keys | Why the references support the proposition | Audit |
|---|---|---|---|
| Introduction: hardware-conscious SEC/SECDED construction and checker optimization are established. | `hsiao1970`, `ghosh2004`, `reviriego2013`, `tripathi2020` | These introduce Hsiao construction, checker power optimization, low-delay SEC logic, and ASIC SECDED/DAEC designs. | Direct |
| Introduction: multi-error code hardware is architecture-dependent. | `naseer2008`, `chen2004`, `wong2011`, `yoo2016`, `lagendijk2026` | These compare DEC/BCH organizations, Chien parallelism, power management, and direct/conventional BCH implementations. | Direct |
| Introduction: cross-layer studies trade reliability against array, storage, performance, or energy cost. | `delbel2014`, `pajouhi2015`, `nair2016`, `das2019`, `wei2020`, `lee2022`, `yoon2011` | Collectively cover device/array co-design, reliability simulation, stronger ECC, adaptive protection, storage efficiency, throughput, and energy. | Direct, collective |
| Related work: odd-weight-column Hsiao construction makes parity-check structure a hardware concern. | `hsiao1970` | The cited paper defines the construction and motivates low-cost checking. | Direct |
| Related work: checker work optimizes power, area, or delay. | `ghosh2004`, `reviriego2013` | One targets checker power with PPA concerns; the other constructs low-delay SEC logic. | Direct |
| Related work: ASIC studies compare SECDED and adjacent DAEC guarantees. | `tripathi2020` | The cited work synthesizes SEC-DED and SEC-DED-DAEC codes of multiple lengths. | Direct |
| Related work: parallel Chien search trades evaluation logic/parallelism against latency and area. | `chen2004` | The paper presents small-area parallel Chien-search architectures. | Direct |
| Related work: low-power Chien variants gate or reorganize activity. | `wong2011`, `yoo2016` | The works use RT-level power management and a two-step parallel search. | Direct |
| Related work: recent direct/conventional BCH decoders occupy different area/latency regions. | `lagendijk2026` | The hardware comparison explicitly contrasts decoder organizations. | Direct; no priority claim |
| Related work: comparative DEC work exposes architecture-dependent cost. | `naseer2008`, `das2019` | Both propose/evaluate stronger-correction hardware organizations. | Direct |
| Related work: memory studies co-design ECC with STT-MRAM, adaptive granularity, GPU register files, DRAM protection, and reliability modeling. | `delbel2014`, `pajouhi2015`, `nair2016`, `wei2020`, `lee2022`, `yoon2011` | Each item maps to one named system/device context. | Direct, collective |
| Related work: equivalent representations and synthesis recipes expose different area/delay opportunities. | `mishchenko2006`, `hosny2020`, `neto2019`, `grosnit2022` | The set covers AIG rewriting and learned/Bayesian logic-synthesis sequence exploration. | Direct, collective |
| Related work: physical-flow parameter tuning changes quality of results. | `kwon2019` | The cited recommender autotunes industrial design-flow settings. | Direct |
| Related work: OpenROAD/OpenLANE enable inspectable RTL-to-layout experiments. | `ajayi2019`, `shalan2020` | These describe the OpenROAD project and the OpenLANE 130-nm flow. | Direct |
| Related work: formal equivalence supplies a behavioral qualification boundary. | `kuehlmann1997`, `kuehlmann2002` | These establish equivalence checking and robust Boolean reasoning for equivalence/property verification. | Direct |
| Related work: activity-based power estimation motivates preserving the trace and switching evidence. | `najm1993`, `najm1994` | These establish transition density and survey power-estimation techniques. | Direct |
| Related work: internal transition behavior matters, but aggregate activity does not prove a specific glitch mechanism. | `najm1993`, `najm1994` | The references support activity sensitivity; the manuscript's negative causal boundary is a conservative inference, not attributed as their quoted conclusion. | Supported + explicit inference |

## Automated checks

- Bibliography entries: 27.
- Distinct cited keys: 27.
- Uncited entries: 0.
- Citation keys missing from the bibliography: 0.
- Undefined LaTeX citations after final build: 0 expected; enforced by `scripts/validate_revision3.py`.
- References supporting experimental values: 0; all such values are tied to the local evidence registry instead.
