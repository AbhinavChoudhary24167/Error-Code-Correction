// BCH(63,51) fixed decoder wrapper.
// NOTE: Underlying decoder is bounded (<=2 bit search) for synthesizability.
module bch_63_decoder #(
  parameter int DATA_W = 51,
  parameter int ECC_W  = 12,
  parameter int CODE_W = DATA_W + ECC_W
) (
  input  logic [CODE_W-1:0] codeword_i,
  output logic [DATA_W-1:0] data_o,
  output logic [CODE_W-1:0] corrected_codeword_o,
  output logic              err_detected_o,
  output logic              err_corrected_o,
  output logic              err_uncorrectable_o
);
  logic [ECC_W-1:0] syndrome;
  bch_decoder #(.N(CODE_W), .K(DATA_W)) u_dec (
    .codeword_i(codeword_i), .data_o(data_o), .corrected_codeword_o(corrected_codeword_o),
    .syndrome_o(syndrome), .err_detected_o(err_detected_o), .err_corrected_o(err_corrected_o),
    .err_uncorrectable_o(err_uncorrectable_o)
  );
endmodule
