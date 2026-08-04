# Reproducible ICCAD #1723 Revision Findings

- Operating scenarios: 3
- ECC families: 5
- ECC configurations: 5
- Candidate-scenario evaluations: 15
- GREEN-ECC versus lookup differences: 3
- Polar Pareto memberships: 0
- Exact/legacy first-front agreement: True

## Selection fabric

- Fixed physical container: 128 bits
- Configured topology MUX count: 784 2:1 cells
- Physical PPA characterized: False

| Topology | Engines | 2:1 MUX cells | Max depth | Protected metadata bits | PPA status |
|---|---:|---:|---:|---:|---|
| fixed | 1 | 0 | 0 | 0 | zero_selection_overhead |
| parallel | 5 | 784 | 3 | 9 | uncharacterized_without_exact_pvt_provider |
| gated_parallel | 5 | 784 | 3 | 9 | uncharacterized_without_exact_pvt_provider |
| shared_reconfigurable | 1 | 1296 | 3 | 9 | uncharacterized_without_exact_pvt_provider |

## Counterfactual selections

- `moderate-low-carbon`: lookup `sec-daec-64` -> GREEN-ECC `bch-63-51-t2`. Exact modeled reliability changes the choice; adaptive physical PPA is uncharacterized, so this is not evidence of a lifecycle-carbon advantage.
- `moderate-high-carbon`: lookup `sec-daec-64` -> GREEN-ECC `bch-63-51-t2`. Exact modeled reliability changes the choice; adaptive physical PPA is uncharacterized, so this is not evidence of a lifecycle-carbon advantage.
- `heavy-fault-regime`: lookup `bch-63-51-t2` -> GREEN-ECC `taec-64`. Exact modeled reliability changes the choice; adaptive physical PPA is uncharacterized, so this is not evidence of a lifecycle-carbon advantage.

## Score conclusion

- `heavy-fault-regime`: winners={'ESII': 'taec-64', 'GS': 'taec-64', 'NESII': 'taec-64'}; all-same=True; component-wise winner=None; rank correlations={'ESII_vs_GS': 1.0, 'ESII_vs_NESII': 1.0, 'NESII_vs_GS': 1.0}.
- `moderate-high-carbon`: winners={'ESII': 'bch-63-51-t2', 'GS': 'bch-63-51-t2', 'NESII': 'bch-63-51-t2'}; all-same=True; component-wise winner=None; rank correlations={'ESII_vs_GS': 0.9, 'ESII_vs_NESII': 1.0, 'NESII_vs_GS': 0.9}.
- `moderate-low-carbon`: winners={'ESII': 'bch-63-51-t2', 'GS': 'bch-63-51-t2', 'NESII': 'bch-63-51-t2'}; all-same=True; component-wise winner=None; rank correlations={'ESII_vs_GS': 0.9, 'ESII_vs_NESII': 1.0, 'NESII_vs_GS': 0.9}.

## Polar ablation

- `moderate-low-carbon` / `polar-64-48-sc`: Pareto=False; FIT=187.372; projected carbon=168.032 kg; projected latency=2 ns; dominated by=['sec-ded-64', 'sec-daec-64', 'taec-64'].
- `moderate-high-carbon` / `polar-64-48-sc`: Pareto=False; FIT=187.372; projected carbon=168.044 kg; projected latency=2 ns; dominated by=['sec-ded-64', 'sec-daec-64', 'taec-64'].
- `heavy-fault-regime` / `polar-64-48-sc`: Pareto=False; FIT=936.862; projected carbon=168.038 kg; projected latency=2 ns; dominated by=['sec-ded-64', 'sec-daec-64', 'taec-64'].

## Validation boundary

The repository contains no Liberty file, synthesis report, STA report, SPICE deck, or measured MUX data. Accordingly, physical adaptive PPA and lifecycle-carbon advantages are not claimed.
