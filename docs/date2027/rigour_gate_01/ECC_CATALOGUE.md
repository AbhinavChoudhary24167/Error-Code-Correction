# Gate 01 ECC catalogue

**Frozen source:** `main@f2908466bfa1a8eee8ad5c13b15e0d02a4730351`  
**Evidence boundary:** existing manifests, source, archived reports, and verification records only. Gate 01 did not create a new distance proof or extend an error universe.

`PASS` below means the identity and existing declared evidence are internally suitable to enter Gate 02; it does not grant publication correctness. `CONDITIONAL PASS` limits use to the stated passing scope. `FAIL` excludes selection. `NOT IMPLEMENTED` denotes source artifacts without a registered, evidenced scientific identity. `NOT ASSESSABLE` denotes evidence that could not be reproduced in the isolated checkout.

## Independently derived counts

Direct enumeration of the registry JSON files gives 15 mathematical codes, 17 implementations, and 17 architectures. Existing verification records contain 15 process-level passes and two failures; one of the 15 passes is capability-level partial (TAEC), yielding 15 currently selectable implementations under the repository policy. The scenario axes contain `2 x 2 x 2 x 2 x 3 x 2 x 2 = 192` cells. These match the expected pre-audit values, but the match does not resolve the checkout-sensitive source-hash failure described below.

## Registered mathematical codes

| Code ID | Canonical construction | `(n,k,r)`, rate | Matrix/polynomial identity | Existing distance evidence | Existing decoder policy and stated scope | Existing miscorrection evidence | Fair-comparison requirement | Gate 01 |
|---|---|---|---|---|---|---|---|---|
| `extended-hamming-secded-72-64-v1` | Binary positional extended Hamming SECDED | `(72,64,8)`, 0.888889 | Deterministic `conventional_extended_hamming`; systematic 64 data plus Hamming parity and overall parity | exact `d=4` asserted in manifest and existing evidence | Repository SECDED policy universally enumerated for all weight-1 correction and weight-2 detection; TAEC and SEC-DAEC policies share this codeword set | SECDED passes its declared universe; shared SEC-DAEC miscorrects 302/2556 doubles; TAEC miscorrects 62/62 adjacent triples | Compare policies at identical code, payload, mapping, architecture, PVT, workload, and fault context | `CONDITIONAL PASS` (SECDED scope only; other policies separate) |
| `hsiao-secded-72-64-v1` | Hsiao minimum-total-ones/odd-column SECDED | `(72,64,8)`, 0.888889 | Deterministic `hsiao_odd_column`; systematic matrix | existing exact dual-enumeration/MacWilliams record gives `d=4` | minimum-weight single-syndrome; existing 72/72 singles corrected and 2556/2556 doubles detected | weight >=3 outside declared universe may miscorrect; no broader guarantee | Directly comparable with positional `(72,64)` only after identical implementation/physical controls; coordinate equivalence is not established | `CONDITIONAL PASS` (existing evidence; isolated verification not assessable) |
| `primitive-bch-63-51-t2-v1` | Primitive narrow-sense binary BCH over GF(2^6), primitive polynomial `0x43`, roots 1..4 | `(63,51,12)`, 0.809524 | generator bits `1010100111001`; deterministic primitive BCH construction | existing exact `d=5` record | bounded GF-syndrome locator, correction through weight 2 | outside `t=2` can fail/miscorrect; no claim beyond declared universe | For 64 useful bits use two codewords/126 stored bits and account for 38 padded data positions | `CONDITIONAL PASS` (existing 2016-mask evidence; Gate 02 revalidation required) |
| `repository-cyclic-63-51-v1` | Repository degree-12 cyclic candidate, not the valid BCH above | `(63,51,12)`, 0.809524 | polynomial integer `4587`; systematic cyclic generator | existing exact record gives `d=2`; no BCH lower bound | bounded valid-codeword search nominally through weight 2 | only 30/63 singles corrected; 33/63 silently miscorrect | Same capacity normalization as other `(63,51)`; never inherit BCH guarantees | `FAIL` |
| `shortened-bch-71-64-t1-v1` | Shortened primitive parent BCH `(127,120,t=1)` | `(71,64,7)`, 0.901408 | `primitive_bch_systematic`, parent-to-shortened coordinate construction | existing exact `d=3` | GF-syndrome correction through weight 1; 71/71 existing masks | outside weight 1 unresolved/unsupported | Equal 64-bit payload and equal total useful capacity; include 71 stored bits/codeword | `CONDITIONAL PASS` |
| `shortened-bch-78-64-t2-v1` | Shortened primitive parent BCH `(127,113,t=2)` | `(78,64,14)`, 0.820513 | same validated construction family, `t=2` | existing exact `d=5` | correction through weight 2; existing 3081/3081 masks | outside weight 2 unresolved/unsupported | Equal payload/capacity and 78 stored bits/codeword | `CONDITIONAL PASS` |
| `shortened-bch-85-64-t3-v1` | Shortened primitive parent BCH `(127,106,t=3)` | `(85,64,21)`, 0.752941 | same construction family, `t=3` | designed `d>=7`; no exact minimum distance in manifest | correction through weight 3; existing 102425/102425 masks | outside weight 3 unresolved/unsupported | Equal payload/capacity and 85 stored bits/codeword | `CONDITIONAL PASS` (do not call exact `d=7`) |
| `forge-hotspot-8-4-v1` | Archived SafeForge/CodeForge binary linear code | `(8,4,4)`, 0.500000 | archived G/H and syndrome table | existing exact `d=4` | archived table policy; declared universes in verification record | beyond declared universe not guaranteed | Scale by integer codewords to common useful payload/capacity; include metadata/table implementation | `CONDITIONAL PASS` |
| `odd-column-secded-4-8` | Archived 4-data-bit odd-column baseline | `(8,4,4)`, 0.500000 | archived G/H and syndrome table | existing exact `d=4` | archived table policy | beyond declared universe not guaranteed | Same normalization as other `(8,4)` artifacts | `CONDITIONAL PASS` |
| `safeforge-robust-8-4-v1` | Archived SafeForge robust binary linear code | `(8,4,4)`, 0.500000 | archived G/H and syndrome table | existing exact `d=3` | abstaining/archived policy as recorded | domains outside table evidence unresolved | Same normalization as other `(8,4)` artifacts | `CONDITIONAL PASS` |
| `forge-spatial-hotspot-72-64-v1` | Archived SafeForge spatial-hotspot code | `(72,64,8)`, 0.888889 | archived G/H and syndrome table | existing exact `d=3` | archived syndrome-table policy | outside enumerated profile unresolved | Identical mapping is essential because construction was spatial-objective-specific | `CONDITIONAL PASS` |
| `forge-sram-portfolio-72-64-v1-geometry-filtered-joint` | Archived geometry-filtered portfolio code | `(72,64,8)`, 0.888889 | archived G/H and table | existing exact `d=4` | archived syndrome-table policy | outside enumerated evidence unresolved | Use the geometry/mapping for which it was designed or label transfer as sensitivity only | `CONDITIONAL PASS` |
| `forge-sram-portfolio-72-64-v1-spatial-hotspot-joint` | Archived spatial-hotspot portfolio code | `(72,64,8)`, 0.888889 | archived G/H and table | existing exact `d=4` | archived syndrome-table policy | outside enumerated evidence unresolved | Same mapping/fault-locality requirement | `CONDITIONAL PASS` |
| `odd-column-secded-64-72` | Archived 64-data-bit odd-column baseline | `(72,64,8)`, 0.888889 | archived G/H and table | existing exact `d=4` | archived syndrome-table policy | beyond declared universe not guaranteed | Same payload/capacity and physical controls as other `(72,64)` codes | `CONDITIONAL PASS` |
| `safeforge-robust-72-64-mapping-v1` | Archived mapping-robust SafeForge code | `(72,64,8)`, 0.888889 | archived G/H and abstaining table | existing exact `d=4` | mapping-specific archived policy | outside enumerated mapping/error universe unresolved | Must evaluate every preregistered physical mapping; a logical consecutive-coordinate model is insufficient | `CONDITIONAL PASS` |

The eight SafeForge/CodeForge rows are distinct archived matrices, not automatically equivalent merely because several have `(72,64)` or `(8,4)` dimensions.

## Registered implementations

| Implementation ID | Mathematical code | Concrete policy/form | Existing proven scope | Existing counterexample/status | Wrapper/duplicate | Physical evidence | Gate 01 |
|---|---|---|---|---|---|---|---|
| `secded-rtl-combinational-72-64-v1` | extended Hamming `(72,64)` | synthesizable combinational positional encoder/decoder | 72/72 single correction; 2556/2556 double detection | no failure within declared SECDED universe | canonical conventional implementation | RTL and generic structural evidence; physical PPA null | `CONDITIONAL PASS` |
| `secdaec-rtl-bounded-72-64-v1` | same extended Hamming code | bounded adjacent-pair syndrome policy | no promotable DAEC guarantee | 302/2556 doubles and 53/63 adjacent pairs silently miscorrect | policy variant, not a new code | RTL differential record only; physical PPA null | `FAIL` |
| `taec-rtl-bounded-72-64-v1` | same extended Hamming code | bounded adjacent-triple policy | shared SECDED universe only | 62/62 adjacent triples silently miscorrect | policy variant, not a `(75,64)` TAEC code | RTL differential record only; physical PPA null | `CONDITIONAL PASS` (SECDED only) |
| `hsiao-generated-combinational-72-64-v1` | Hsiao `(72,64)` | generated combinational matrix decoder | existing full declared SECDED universe | isolated rerun blocked by CRLF-sensitive source hash | generated registered RTL | generic structural only; physical PPA null | `NOT ASSESSABLE` for rerun; existing record `CONDITIONAL PASS` |
| `primitive-bch-63-51-t2-v1-reference-decoder` | valid primitive BCH | Python reference plus independent C++ `src/bch63.*` | existing correction through weight 2 | no counterexample in declared universe | C++ is duplicate/independent implementation evidence | reference software, not characterized RTL | `CONDITIONAL PASS` |
| `cyclic-rtl-bounded-search-63-51-v1` | invalid cyclic candidate | `asic/rtl/bch/bch_codec.sv` bounded search | none sufficient for selection | 33/63 single silent miscorrections | historically BCH-labelled; not valid BCH reference | RTL differential only | `FAIL` |
| `shortened-bch-71-64-t1-v1-reference-decoder` | shortened BCH t1 | Python reference | existing 71 masks through weight 1 | none within scope | sole registered implementation | software only | `CONDITIONAL PASS` |
| `shortened-bch-78-64-t2-v1-reference-decoder` | shortened BCH t2 | Python reference | existing 3081 masks through weight 2 | none within scope | sole registered implementation | software only | `CONDITIONAL PASS` |
| `shortened-bch-85-64-t3-v1-reference-decoder` | shortened BCH t3 | Python reference | existing 102425 masks through weight 3 | none within scope | sole registered implementation | software only | `CONDITIONAL PASS` |
| `forge-hotspot-8-4-v1-archived-table-decoder` | `forge-hotspot-8-4-v1` | archived table decoder | declared existing record | broader domain unproven | sole registered implementation | no physical implementation | `CONDITIONAL PASS` |
| `odd-column-secded-4-8-archived-table-decoder` | `odd-column-secded-4-8` | archived table decoder | declared existing record | broader domain unproven | sole registered implementation | no physical implementation | `CONDITIONAL PASS` |
| `safeforge-robust-8-4-v1-archived-table-decoder` | `safeforge-robust-8-4-v1` | archived table/abstention policy | declared existing record | broader domain unproven | sole registered implementation | no physical implementation | `CONDITIONAL PASS` |
| `forge-spatial-hotspot-72-64-v1-archived-table-decoder` | corresponding archived code | archived table decoder | declared existing record | mapping transfer unproven | sole registered implementation | no physical implementation | `CONDITIONAL PASS` |
| `forge-sram-portfolio-72-64-v1-geometry-filtered-joint-archived-table-decoder` | corresponding archived code | archived table decoder | declared existing record | geometry transfer unproven | sole registered implementation | no physical implementation | `CONDITIONAL PASS` |
| `forge-sram-portfolio-72-64-v1-spatial-hotspot-joint-archived-table-decoder` | corresponding archived code | archived table decoder | declared existing record | locality transfer unproven | sole registered implementation | no physical implementation | `CONDITIONAL PASS` |
| `odd-column-secded-64-72-archived-table-decoder` | `odd-column-secded-64-72` | archived table decoder | declared existing record | broader domain unproven | sole registered implementation | no physical implementation | `CONDITIONAL PASS` |
| `safeforge-robust-72-64-mapping-v1-archived-table-decoder` | mapping-robust archived code | archived abstaining table | declared existing record | physical mapping transfer unproven | sole registered implementation | no physical implementation | `CONDITIONAL PASS` |

## Unregistered implementations, generated widths, wrappers, and aliases

Every concrete generated-width file is listed. A row can name several modules only when they are encoder/decoder/SRAM/top wrappers in the same file and share one construction.

| Artifact/implementation | Dimensions represented | Status and identity | Evidence/fairness consequence | Gate 01 |
|---|---|---|---|---|
| `rtl/ecc_generated/secded_8b.v` | `(13,8)` | generated positional SECDED encoder/decoder/SRAM/top; unregistered | no archived identity/differential certificate; cannot enter portfolio | `NOT IMPLEMENTED` |
| `rtl/ecc_generated/secded_16b.v` | `(22,16)` | same generated family | same | `NOT IMPLEMENTED` |
| `rtl/ecc_generated/secded_32b.v` | `(39,32)` | same generated family | same | `NOT IMPLEMENTED` |
| `rtl/ecc_generated/secded_64b.v` | `(72,64)` | duplicate policy family of registered positional SECDED | must prove bit-exact equivalence rather than count as a new code | `NOT ASSESSABLE` |
| `rtl/ecc_generated/secdaec_64b.v` | `(72,64)` | duplicate bounded adjacent-pair policy family | inherits no DAEC guarantee; registered policy has counterexamples | `FAIL` |
| `rtl/ecc_generated/taec_8b.v` | `(13,8)` | generated positional policy, not a distinct certified TAEC matrix | missing construction and miscorrection certificate | `NOT IMPLEMENTED` |
| `rtl/ecc_generated/taec_16b.v` | `(22,16)` | same | same | `NOT IMPLEMENTED` |
| `rtl/ecc_generated/taec_32b.v` | `(39,32)` | same | same | `NOT IMPLEMENTED` |
| `rtl/ecc_generated/taec_64b.v` | `(72,64)` | duplicate collision-prone policy family | registered 64-bit policy fails adjacent triples | `FAIL` for TAEC claim |
| `rtl/ecc_generated/bch_8b.v` | `(14,8)` | BCH-labelled ad hoc parity equations, not certified primitive BCH | generator/decoder identity and distance unresolved | `FAIL` for BCH claim |
| `rtl/ecc_generated/bch_16b.v` | `(24,16)` | same | same | `FAIL` for BCH claim |
| `rtl/ecc_generated/bch_32b.v` | `(45,32)` | same | same | `FAIL` for BCH claim |
| `rtl/ecc_generated/bch_51b.v` | `(63,51)` | same historical family, distinct from valid primitive BCH reference | must not inherit valid BCH evidence | `FAIL` |
| `rtl/ecc_generated/polar_8b.v` | `(16,8)` | transform encoder plus bounded/practical decoder model; unregistered | no declared SRAM correction universe or SC/SCL certificate | `NOT IMPLEMENTED` |
| `rtl/ecc_generated/polar_16b.v` | `(32,16)` | same | same | `NOT IMPLEMENTED` |
| `rtl/ecc_generated/polar_32b.v` | `(64,32)` | same | same | `NOT IMPLEMENTED` |
| `rtl/ecc_generated/polar_48b.v` | `(64,48)` | same | same | `NOT IMPLEMENTED` |
| `rtl/ecc_generated/polar_96b.v` | `(128,96)` | same | same | `NOT IMPLEMENTED` |
| `asic/{secded,secdaec,taec,bch}/{encoder,decoder,sram_*_top}.sv` | fixed 64/51-bit wrappers | wrappers around `asic/rtl/*`, not independent mathematical implementations | include wrapper/storage overhead in later PPA, but do not multiply scientific candidates | `NOT ASSESSABLE` |
| `asic/polar/*_{64_32,64_48,128_96}.sv` | `(64,32)`, `(64,48)`, `(128,96)` | three fixed Polar wrapper/configuration bundles | no registered correction guarantee or differential deployed-decoder certificate | `NOT IMPLEMENTED` |
| `asic/rtl/sram/sram_wrappers.sv` | SECDED/TAEC 8,16,32; BCH 8,16,32; Polar 8,16,32 | parameterized wrappers plus 12 named width wrappers | duplicate interfaces to unregistered cores; no new identity | `NOT IMPLEMENTED` |
| `asic/rtl/common/ecc_entries.sv` | SECDED/SEC-DAEC/TAEC/BCH/Polar entries | family entry wrappers | deployment plumbing, not independent evidence | `NOT IMPLEMENTED` |
| `src/bch63.cpp`, `src/bch63.hpp` | `(63,51,t=2)` | independent C++ duplicate of valid primitive BCH policy | useful differential evidence; not a separate code | `CONDITIONAL PASS` as supporting evidence |
| `src/SecDaec64.hpp` | `(72,64)` | C++ duplicate of positional bounded adjacent-pair family | cannot enter selection independently; DAEC claim rejected | `FAIL` for DAEC claim |
| `src/BCHvsHamming.cpp`, `src/Hamming32bit1Gb.cpp`, `src/Hamming64bit128Gb.cpp`, `src/PracticalSRAMSimulator.cpp` | mixed demo/workload configurations | unregistered simulators/helpers, not frozen code/decoder identities | numerical outputs require separate provenance; names such as 1GB/128GB do not establish a fair hardware comparison | `NOT ASSESSABLE` |
| `taec_hamming_sim.py` and TAEC coverage Monte Carlo inputs | family-level coverage model | assumptions without executable distinct TAEC matrix/decoder identity | sensitivity only; never correction proof | `NOT IMPLEMENTED` |
| `polar.py` / Polar analytical bound model | communication-channel analytical proxy | no deployed SRAM decoder | cannot support SRAM correction or PPA claims | `NOT IMPLEMENTED` |
| external repetition fixture under `tests/fixtures/multi_ecc_external/` | `(3,1)` | test-only framework plugin | excluded from scientific counts by design | `PASS` only as interface fixture |
| thesis mentions of `(75,64)` TAEC I6/I7 | claimed literature/design identity | no matrix, generator, lookup table, RTL, or executable simulator found | not implemented; no comparison permitted | `NOT IMPLEMENTED` |
| LDPC and Reed–Solomon mentions | literature only | no repository encoder/decoder/framing identity | not portfolio candidates | `NOT IMPLEMENTED` |
| legacy selector aliases `SEC-DAEC`, `TAEC`, `BCH`, etc. | family labels | no one-to-one mapping to verified implementation IDs | legacy selector agreement is not assessable until identity mapping is frozen | `NOT ASSESSABLE` |

## Construction and policy conclusions

1. A decoder policy is not a mathematical code. Conventional SECDED, bounded SEC-DAEC, and bounded TAEC use the same `(72,64)` extended-Hamming codeword set.
2. The degree-12 repository cyclic code is not the registered valid primitive BCH despite equal `(63,51)` dimensions. The former has existing exact `d=2` and single-bit counterexamples; the latter has an existing primitive-field construction and `d=5` record.
3. The repository contains no distinct `(75,64)` I6/I7 TAEC construction.
4. Hsiao and positional extended Hamming are kept distinct because no coordinate-equivalence proof is present.
5. Comparisons across different `k`, `n`, and rates are scientifically interpretable only after equal-useful-capacity construction, integer codeword/padding accounting, identical physical context, and complete codec/storage overhead.
6. All positive correctness statuses remain provisional for Gate 02. The isolated checkout could not reload the registry because a raw-byte SHA-256 is sensitive to Git's LF-to-CRLF conversion; normalized bytes match, but Gate 01 did not alter the hash mechanism.
