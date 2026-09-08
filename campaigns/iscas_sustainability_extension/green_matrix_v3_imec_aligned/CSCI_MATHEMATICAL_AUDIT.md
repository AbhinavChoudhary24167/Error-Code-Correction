# CSCI mathematical audit

## Verdict

CSCI is dimensionally and mathematically defensible as a conditional lifecycle
intensity, provided the functional unit and boundary are fixed, correct service
is not inferred from logical mask frequency, all included carbon terms are
qualified, and hard reliability/SLA constraints are applied first.  It is not
currently numerically qualified for U0 or E0.

## Properties and counterexamples

1. **Dimensions:** `kgCO2e / service`; CSCI_bit is `kgCO2e / payload bit`.
2. **Input domain:** carbon, requests, and probability are non-negative;
   `Q_correct` lies in `[0,1]`.
3. **Zero denominator:** `N_req × Q_correct = 0` is undefined, never epsilon-
   regularized.
4. **Zero carbon:** a qualified physical zero with positive service yields zero;
   missing carbon is not zero.
5. **Carbon monotonicity:** for positive service,
   `d CSCI/d C_LC = 1/(N_req Q_correct) > 0`.
6. **Reliability monotonicity:** at fixed carbon and requests,
   `d CSCI/d Q_correct = -C_LC/(N_req Q_correct^2) <= 0`.
7. **Candidate independence:** the value depends only on the candidate and its
   declared scenario, not cohort min/max values.
8. **Workload/lifetime:** if
   `C_LC = C_embodied + N_req e_service CI`, then
   `CSCI = C_embodied/(N_req Q) + e_service CI/Q`.  Embodied intensity
   amortizes with use and the operational term is the large-use asymptote.
   This statement fails if workload, failure probability, replacement, or
   lifetime carbon changes nonlinearly; those effects must be modeled.
9. **Grid sensitivity:** for fixed energy and other terms, operational CSCI is
   linear in use-grid CI.  Manufacturing-grid CI remains an independent input.
10. **Embodied/operational regimes:** at low utilization embodied carbon can
    dominate; at high utilization the per-service operational term can dominate.
11. **Payload scaling:** for a fixed access, CSCI_bit is CSCI divided by payload
    bits.  Access and bit rankings need not agree.  Example: A has access CSCI
    1 with 64 bits; B has 0.8 with 32 bits.  B wins per access, while A wins per
    bit (0.015625 versus 0.025).
12. **Reliability does not remove the hard gate:** a low-carbon design with an
    unacceptable SDC rate can have low CSCI but remains infeasible.
13. **Retry pathology guard:** retries add energy/latency but never inflate
    `N_req`.  Otherwise retry-heavy designs could manufacture denominator credit.
14. **SDC guard:** treating SDC as delivered service falsely improves CSCI and
    is prohibited.
15. **Uncertainty:** ratio distributions are propagated from input scenarios or
    defensible distributions.  If the service interval reaches zero, CSCI is
    unbounded/undefined; a symmetric error bar is not reported.
16. **Infinite lifetime:** with fixed per-service energy and stable Q, embodied
    contribution tends to zero and operational CSCI remains.  “Infinite
    lifetime” is not a physical input and cannot erase replacements or aging.
17. **Unit conversion:** J/kWh and kg/g scaling change numeric representation,
    not physical ranking, when converted explicitly.
18. **Missing data:** an included unavailable lifecycle term blocks absolute
    CSCI.  Excluded, included-zero, parametric, and unavailable are distinct.
19. **Baseline-relative interpretation:** a fixed-baseline CSCI ratio is valid
    under matched units/boundaries, but no cohort normalization is used.
20. **Zero operational energy:** CSCI can remain positive because embodied
    carbon is not implicitly removed.

The implementation and adversarial tests are in `core.py` and
`tests/test_green_matrix_v3_core.py`.
