# Reproduce the DATE 2027 breadth-remediation campaign

## Fixed environment

Run from Windows PowerShell with WSL distribution `Ubuntu-24.04`, Docker available inside WSL, and repository commit `b51291442bbd04346dac939dea6ba7d532b9c5c4` plus this additive campaign change set. The physical flow is pinned to:

```text
openroad/orfs@sha256:f05cee3219a02f26289f02f00e11a3fc986ab51a482a0000a2da810cda219a6e
ORFS    56496f3980fb6e9e58f10c8aea4a98949c0fe5f2
OpenROAD ab6fd26351dc449e69059684dc6aa9ae9046eb36
```

The generators are intentionally write-once. They refuse to overwrite existing formal, synthesis, analysis, matrix, or run evidence. To repeat the experiment, use a fresh source-only reproduction checkout and a WSL instance in which `/var/lib/green-ecc-date2027-breadth-remediation` does not exist. Do not remove or reuse the qualified evidence root `/var/lib/green-ecc-date2027-revision2`.

The commands below assume this repository path:

```text
C:\Users\Abhinav\OneDrive\Desktop\ECC\Error-Code-Correction
/mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction
```

## 1. Structural-pair formal proof and synthesis sanity

```powershell
wsl -d Ubuntu-24.04 -u root -- python3 /mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction/campaigns/date_2027_breadth_remediation/scripts/qualify_structural_pair.py --repo /mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction
wsl -d Ubuntu-24.04 -u root -- python3 /mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction/campaigns/date_2027_breadth_remediation/scripts/synthesize_structural_pair.py --repo /mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction
```

The first command must emit `STRUCTURAL_PAIR_FORMAL_GATE = PASS` before any physical preparation. The second command must establish common-policy mapped structural distinctness. If either gate fails, stop Workstream A.

## 2. Freeze the physical bundle

```powershell
wsl -d Ubuntu-24.04 -u root -- python3 /mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction/campaigns/date_2027_breadth_remediation/scripts/prepare_physical_campaign.py --repo /mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction
```

This validates the frozen plans/contracts, verifies the exact container digest and protected source hashes, copies the qualified Hsiao trace byte-for-byte with provenance, generates the deterministic 5 ns trace, and creates the write-once external campaign root.

## 3. Structural-pair five-seed physical campaign

```powershell
wsl -d Ubuntu-24.04 -u root -- python3 /var/lib/green-ecc-date2027-breadth-remediation/policy/repo_snapshot/campaigns/date_2027_breadth_remediation/scripts/run_physical_matrix.py --workstream A
```

The frozen matrix executes exactly ten runs in seed-interleaved order: flat then hierarchical at 11, 13, 17, 19, and 23. Each case records its full Docker command, effective environment, logs, final physical artifacts, metadata, power report when eligible, and `raw-artifacts.sha256`.

## 4. Existing-power decomposition

```powershell
wsl -d Ubuntu-24.04 -u root -- python3 /mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction/campaigns/date_2027_breadth_remediation/scripts/analyze_power_decomposition.py --repo /mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction
```

This reads only immutable Revision-2 SECDED combinational/pipelined routes and reports. It verifies every evidence join and reproduces the published power and energy values before emitting the B CSV, JSON, and report.

## 5. Fresh 5 ns campaign

```powershell
wsl -d Ubuntu-24.04 -u root -- python3 /var/lib/green-ecc-date2027-breadth-remediation/policy/repo_snapshot/campaigns/date_2027_breadth_remediation/scripts/run_physical_matrix.py --workstream C
```

The frozen matrix executes exactly ten fresh implementations in seed-interleaved order: combinational then pipelined at 11, 13, 17, 19, and 23. It does not reuse a 10 ns database and admits operating-point energy only for timing-feasible routes.

## 6. Summary analysis and campaign tests

```powershell
wsl -d Ubuntu-24.04 -u root -- python3 /mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction/campaigns/date_2027_breadth_remediation/scripts/analyze_physical_campaign.py --repo /mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction --workstream A
wsl -d Ubuntu-24.04 -u root -- python3 /mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction/campaigns/date_2027_breadth_remediation/scripts/analyze_physical_campaign.py --repo /mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction --workstream C
python3 -m pytest -q campaigns\date_2027_breadth_remediation\tests
```

The analyzers verify the frozen policy manifest and every run-level raw-artifact manifest before producing per-seed and descriptive outputs. Zero-valued reference metrics retain absolute differences and report percentage effects as not assessable.

## 7. Existing regressions and final integrity verification

```powershell
make
make test
python3 -m pytest -q
& 'D:\Compiler Cpp\ucrt64\bin\python3.exe' campaigns\date_2027_breadth_remediation\scripts\audit_inventory.py --verify campaigns\date_2027_breadth_remediation\00_baseline_inventory.sha256 --result-json campaigns\date_2027_breadth_remediation\FINAL_baseline_integrity_check.json
python3 campaigns\date_2027_breadth_remediation\scripts\hash_campaign.py
```

A valid final integrity result has `status: PASS` and empty `changed`, `missing`, and `added` arrays. The current qualified result covers 79 repository files and 2,366 external Revision-2 files.

The final command creates `FINAL_campaign_inventory.sha256` and refuses to overwrite it. Run it only after the repository-resident campaign record is complete.

## Evidence locations

- Repository campaign: `campaigns/date_2027_breadth_remediation/`
- Immutable raw campaign: `/var/lib/green-ecc-date2027-breadth-remediation/`
- Frozen policy snapshot: `/var/lib/green-ecc-date2027-breadth-remediation/policy/`
- Workstream A raw runs: `/var/lib/green-ecc-date2027-breadth-remediation/runs/A/`
- Workstream C raw runs: `/var/lib/green-ecc-date2027-breadth-remediation/runs/C/`
- Historical read-only source for Workstream B: `/var/lib/green-ecc-date2027-revision2/`

No command in this procedure edits the DATE manuscript or any Revision-2 qualified artifact.
