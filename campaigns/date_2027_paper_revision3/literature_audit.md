# Revision-3 literature audit

## Selection result

- Final bibliography: **27 cited references**, within the requested 22--30 range and designed to fit one DATE reference page.
- Revision-2 references retained: **14**.
- References added after the Revision-3 search: **13**.
- Revision-2 references removed: **0**.
- Selection rule: retain a paper only when it supports a specific sentence about ECC hardware, cross-layer protection, synthesis/representation sensitivity, physical-flow variability, formal qualification, or activity-based power. Search results, inaccessible secondary summaries, and topically adjacent papers without a manuscript role were excluded.
- Metadata source of record: `paper/date2027_revision3/date2027_revision3.bib`. DOI links below resolve through the publisher DOI registry; arXiv records are linked directly.

## Curated bibliography

| Key | Status | Theme | Authors; title | Venue, year | DOI / official record | Manuscript role |
|---|---|---|---|---|---|---|
| `hsiao1970` | Retained | ECC hardware | M. Y. Hsiao; “A Class of Optimal Minimum Odd-Weight-Column SEC-DED Codes” | IBM J. R&D, 1970 | [10.1147/rd.144.0395](https://doi.org/10.1147/rd.144.0395) | Establishes Hsiao construction as a hardware-conscious code structure. |
| `ghosh2004` | Retained | ECC hardware/power | S. Ghosh, S. Basu, N. A. Touba; “Reducing Power Consumption in Memory ECC Checkers” | ITC, 2004 | [10.1109/TEST.2004.1387407](https://doi.org/10.1109/TEST.2004.1387407) | Supports checker power/area/delay optimization context. |
| `reviriego2013` | Retained | ECC hardware/timing | P. Reviriego, S. Pontarelli, J. A. Maestro, M. Ottavi; “A Method to Construct Low Delay Single Error Correction Codes for Protecting Data Bits Only” | IEEE TCAD, 2013 | [10.1109/TCAD.2012.2226585](https://doi.org/10.1109/TCAD.2012.2226585) | Supports low-delay SEC/SECDED logic construction. |
| `tripathi2020` | Retained | ECC hardware | S. Tripathi, J. Jana, J. Bhaumik; “Design of SEC-DED and SEC-DED-DAEC Codes of Different Lengths” | arXiv, 2020 | [arXiv:2002.07507](https://arxiv.org/abs/2002.07507) | Provides an ASIC-oriented adjacent-guarantee comparison. |
| `naseer2008` | Retained | Stronger ECC | R. Naseer, J. Draper; “Parallel Double Error Correcting Code Design to Mitigate Multi-Bit Upsets in SRAMs” | ESSCIRC, 2008 | [10.1109/ESSCIRC.2008.4681832](https://doi.org/10.1109/ESSCIRC.2008.4681832) | Grounds architecture-dependent DEC cost. |
| `chen2004` | Added | BCH hardware | Y. Chen, K. K. Parhi; “Small Area Parallel Chien Search Architectures for Long BCH Codes” | IEEE TVLSI, 2004 | [10.1109/TVLSI.2004.826203](https://doi.org/10.1109/TVLSI.2004.826203) | Shows Chien-search area/parallelism dependence. |
| `wong2011` | Retained | BCH power | S.-Y. Wong, C. Chen, Q. M. J. Wu; “Low Power Chien Search for BCH Decoder Using RT-Level Power Management” | IEEE TVLSI, 2011 | [10.1109/TVLSI.2009.2033698](https://doi.org/10.1109/TVLSI.2009.2033698) | Supports architecture-sensitive BCH power. |
| `yoo2016` | Added | BCH power | H. Yoo, Y. Lee, I.-C. Park; “Low-Power Parallel Chien Search Architecture Using a Two-Step Approach” | IEEE TCAS-II, 2016 | [10.1109/TCSII.2015.2482958](https://doi.org/10.1109/TCSII.2015.2482958) | Adds a distinct low-power Chien architecture. |
| `lagendijk2026` | Retained | BCH hardware | J. Lagendijk, W. Song, Y. C. Gültekin, A. Burg, A. Alvarado, A. Balatsoukas-Stimming; “High-Throughput Low-Latency Hardware Implementation of BCH Decoders” | arXiv, 2026 | [arXiv:2606.17837](https://arxiv.org/abs/2606.17837) | Prevents a family-wide inference from the evaluated BCH RTL. |
| `delbel2014` | Retained | Cross-layer ECC | B. Del Bel, J. Kim, C. H. Kim, S. S. Sapatnekar; “Improving STT-MRAM Density Through Multibit Error Correction” | DATE, 2014 | [10.7873/DATE2014.195](https://doi.org/10.7873/DATE2014.195) | Positions ECC/device/array co-design. |
| `pajouhi2015` | Retained | Cross-layer ECC | Z. Pajouhi, X. Fong, K. Roy; “Device/Circuit/Architecture Co-Design of Reliable STT-MRAM” | DATE, 2015 | [10.7873/DATE.2015.0145](https://doi.org/10.7873/DATE.2015.0145) | Positions cross-layer reliability/cost trade-offs. |
| `nair2016` | Retained | Reliability modeling | P. J. Nair, D. A. Roberts, M. K. Qureshi; “FaultSim: A Fast, Configurable Memory-Reliability Simulator for Conventional and 3D-Stacked Systems” | ACM TACO, 2016 | [10.1145/2831234](https://doi.org/10.1145/2831234) | Separates codec PPA from operational reliability modeling. |
| `wei2020` | Retained | Adaptive ECC | X. Wei, H. Yue, J. Tan; “LAD-ECC: Energy-Efficient ECC Mechanism for GPGPU Register File” | DATE, 2020 | [10.23919/DATE48585.2020.9116503](https://doi.org/10.23919/DATE48585.2020.9116503) | Positions workload/system adaptation. |
| `lee2022` | Retained | Adaptive ECC | Y. S. Lee, G. Koo, Y.-H. Gong, S. W. Chung; “Stealth ECC: A Data-Width Aware Adaptive ECC Scheme for DRAM Error Resilience” | DATE, 2022 | [10.23919/DATE54114.2022.9774775](https://doi.org/10.23919/DATE54114.2022.9774775) | Positions data-width-aware system ECC. |
| `das2019` | Retained | Stronger ECC | A. Das, N. A. Touba; “Layered-ECC: A Class of Double Error Correcting Codes for High Density Memory Systems” | IEEE VTS, 2019 | [10.1109/VTS.2019.8758647](https://doi.org/10.1109/VTS.2019.8758647) | Supports alternative DEC organizations. |
| `yoon2011` | Added | Adaptive protection | D. H. Yoon, M. K. Jeong, M. Erez; “Adaptive Granularity Memory Systems: A Tradeoff Between Storage Efficiency and Throughput” | ISCA, 2011 | [10.1145/2000064.2000100](https://doi.org/10.1145/2000064.2000100) | Adds a system-level granularity trade-off reference. |
| `mishchenko2006` | Added | Logic representation | A. Mishchenko, S. Chatterjee, R. K. Brayton; “DAG-Aware AIG Rewriting: A Fresh Look at Combinational Logic Synthesis” | DAC, 2006 | [10.1145/1146909.1147048](https://doi.org/10.1145/1146909.1147048) | Establishes representation-sensitive equivalent rewriting. |
| `hosny2020` | Added | Synthesis sequences | A. Hosny, S. Hashemi, M. Shalan, S. Reda; “DRiLLS: Deep Reinforcement Learning for Logic Synthesis” | ASP-DAC, 2020 | [10.1109/ASP-DAC47756.2020.9045529](https://doi.org/10.1109/ASP-DAC47756.2020.9045529) | Supports synthesis-recipe sensitivity. |
| `neto2019` | Added | Synthesis sequences | W. L. Neto et al.; “LSOracle: A Logic Synthesis Framework Driven by Artificial Intelligence” | ICCAD, 2019 | [10.1109/ICCAD45719.2019.8942145](https://doi.org/10.1109/ICCAD45719.2019.8942145) | Supports representation/recipe-dependent optimization. |
| `grosnit2022` | Added | Synthesis sequences | A. Grosnit, C. Malherbe, R. Tutunov, X. Wan, J. Wang, H. Bou-Ammar; “BOiLS: Bayesian Optimisation for Logic Synthesis” | DATE, 2022 | [10.23919/DATE54114.2022.9774632](https://doi.org/10.23919/DATE54114.2022.9774632) | Adds DATE-specific synthesis-sequence optimization context. |
| `kwon2019` | Added | Physical-flow variability | J. Kwon, M. M. Ziegler, L. P. Carloni; “A Learning-Based Recommender System for Autotuning Design Flows of Industrial High-Performance Processors” | DAC, 2019 | [10.1145/3316781.3323919](https://doi.org/10.1145/3316781.3323919) | Establishes flow-parameter quality sensitivity. |
| `ajayi2019` | Retained | Open physical design | T. Ajayi et al.; “Toward an Open-Source Digital Flow: First Learnings from the OpenROAD Project” | DAC, 2019 | [10.1145/3316781.3326334](https://doi.org/10.1145/3316781.3326334) | Positions the inspectable open RTL-to-layout flow. |
| `shalan2020` | Added | Open physical design | M. Shalan, T. Edwards; “Building OpenLANE: A 130 nm OpenROAD-Based Tapeout-Proven Flow” | ICCAD, 2020 | [10.1109/ICCAD51958.2020.9256623](https://doi.org/10.1109/ICCAD51958.2020.9256623) | Adds the SKY130/open-flow context. |
| `kuehlmann1997` | Added | Formal qualification | A. Kuehlmann, F. Krohm; “Equivalence Checking Using Cuts and Heaps” | DAC, 1997 | [10.1145/266021.266090](https://doi.org/10.1145/266021.266090) | Grounds combinational equivalence qualification. |
| `kuehlmann2002` | Added | Formal qualification | A. Kuehlmann, V. Paruthi, F. Krohm, M. K. Ganai; “Robust Boolean Reasoning for Equivalence Checking and Functional Property Verification” | IEEE TCAD, 2002 | [10.1109/TCAD.2002.804386](https://doi.org/10.1109/TCAD.2002.804386) | Grounds robust equivalence/property reasoning. |
| `najm1993` | Added | Activity power | F. N. Najm; “Transition Density: A New Measure of Activity in Digital Circuits” | IEEE TCAD, 1993 | [10.1109/43.205010](https://doi.org/10.1109/43.205010) | Supports transition-activity-sensitive power reasoning. |
| `najm1994` | Added | Activity power | F. N. Najm; “A Survey of Power Estimation Techniques in VLSI Circuits” | IEEE TVLSI, 1994 | [10.1109/92.335013](https://doi.org/10.1109/92.335013) | Supports the scope and limits of activity-based estimation. |

## Exclusion and curation notes

- No reference is included only to claim broad topic coverage; every entry is cited in a supporting sentence.
- The 2026 BCH preprint is retained because it directly limits the interpretation of the repository's single syndrome/Chien realization; it is not used for a priority claim.
- The two power references are foundational rather than recent because the manuscript needs methodological support for activity-dependent estimation, not a survey of contemporary low-power EDA.
- The literature audit found adjacent work in each component area, so Revision 3 avoids universal-absence, “first,” and family-wide superiority claims.
