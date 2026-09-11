# GREEN operation-aware ISCAS 2027 paper package

This additive directory turns the GREEN v3.3 E5 campaign into a scoped manuscript and supporting analysis. The scientific evidence is sealed at commit `8cf245ac6ac8cb9b010c073d439f04eb204d48a1`; the builder refuses to proceed if the v3.3 evidence tree differs from that commit or if any of its 1,697 retained artifact hashes fails.

The package does not run synthesis, place-and-route, simulation, or power analysis. It reads the sealed aggregates, recomputes descriptive statistics, verifies the canonical E5 record chain, derives the workload boundary, constructs only qualified Pareto comparisons, and emits four figures.

Build and validate from the repository root:

```text
python3 paper/iscas2027_green_operation_aware/scripts/build_analysis.py
python3 paper/iscas2027_green_operation_aware/scripts/validate_analysis.py
```

The public ISCAS 2027 call and submission pages were checked on 2026-09-09. They give the regular-paper deadline but do not yet publish a final author kit or a regular-paper page limit. The package therefore retains the working design constraint of about four technical pages plus one references-only page. Recheck the [official submission page](https://2027.ieee-iscas.org/submission) before typesetting.

`MANUSCRIPT_DRAFT.md` is the paper text; `FINAL_REPORT.md` is the handoff decision record. `NEW_ARTIFACTS.sha256` seals every file in this directory except itself.
