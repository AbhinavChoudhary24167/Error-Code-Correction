# Residual external DRV inventory

Canonical final-route seed 11 retains exactly two genuine external rows, one per design. Exact values come from OpenSTA over the final ODB/SDC/SPEF; topology and route length come from final DEF.

| Design | Object | Driver / cell | Actual / required (ns) | Fanout | SPEF cap (pF) | Wire (um) | Status |
|---|---|---|---:|---:|---:|---:|---|
| U0 | `u_data/rstb` | `hold151/X` / `sky130_fd_sc_hd__buf_16` | 0.619147718 / 0.351 | 1 | 0.00213879 | 19.090 | VIOLATING |
| E0 | `u_protected_memory.u_data/rstb` | `hold824/X` / `sky130_fd_sc_hd__buf_16` | 0.615635812 / 0.351 | 1 | 0.00111857 | 10.670 | VIOLATING |

Closed targeted interfaces:

| Design | Object | Actual / required (ns) | Status |
|---|---|---:|---|
| U0 | `u_data/clk` | 0.042701319 / 0.351 | CLOSED |
| E0 | `u_protected_memory.u_data/clk` | 0.325266629 / 0.351 | CLOSED |
| E0 | `u_protected_memory.u_ecc/rstb` | 0.307288498 / 0.351 | CLOSED |
| E0 | `u_protected_memory.u_ecc/clk` | 0.135259956 / 0.351 | CLOSED |
