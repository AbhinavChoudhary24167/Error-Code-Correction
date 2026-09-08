# GREEN v3.3 activity-complete E5 campaign

This is an additive campaign over the sealed GREEN v3.2 matched physical population. It does not alter historical evidence.

Build the deterministic audit, workload, and qualification artifacts:

```text
python campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5/build_campaign.py --repo .
```

Run a populated priority queue:

```text
python campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5/scripts/run_campaign.py
```

`run_campaign.py` creates `RUNTIME_STATE.json` on first execution. That file contains one campaign start and one hard deadline exactly 54,000 seconds later. Resume invocations load that deadline; they do not reset it. The default per-run timeout is null. An explicitly shorter job timeout is allowed, but the effective timeout is always clamped to the time remaining in the whole campaign.

The checked-in queue is intentionally empty until the complete-population post-route activity flow has been audited. This prevents an unaudited OpenROAD/OpenRAM command from spending the campaign budget. `CAMPAIGN_STATUS.json` and `FINAL_REPORT.md` record the resulting fail-closed E5 status.

