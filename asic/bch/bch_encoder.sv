// BCH(63,51) fixed encoder wrapper.
module bch_63_encoder #(
  parameter int DATA_W = 51,
  parameter int ECC_W  = 12,
  parameter int CODE_W = DATA_W + ECC_W
) (
  input  logic [DATA_W-1:0] data_i,
  output logic [CODE_W-1:0] codeword_o
);
  bch_encoder #(.N(CODE_W), .K(DATA_W)) u_enc (
    .data_i(data_i),
    .codeword_o(codeword_o)
  );
endmodule
