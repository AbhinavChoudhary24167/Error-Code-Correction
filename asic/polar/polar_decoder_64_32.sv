// Polar (64,32) fixed decoder wrapper.
// NOTE: Underlying decoder is bounded local search, not full SC/SCL.
module polar_decoder_64_32 #(
  parameter int DATA_W = 32,
  parameter int CODE_W = 64,
  parameter int ECC_W  = CODE_W - DATA_W
) (
  input  logic [CODE_W-1:0] codeword_i,
  output logic [DATA_W-1:0] data_o,
  output logic [CODE_W-1:0] corrected_codeword_o,
  output logic              err_detected_o,
  output logic              err_corrected_o,
  output logic              err_uncorrectable_o
);
  logic [CODE_W-1:0] u_hat;
  polar_decoder #(.N(CODE_W), .K(DATA_W)) u_dec (
    .codeword_i(codeword_i), .data_o(data_o), .corrected_codeword_o(corrected_codeword_o),
    .u_hat_o(u_hat), .err_detected_o(err_detected_o), .err_corrected_o(err_corrected_o),
    .err_uncorrectable_o(err_uncorrectable_o)
  );
endmodule
