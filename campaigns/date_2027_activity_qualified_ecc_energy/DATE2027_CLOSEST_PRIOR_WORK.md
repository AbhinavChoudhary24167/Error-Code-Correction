# Closest Prior Work

## Closest work

Ghosh, Basu, and Touba, “Reducing Power Consumption in Memory ECC Checkers,” ITC 2004, DOI 10.1109/TEST.2004.1387407.

## Why it is close

It rejects activity-blind reasoning by using SPEC and MediaBench traces to optimize memory ECC checker power. It therefore has priority over any broad claim that workload traces or activity-aware ECC power analysis are new.

## Exact remaining gap

The verified remaining gap is narrower: a paired post-route study that keeps each architecture/seed implementation and final extracted parasitics fixed, contrasts its diagnostic vectorless ordering with explicit operation-normalized switching activity, and tests whether the conventional-versus-Hsiao SECDED ordering survives across the same physical seeds.

## Claim language allowed

Allowed: “We are not aware of prior work that tests this ordering-invariance question under matched final-route identity.”

Not allowed: “This is the first activity-aware ECC power analysis,” “real workloads have not been used for ECC,” or “Hsiao energy has never been physically evaluated.”

## Novelty consequence

The paper's novelty is experimental control plus the observed ranking failure, not the invention of activity-aware power analysis, the Hsiao code, an ECC optimization, or an RTL-to-GDS flow.

