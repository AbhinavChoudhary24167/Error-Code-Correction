# Gate 04 infrastructure incident and replacement decision

The first prospective namespace, `/var/lib/green-ecc-date2027-gate04-final`, is excluded in full from scientific interpretation.

After the conventional SECDED physical and power commands completed, the frozen runner raised a Python `NameError` while writing metadata because it used `false` instead of `False`. The matrix then began the pipelined SECDED flow. It was deliberately interrupted as soon as the deterministic defect was observed.

Both affected attempts are preserved, content-inventoried, SHA-256 protected, and sealed read-only. No physical metric or power value from that namespace is used in the Gate 04 dataset.

Decision: `CLEAN_REPLACEMENT_NAMESPACE_JUSTIFIED`.

Exactly one replacement is authorized for each affected implementation because:

- the defect is confined to post-run Python metadata serialization;
- the Docker image, ORFS/OpenROAD revisions, SKY130HD files, corner, RTL, boundary, SDC, VCDs, seeds, placement settings, and worker count do not change;
- the entire failed namespace is excluded rather than selectively reusing or cherry-picking results;
- the other two implementations had not begun.

The replacement namespace is `/var/lib/green-ecc-date2027-gate04-final-confirmatory-02`. Its experiment manifest records the superseded namespace and the two replacement mappings before execution.
