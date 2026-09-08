# Marginal Reliability Carbon Cost (MRCC)

For candidate `a` and one fixed, declared, physically matched baseline `b`,

`MRCC(a|b) = (C_LC,a - C_LC,b) / (N_correct,a - N_correct,b)`.

The unit is `kgCO2e / additional correct service`.  The domain requires
`Delta N_correct > 0`.  With zero improvement MRCC is undefined.  With negative
improvement it is not an incremental reliability gain and the pair belongs in a
dominance/Pareto classification.  No epsilon floor is permitted.

Candidate and baseline must match technology/process scenario, system boundary,
payload/functional unit, workload, service policy, request count, lifetime,
grid scenarios, and allocation method unless the comparison explicitly varies
one of them.  U0 is a permissible baseline only when those matches hold.

MRCC is a marginal diagnostic, not the primary selector.  A negative numerator
with positive service improvement is meaningful: the candidate saves carbon
while delivering more correct service.  A positive MRCC does not say whether
the service improvement is necessary; hard constraints decide that first.
