# GREEN v3.3 activity-complete E5 campaign

This is an additive campaign over the sealed GREEN v3.2 matched physical population. It does not alter historical evidence.

Rebuild the deterministic executed-evidence analysis and provenance seal:

```text
python campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5/build_campaign.py --repo .
```

The scientific queue has completed and its original deadline has expired. Do
not rerun it as a new campaign. For reference, the deadline-aware controller is:

```text
python campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5/scripts/run_campaign.py
```

`run_campaign.py` creates `RUNTIME_STATE.json` on first execution. That file contains one campaign start and one hard deadline exactly 54,000 seconds later. Resume invocations load that deadline; they do not reset it. The default per-run timeout is null. An explicitly shorter job timeout is allowed, but the effective timeout is always clamped to the time remaining in the whole campaign.

The audited queue completed five matched 10 ns SECDED/Hsiao seeds. The campaign
contains 46 qualified ECC-logic E5 operation records; SRAM macro-internal energy
remains incomplete, so whole-memory E5 is still blocked. `CAMPAIGN_STATUS.json`
and `FINAL_REPORT.md` give the final scope and conclusions.
