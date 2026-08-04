# Transition-aware ECC and architecture co-design

## Ordered decision model

Let the operating trace be

\[
\mathcal{X}=\{x_1,\ldots,x_T\}.
\]

Each epoch records duration, accesses, active capacity, fault regime, FIT
multiplier, VDD, temperature, read/write mix, reliability and latency limits,
grid carbon intensity, and uncertainty intervals. A physical design `a` fixes
deployment mode, topology, granularity, supported ECC engines, protected
metadata format, and continuing overhead. An epoch state is

\[
m_t=(a,\mathrm{ECC}_t,\mathrm{scrub}_t,\mathrm{metadata}_a).
\]

Topology and granularity cannot change freely at runtime. GREEN-ECC solves one
schedule for each feasible physical design and then compares the complete
design totals. This is the joint co-design step.

For lifecycle carbon,

\[
C(a,m_{1:T})=C_{\mathrm{embodied}}(a)
+\sum_{t=1}^{T} C_{\mathrm{op}}(x_t,m_t)
+\sum_{t=2}^{T}C_{\mathrm{transition}}(x_t,m_{t-1},m_t).
\]

Energy replaces each carbon term with joules. Operational conversion uses

\[
C_{\mathrm{op},t}[\mathrm{kgCO_2e}]
=E_t[\mathrm{J}]\,CI_t[\mathrm{kgCO_2e/kWh}]/3.6\times10^6.
\]

Reliability, latency, capacity, area, transition safety, minimum dwell, and
maximum switching rate are hard constraints. An unavailable metric makes a
required objective or constraint infeasible; it is never silently zero.

## Exact scheduler

With one-epoch costs `c_t(m)` and transition costs `s_t(m',m)`, the basic
recurrence is

\[
D_t(m)=c_t(m)+\min_{m'}[D_{t-1}(m')+s_t(m',m)].
\]

Infeasible modes and unsafe/uncharacterized transitions have infinite cost.
The basic time complexity is `O(T M^2)` and memory is `O(T M)` when the path is
retained. Minimum dwell `D` and a maximum switch-count state `S` increase the
implemented worst-case bound to `O(T M^2 D S)`. The unrestricted and extended
implementations are exact; no pruning is applied.

The primary objective is lifecycle energy or lifecycle carbon. Pareto methods
remain available elsewhere in GREEN-ECC but the scheduler does not trade a FIT
violation against an arbitrary scalar saving.

## Break-even conditions

For transition `i -> j`, separate codec cost from continuing adaptability:

\[
\Delta e=e_i-e_j-e_{\mathrm{adaptive}}.
\]

When `Delta e > 0`,

\[
N_{BE}^{E}=\left\lceil
\frac{E_{\mathrm{migration}}+E_{\mathrm{control}}}
{\Delta e}\right\rceil.
\]

If the numerator is zero, benefit is immediate. If the denominator is zero or
negative, the change is never beneficial. Missing terms return “insufficient
characterization”; a forbidden or overlong migration returns “infeasible
transition.”

For carbon,

\[
N_{BE}^{C}=\left\lceil
\frac{C_{\mathrm{migration}}+\Delta C_{\mathrm{embodied,allocated}}}
{c_i-c_j-c_{\mathrm{adaptive}}}\right\rceil.
\]

Within an already-instantiated adaptive design, common MUX/controller overhead
cancels between two ECC states. When comparing adaptive against fixed hardware,
incremental implementation, leakage, metadata, and per-access overhead are
charged exactly once. This prevents double counting.

Two dimensionless diagnostics retain direct physical meaning:

\[
\rho_{transition}=C_{transition}/B_{gross,epoch},\qquad
\rho_{adaptive}=C_{all\ adaptability}/B_{gross,trace}.
\]

Adaptation is net beneficial only below one. These ratios are explanations,
not another score.

## Chance constraints and hysteresis

Relative uncertainty intervals yield a per-mode feasibility probability. The
robust scheduler requires

\[
P(FIT\le FIT_{max})P(L\le L_{max})\ge 1-\epsilon
\]

under the declared independence approximation, then adds a stated risk margin
to the primary objective. The deployable rule changes mode only if

\[
\sum_{\tau=t}^{t+H}(c_\tau(m_{current})-c_\tau(m_{new}))
>s_t+\Gamma_{uncertainty}+\Gamma_{benefit}.
\]

It also enforces minimum dwell, maximum switches, confidence threshold, safe
fallback, and abstention. A hard constraint violation can force a safety switch
even when economic break-even has not been reached.

## Granularity accounting

Whole-memory, bank, and page designs calculate regions, affected regions,
migrated words, MUX replication, fan-out, and protected mode bits. Finer
granularity reduces migrated words only when the changing region is smaller,
but increases metadata and lookup/routing burden. Word-level selection is
rejected by default because no credible per-word physical characterization is
present.

The supplied example is a normalized physical-unit sensitivity experiment.
Replacing it with a technology result requires characterized mode energy,
leakage, area, transition latency/energy, metadata lookup, controller, and
embodied-carbon providers at the exact PVT point.
