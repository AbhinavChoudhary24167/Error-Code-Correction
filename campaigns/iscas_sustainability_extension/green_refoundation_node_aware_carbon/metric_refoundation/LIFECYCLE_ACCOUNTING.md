# Lifecycle accounting boundary

The campaign defines

`C_LC = C_emb + C_op + C_replacement_or_external_recovery`.

`C_emb` includes supported wafer-to-good-die processing plus separately stated
mask NRE, package, and other terms. `C_op` includes normal read/write, ECC
encode/decode, correction, scrub, retry, local recovery, and idle leakage
energy exactly once. The third term is reserved for genuinely additional
burdens such as device replacement, maintenance, or recomputation outside the
local memory boundary. It is zero unless evidence explicitly establishes such
a burden.

The current SKY130 rows have neither qualified absolute embodied carbon nor
qualified operational energy. Therefore `C_LC`, GSE, and GCI remain empty; a
missing term is not interpreted as zero.
