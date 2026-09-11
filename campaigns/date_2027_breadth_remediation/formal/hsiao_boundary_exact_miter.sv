module breadth_hsiao_boundary_exact_miter(
  input logic clk_i,
  input logic rst_ni,
  input logic valid_i,
  input logic [63:0] enc_data_i,
  input logic [71:0] dec_codeword_i,
  output logic mismatch
);
  logic baseline_enc_valid;
  logic [71:0] baseline_enc_codeword;
  logic baseline_dec_valid;
  logic [63:0] baseline_dec_data;
  logic [71:0] baseline_dec_echo;
  logic baseline_detected;
  logic baseline_corrected;
  logic baseline_uncorrectable;
  logic hierarchical_enc_valid;
  logic [71:0] hierarchical_enc_codeword;
  logic hierarchical_dec_valid;
  logic [63:0] hierarchical_dec_data;
  logic [71:0] hierarchical_dec_echo;
  logic hierarchical_detected;
  logic hierarchical_corrected;
  logic hierarchical_uncorrectable;

  gate04_rev2_hsiao_72_64 baseline(
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .valid_i(valid_i),
    .enc_data_i(enc_data_i),
    .dec_codeword_i(dec_codeword_i),
    .enc_valid_o(baseline_enc_valid),
    .enc_codeword_o(baseline_enc_codeword),
    .dec_valid_o(baseline_dec_valid),
    .dec_data_o(baseline_dec_data),
    .dec_codeword_echo_o(baseline_dec_echo),
    .dec_detected_o(baseline_detected),
    .dec_corrected_o(baseline_corrected),
    .dec_uncorrectable_o(baseline_uncorrectable)
  );

  breadth_hsiao_hierarchical_72_64 hierarchical(
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .valid_i(valid_i),
    .enc_data_i(enc_data_i),
    .dec_codeword_i(dec_codeword_i),
    .enc_valid_o(hierarchical_enc_valid),
    .enc_codeword_o(hierarchical_enc_codeword),
    .dec_valid_o(hierarchical_dec_valid),
    .dec_data_o(hierarchical_dec_data),
    .dec_codeword_echo_o(hierarchical_dec_echo),
    .dec_detected_o(hierarchical_detected),
    .dec_corrected_o(hierarchical_corrected),
    .dec_uncorrectable_o(hierarchical_uncorrectable)
  );

  assign mismatch =
    (baseline_enc_valid != hierarchical_enc_valid) ||
    (baseline_enc_codeword != hierarchical_enc_codeword) ||
    (baseline_dec_valid != hierarchical_dec_valid) ||
    (baseline_dec_data != hierarchical_dec_data) ||
    (baseline_dec_echo != hierarchical_dec_echo) ||
    (baseline_detected != hierarchical_detected) ||
    (baseline_corrected != hierarchical_corrected) ||
    (baseline_uncorrectable != hierarchical_uncorrectable);
endmodule
