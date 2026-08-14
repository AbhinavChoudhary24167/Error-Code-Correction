// Gate 03E mapping-only boundaries.  Encoder and decoder channels are
// deliberately independent so synthesis cannot optimize an encode->decode
// feedback-free composition into a trivial payload path.

module gate03e_secded_combinational_boundary (
  input  logic [63:0] enc_data_i,
  output logic [71:0] enc_codeword_o,
  input  logic [71:0] dec_codeword_i,
  output logic [63:0] dec_data_o,
  output logic [71:0] dec_corrected_codeword_o,
  output logic        dec_detected_o,
  output logic        dec_corrected_o,
  output logic        dec_uncorrectable_o
);
  logic [6:0] enc_parity_dbg;
  logic [6:0] dec_syndrome;
  logic dec_overall_mismatch;
  logic [71:0] dec_correction_mask;
  logic [6:0] dec_error_pos;

  secded_encoder #(.DATA_W(64)) u_encoder (
    .data_i(enc_data_i),
    .codeword_o(enc_codeword_o),
    .parity_dbg_o(enc_parity_dbg)
  );
  secded_decoder #(.DATA_W(64)) u_decoder (
    .codeword_i(dec_codeword_i),
    .data_o(dec_data_o),
    .corrected_codeword_o(dec_corrected_codeword_o),
    .syndrome_o(dec_syndrome),
    .overall_mismatch_o(dec_overall_mismatch),
    .err_detected_o(dec_detected_o),
    .err_corrected_o(dec_corrected_o),
    .err_uncorrectable_o(dec_uncorrectable_o),
    .correction_mask_o(dec_correction_mask),
    .error_pos_o(dec_error_pos)
  );
endmodule

module gate03e_secded_pipelined_boundary (
  input  logic        clk_i,
  input  logic        enc_valid_i,
  input  logic [63:0] enc_data_i,
  output logic        enc_valid_o,
  output logic [71:0] enc_codeword_o,
  input  logic        dec_valid_i,
  input  logic [71:0] dec_codeword_i,
  output logic        dec_valid_o,
  output logic [63:0] dec_data_o,
  output logic [71:0] dec_corrected_codeword_o,
  output logic        dec_detected_o,
  output logic        dec_corrected_o,
  output logic        dec_uncorrectable_o
);
  secded_pipelined_72_64_v1_encoder u_encoder (
    .clk_i(clk_i),
    .valid_i(enc_valid_i),
    .data_i(enc_data_i),
    .valid_o(enc_valid_o),
    .codeword_o(enc_codeword_o)
  );
  secded_pipelined_72_64_v1_decoder u_decoder (
    .clk_i(clk_i),
    .valid_i(dec_valid_i),
    .codeword_i(dec_codeword_i),
    .valid_o(dec_valid_o),
    .data_o(dec_data_o),
    .corrected_codeword_o(dec_corrected_codeword_o),
    .err_detected_o(dec_detected_o),
    .err_corrected_o(dec_corrected_o),
    .err_uncorrectable_o(dec_uncorrectable_o)
  );
endmodule
