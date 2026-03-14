// TAEC 64b fixed encoder wrapper.
module taec_64_encoder #(
  parameter int DATA_W = 64,
  parameter int ECC_W  = ecc_pkg::hamming_parity_bits(DATA_W) + 1,
  parameter int CODE_W = DATA_W + ECC_W
) (
  input  logic [DATA_W-1:0] data_i,
  output logic [CODE_W-1:0] codeword_o
);
  taec_encoder #(.DATA_W(DATA_W)) u_enc (
    .data_i(data_i),
    .codeword_o(codeword_o)
  );
endmodule
