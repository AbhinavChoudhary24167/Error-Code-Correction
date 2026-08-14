# Gate-03 tooling boundary

This subtree is additive audit tooling. The `rtl/` files are clean PPA shells and
must never contain fault injection. The only injection XORs are in
`verification/`, whose tops are excluded from every synthesis and ORFS file list.

The ORFS template is unusable until both an immutable image digest and its matching
source commit/configuration have been recorded. A mutable checkout must never be
combined with a separately pinned image.
