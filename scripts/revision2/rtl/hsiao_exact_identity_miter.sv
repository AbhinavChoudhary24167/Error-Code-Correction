module rev2_hsiao_exact_identity_miter(
  input logic [71:0] word,
  output logic mismatch
);
  logic [63:0] historical_data;
  logic historical_corrected;
  logic historical_uncorrectable;
  logic [63:0] algorithmic_data;
  logic algorithmic_corrected;
  logic algorithmic_uncorrectable;

  hsiao_secded_72_64_v1_decoder historical(
    .word(word),
    .data_out(historical_data),
    .correction_applied(historical_corrected),
    .detected_uncorrectable(historical_uncorrectable)
  );

  hsiao_secded_72_64_v2_algorithmic_decoder algorithmic(
    .word(word),
    .data_out(algorithmic_data),
    .correction_applied(algorithmic_corrected),
    .detected_uncorrectable(algorithmic_uncorrectable)
  );

  assign mismatch =
    (historical_data != algorithmic_data) ||
    (historical_corrected != algorithmic_corrected) ||
    (historical_uncorrectable != algorithmic_uncorrectable);
endmodule
