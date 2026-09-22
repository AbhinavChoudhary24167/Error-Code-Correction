# Activity-qualified ECC energy evidence report — revision 2

## Scope

Revision 2 retains the activity-qualified main study and adds bounded temporal, structural, timing-condition, and BCH feasibility controls. The delta convention is changed minus baseline. The routed-ECC-logic measurement boundary excludes SRAM-macro internal energy and silicon claims.

## Main evidence

- Ten routed implementations are timing-feasible at 10 ns, with five matched deterministic seeds per architecture.
- The main dataset contains 46 activity records and 23 matched operation/seed cells.
- Hsiao is lower in 5/5 vectorless physical pairs and 4/23 operation-specific energy cells.
- All admitted activity records cover all 72 output roots; functional logic coverage is 99.298390–99.356061% and sequential coverage is 100%.
- Clean-read internal and net-switching contributions oppose one another in all five pairs.

## Control evidence

- The temporal SECDED pair has an exact systematic transaction relation after two-cycle response alignment; latency and clock burden differ.
- Tightening the temporal-control target from 10 ns to 5 ns changes effect magnitude without reversing the reported directions.
- The structural Hsiao pair is exactly qualified and exhibits a small mixed physical displacement.
- The evaluated BCH(78,64,t=2) realization is timing-feasible in 0/5 attempts at the common target; this is not a claim about the BCH family.

## Interpretation and limits

Use `data/controlled_implementation_statistics.json`, `FORMAL_QUALIFICATION_MATRIX.csv`, the claim ledger, and the provenance manifest for exact identities and hashes. The evidence is conditional on the recorded implementation, flow, corner, workload classes, and seeds. It does not support a global ECC ranking, whole-memory energy, physical event rates, population inference, or silicon behavior.

Publication manuscripts, review material, and submission PDFs are not part of this repository.
