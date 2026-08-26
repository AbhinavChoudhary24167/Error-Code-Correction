# Gate 04 analysis provenance

The experiment policy, run matrix, physical commands, and power extraction precision were frozen before execution. The frozen analyzer assumed every run would reach final reports. After the preserved Hsiao synthesis-policy failure, generic handling for a missing final report was added so the run is represented as `PHYSICAL_CHARACTERIZATION_PARTIAL` with null PPA values instead of aborting adjudication. Successful-run extraction, normalization formulas, timing rules, power parsing, and gate thresholds were not changed.

Copied analyzer SHA-256: `c76b4b47475345f7130deb7a1a6fd8fc7efc553ecf2e60cd05a843d2827efd06`.
