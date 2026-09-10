# Reader-Facing Terminology Map

| Internal/source term | Manuscript term | Rule |
|---|---|---|
| `SECDED` architecture ID | conventional SECDED | Define once as Hamming-style parity organization. |
| `HSIAO_SECDED` | Hsiao SECDED | Use the historical construction name. |
| `E4_DIAGNOSTIC_VECTORLESS` | vectorless diagnostic | Never present as operation energy. |
| `E5_LOGIC_ACTIVITY_QUALIFIED_MACRO_ENERGY_INCOMPLETE` | activity-qualified ECC-logic energy; macro energy excluded | Preserve the limitation in prose/captions. |
| `READ_CLEAN` | clean read | Energy normalized per completed operation. |
| `WRITE_CLEAN` | clean write | Energy normalized per completed operation. |
| `READ_SINGLE_BIT_ERROR_CORRECT` | single-bit correction | A read that exercises correction. |
| `READ_DOUBLE_BIT_ERROR_DETECT` | double-bit detection | A read that exercises detection. |
| `IDLE` | scheduled idle window | Do not imply arbitrary residency energy. |
| `delta_definition=HSIAO_SECDED_MINUS_SECDED` | $\Delta E=E_{Hsiao}-E_{conventional}$ | Negative always means Hsiao lower. |
| physical seed | route seed / physical seed | Treat as a paired realization, not a statistical population sample. |
| final zero-delay gate-netlist VCD | final-routed-netlist switching activity | State zero-delay limitation in threats. |
| final SPEF | extracted final-route parasitics | Never call post-layout silicon. |

Forbidden in title, abstract, contribution statements, figure captions, and conclusion: `E4`, `E5`, campaign names, internal run IDs, absolute paths, and GREEN tier labels.
