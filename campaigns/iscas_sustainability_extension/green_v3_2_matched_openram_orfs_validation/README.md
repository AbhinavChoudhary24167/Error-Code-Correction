# GREEN v3.2 matched OpenRAM + ORFS validation

This additive campaign asks whether a broader ECC population can be freshly
functionally validated and physically implemented at a matched boundary. It
does not modify GREEN Matrix v3.2 or create v3.3.

Current classification: `GREEN_V3_2_MATCHED_ORFS_MULTI_ARCH_PHYSICAL_VALIDATION_COMPLETE_OPENRAM_REGENERATION_PARTIAL_RUNTIME_CUTOFF_INHERITED_SRAM_MACROS_E4_E5_PENDING_ABSOLUTE_RELIABILITY_AND_LIFECYCLE_BLOCKED`

Reproduce fresh RTL validation with:

```bash
python3 scripts/run_functional_validation.py --repo <repository-root>
```

Run the pinned OpenRAM attempt in its isolated WSL namespace with:

```bash
python3 scripts/run_openram_campaign.py --repo <repository-root> --timeout-seconds 10800
```

The three-hour cutoff is explicit evidence metadata; it is not reported as a
compiler pass. The historical OpenRAM source, virtual environment, and PDK are
mounted read-only.

Run the WSL ORFS matrix with:

```bash
python3 scripts/run_orfs_campaign.py --repo <repository-root> --workers 2
```

Rebuild committed tables and reports deterministically with:

```bash
python3 build_campaign.py --repo <repository-root>
```

Full physical outputs are preserved under the external WSL evidence root
recorded in `RUN_MANIFEST.json`; hashes and compact reports are committed here.
