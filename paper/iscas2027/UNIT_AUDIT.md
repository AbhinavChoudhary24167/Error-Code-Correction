# ISCAS 2027 Unit Audit

## Audit rule

Every reported metric retains its native measurement boundary and unit. Unit
conversion is performed only after numerator, denominator, time window, and
system boundary are explicit. The paper does not normalize by macro capacity,
codeword bit, die area, or fault coverage because those normalizations would mix
unqualified quantities.

## Metric ledger

| Metric | Source quantity / formula | Native unit | Paper unit | Boundary and audit result |
|---|---|---:|---:|---|
| Setup WNS | final OpenSTA setup report | ns | ns | One routed wrapper identity at one target/corner/seed. PASS. |
| Hold WNS | final OpenSTA hold report | ns | ns | Same identity as setup. Full timing requires both WNS values nonnegative. PASS. |
| Standard-cell area | sum reported by physical flow | um^2 | $\mu$m$^2$ | Logic/wrapper plus macro-interface cells; SRAM macro area excluded from the headline delta. PASS. |
| Routed wirelength | final route report | um | $\mu$m | Hsiao minus conventional within a matched seed. PASS. |
| Via count | final route report | count | vias | Integer resource count; the reported mean may be fractional across seeds. PASS. |
| Per-record operation energy | $E=P_{a,s,o}T_{s,o}/N$ | W x s / operation | J/op | $P$ is activity-qualified ECC-logic power; $T$ is the measured trace window after warm-up; $N=256$ measured operations. SRAM-macro internal energy excluded. PASS. |
| Energy display conversion | $E_{\rm pJ}=E_{\rm J}\times10^{12}$ | J/op | pJ/op | Applied after reading each architecture/seed/operation record. PASS. |
| Paired energy delta | $\Delta E_{s,o}=E_{H,s,o}-E_{C,s,o}$ | J/op | pJ/op | Same seed, clock, operation, activity method, parasitics, and ECC-logic scope. PASS. |
| Mean operation delta | $\overline{\Delta E_o}=|S|^{-1}\sum_{s\in S}\Delta E_{s,o}$ | pJ/op | pJ/op | $S$ is derived by the setup+hold+complete-operation gate, yielding seeds 13, 17, 19, and 23. Descriptive mean only. PASS. |
| Workload energy delta | $\Delta E(\mathbf p)=\sum_o p_o\overline{\Delta E_o}$ | dimensionless x pJ/op | pJ/op | $p_o\ge0$ and $\sum p_o=1$. It is a conditional decision equation, not an observed workload distribution. PASS. |
| Operational carbon delta | $\Delta C_{\rm op}=N_{\rm life}I_g\Delta E$ | operation x kgCO2e/J x J/operation | kgCO2e | If grid intensity is supplied in kgCO2e/kWh, divide by $3.6\times10^6$ before use. No numerical grid value is assumed. PASS (symbolic). |
| Lifecycle carbon delta | $\Delta C_{\rm life}=\Delta C_{\rm emb}+\Delta C_{\rm op}$ | kgCO2e + kgCO2e | kgCO2e | Embodied difference is unqualified for the local SKY130 boundary, so the result remains symbolic. PASS (symbolic only). |
| Break-even operations | $N^*=\Delta C_{\rm emb}/[-I_g\Delta E]$ for $\Delta E<0$ | kgCO2e / (kgCO2e/operation) | operations | Defined only for the stated sign conditions. No numeric value reported. PASS (conditional). |
| Activity root coverage | annotated required roots / required roots | fraction | count and fraction | Campaign records 72/72 SRAM-output roots; this does not imply macro-internal state coverage. PASS with boundary qualifier. |
| Functional logic coverage | annotated functional nets / required functional nets | fraction | percent when displayed | Campaign range is retained in source evidence but not promoted to a headline claim. PASS. |

## Dimensional checks

1. $1\,\mathrm{W}=1\,\mathrm{J/s}$, hence $P\,T/N$ has units J/op.
2. A pJ/op coefficient must be multiplied by $10^{-12}$ before use with
   $I_g$ in kgCO2e/J.
3. kgCO2e/kWh cannot be multiplied directly by J/op; conversion to kgCO2e/J is
   mandatory.
4. Standard-cell area and inherited macro area are not summed in any headline
   comparison because their qualification boundaries differ.
5. Categorical correction/detection service has no unit and is never converted
   into FIT, SDC, DUE, lifetime, or avoided-carbon values.

## Prohibited denominator substitutions

- No energy per protected bit: macro-internal energy is incomplete.
- No carbon per corrected error: field error frequency is absent.
- No carbon per die or wafer: a matched SKY130 manufacturing inventory and yield
  model are absent.
- No reliability per routed area: Qcrit, particle environment, and bit mapping
  are absent.

