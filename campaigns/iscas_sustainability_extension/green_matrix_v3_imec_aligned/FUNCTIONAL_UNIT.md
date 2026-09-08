# Functional unit

The primary functional unit is:

> one correct payload-bearing memory service delivered to the requester under
> a declared workload, service policy, payload size, latency/SLA, fault
> environment, and system boundary.

The access-normalized count is `N_req × Q_correct`.  For comparisons with
different exposed payload widths, the preferred normalization is
`B_payload × N_req × Q_correct`, called a `correct_payload_bit_service`.

An external request is counted once.  Internal retries and scrubs add activity,
energy, latency, and possibly failure risk; they do not create extra requested
services.  A corrected response or response after retry earns credit only when
it is correct and inside the declared SLA.  SDC never earns credit.  An
unrecovered DUE, detected failure, timeout, or SLA violation earns no credit.
External recovery may change this only when the service policy, time, energy,
replacement effects, and system boundary explicitly include it.

An access and a payload bit are different functional units.  CSCI and CSCI_bit
can rank architectures differently when payload widths differ; both payload
and request semantics therefore accompany every result.
