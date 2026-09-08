# Attempt06 backend decision

Classification: `SRAM22_PARTIALLY_QUALIFIED`  
Recommendation: `KEEP_GATE3_FAILED`

SRAM22 provides immutable, licensed, exact 256×64 and 256×8 published macros with consistent GDS, LEF, SPICE, FF/TT/SS Liberty, and executable Verilog. Both functional models and the two-bank Hsiao `(72,64)` composition qualify. Both macros import into OpenROAD; E0 reaches merged final GDS with zero detailed-route DRC errors.

Candidate A cannot be classified `SRAM22_BACKEND_QUALIFIED` because U0 detailed routing did not converge, the mandatory U0 successful placement/routing criterion is unmet, final timing design-rule/hold limits remain, leaf LVS did not independently reproduce, and no public SRAM22-specific foundry DRC waiver or complete signoff collateral exists. The dense-bitcell hypothesis is supported—100% of public-deck markers localize to SRAM-internal hierarchy—so future integration may defensibly black-box the immutable hardened macro with a documented risk acceptance. That evidence does not transform leaf DRC into PASS.

The historical OpenRAM/SKY130 conclusion remains `MATERIALIZATION_SEMANTICS_UNRESOLVED` / `STOP_OPENRAM_SKY130_BACKEND`. No repair, add-mask mapping, internal macro edit, or Gate 4 work occurred. Gate 3 remains `FAIL`; Gate 4 remains `NOT_STARTED_UNAUTHORIZED`; Attempt07 was not begun.

