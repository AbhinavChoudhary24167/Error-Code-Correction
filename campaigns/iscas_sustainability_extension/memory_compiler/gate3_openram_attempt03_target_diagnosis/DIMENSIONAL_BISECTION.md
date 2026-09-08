# Dimensional-bisection decision

The prerequisite control did not pass. The first and only attempt03 target executed was the stock-compatible 16x8 control, and it failed DRC, LVS, and Liberty characterization. Under the campaign rule, 256x8, 256x64, and a new 256x72 qualification run were therefore **not run**.

There is no scientifically valid width/depth transition to report. The earliest failure boundary is the control itself (`CONTROL_FAIL`), so the pinned integration is unhealthy before any 256-word or 72-bit stress is introduced. The 256x72 row in `dimensional_bisection.csv` contains only clearly labeled prior attempt02 evidence; it is not an attempt03 bisection execution.

Separate output namespaces were preserved, and no target reused the control output directory.

