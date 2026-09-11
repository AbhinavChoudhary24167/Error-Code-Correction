module breadth_hsiao_structural_exact_miter(
  input logic [71:0] word,
  output logic mismatch
);
  logic [63:0] baseline_data;
  logic baseline_corrected;
  logic baseline_uncorrectable;
  logic [63:0] hierarchical_data;
  logic hierarchical_corrected;
  logic hierarchical_uncorrectable;

  hsiao_secded_72_64_v2_algorithmic_decoder baseline(
    .word(word),
    .data_out(baseline_data),
    .correction_applied(baseline_corrected),
    .detected_uncorrectable(baseline_uncorrectable)
  );

  hsiao_secded_72_64_v3_hierarchical_decoder hierarchical(
    .word(word),
    .data_out(hierarchical_data),
    .correction_applied(hierarchical_corrected),
    .detected_uncorrectable(hierarchical_uncorrectable)
  );

  assign mismatch =
    (baseline_data != hierarchical_data) ||
    (baseline_corrected != hierarchical_corrected) ||
    (baseline_uncorrectable != hierarchical_uncorrectable);
endmodule
