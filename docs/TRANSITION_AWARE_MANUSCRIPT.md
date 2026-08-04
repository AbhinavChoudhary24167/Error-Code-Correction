# Insertion-ready transition-aware manuscript narrative

> The authoritative LaTeX paper/thesis source is absent. This section is
> insertion-ready Markdown and has not been presented as a compiled manuscript.

## Motivation

Different operating epochs can favor different ECCs, but a sequence of locally
preferred codes is not automatically a good implementation. Supporting several
codes requires MUXes, inactive engines or a shared datapath, protected format
metadata, and control. Changing a populated region additionally requires a safe
read–decode–re-encode–write transition. The benefit of the next mode must repay
both the transition and the continuing cost of adaptability within the
remaining workload horizon.

GREEN-ECC therefore asks whether protection should change, not only which ECC
is best in the current snapshot. It selects a fixed/configurable/adaptive
architecture and granularity, schedules ECC modes across an ordered trace, and
emits the schedule and transition conditions consumed by a controller.

## Method summary

Hard FIT, latency, capacity, area, dwell, and safety constraints are applied
before optimization. For each physical design, an exact dynamic program
minimizes lifecycle energy or carbon including asymmetric transitions. Fixed
and boot-configurable designs retain one ECC across the trace; adaptive designs
may change among instantiated modes. The globally preferred design is the
minimum complete feasible total.

Comparison policies are the best static ECC, fault-regime lookup, snapshot
oracle that ignores transition costs, greedy switching, robust hysteresis,
exact transition-aware scheduling, and chance-constrained robust scheduling.
The snapshot oracle is intentionally non-deployable: its charged total exposes
when local recommendations become globally inferior.

## Main result language

The default experiment suite is synthetic and supports threshold conclusions,
not technology-specific savings. In the generated periodic and noisy traces,
the snapshot oracle follows short-lived local preferences but becomes worse
than the best fixed ECC once migration is charged. The exact scheduler retains
one mode and avoids those changes. Longer one-time and combined phases can
amortize migration, causing an adaptive shared design to win under the supplied
physical-unit sensitivity inputs. The break-even map—not a universal winner—is
the principal result.

Whole-memory reconfiguration minimizes metadata and lookup cost but migrates
the complete active memory. Bank/page granularity reduces migration for local
changes while replicating protected metadata and selection structures. The
experiment reports where this trade changes sign; it does not claim that
page-level control is practical at an uncharacterized technology.

## Figure interpretations

1. **Architecture comparison:** the winning implementation changes between
   stationary/short traces and long phase changes; adaptability is not free.
2. **Scheduling formulation:** constraints precede lifecycle minimization, and
   transition cost connects adjacent decisions.
3. **Mode timeline:** snapshot policies oscillate while exact/hysteretic policies
   suppress changes whose horizon benefit is insufficient.
4. **Break-even map:** the adaptive region grows with epoch accesses and shrinks
   with migration energy.
5. **Topology/granularity map:** finer control helps only in bounded localized
   transition regions.
6. **Waterfall:** gross operational saving is reduced by migration and allocated
   implementation overhead before net benefit is claimed.
7. **Robustness/regret:** nominal optimality and decision stability are distinct.
8. **Scalability:** exact scheduling follows `O(T M^2)` for the basic state.

## Limitations

No Liberty, synthesis, STA, SPICE, or measured controller/MUX/migration data is
available. Example values are explicitly synthetic sensitivity inputs. The RTL
implements a transition sequencer and recovery protocol but not the memory
migration datapath. Traces are generated, not measured workloads. Consequently,
the supported claim is that the framework identifies conditional break-even
regions and produces an exact transition-safe schedule for supplied models; no
silicon, node-specific, universal-optimality, or “first” claim is made.

## Suggested title

**When Is Adaptive ECC Worth It? Transition-Aware Reliability Scheduling for SRAMs**

Alternative:

**GREEN-ECC: Transition-Aware and Overhead-Conscious ECC Adaptation for Sustainable SRAMs**
