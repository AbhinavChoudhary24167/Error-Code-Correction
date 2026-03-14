// SEC-DED 64b fixed decoder wrapper.
module secded_64_decoder #(
  parameter int DATA_W = 64,
  parameter int ECC_W  = ecc_pkg::hamming_parity_bits(DATA_W) + 1,
  parameter int CODE_W = DATA_W + ECC_W
) (
  input  logic [CODE_W-1:0] codeword_i,
  output logic [DATA_W-1:0] data_o,
  output logic [CODE_W-1:0] corrected_codeword_o,
  output logic              err_detected_o,
  output logic              err_corrected_o,
  output logic              err_uncorrectable_o,
  output logic              double_error_o
);
  logic [ecc_pkg::hamming_parity_bits(DATA_W)-1:0] syndrome;
  logic overall_mismatch;
  logic [CODE_W-1:0] correction_mask;
  logic [$clog2(CODE_W+1)-1:0] error_pos;

  secded_decoder #(.DATA_W(DATA_W)) u_dec (
    .codeword_i(codeword_i),
    .data_o(data_o),
    .corrected_codeword_o(corrected_codeword_o),
    .syndrome_o(syndrome),
    .overall_mismatch_o(overall_mismatch),
    .err_detected_o(err_detected_o),
    .err_corrected_o(err_corrected_o),
    .err_uncorrectable_o(err_uncorrectable_o),
    .correction_mask_o(correction_mask),
    .error_pos_o(error_pos)
  );

  assign double_error_o = err_uncorrectable_o;
endmodule
