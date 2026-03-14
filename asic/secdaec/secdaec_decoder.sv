// SEC-DAEC 64b fixed decoder wrapper.
module secdaec_64_decoder #(
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
  output logic              adjacent_error_o
);
  logic [ecc_pkg::hamming_parity_bits(DATA_W)-1:0] syndrome;

  secdaec_decoder #(.DATA_W(DATA_W)) u_dec (
    .codeword_i(codeword_i), .data_o(data_o), .corrected_codeword_o(corrected_codeword_o),
    .syndrome_o(syndrome), .err_detected_o(err_detected_o), .err_corrected_o(err_corrected_o),
    .err_uncorrectable_o(err_uncorrectable_o), .adjacent_double_corrected_o(adjacent_error_o)
  );
endmodule
