// SEC-DED 64b fixed encoder wrapper.
module secded_64_encoder #(
  parameter int DATA_W = 64,
  parameter int ECC_W  = ecc_pkg::hamming_parity_bits(DATA_W) + 1,
  parameter int CODE_W = DATA_W + ECC_W
) (
  input  logic [DATA_W-1:0] data_i,
  output logic [CODE_W-1:0] codeword_o
);
  logic [ecc_pkg::hamming_parity_bits(DATA_W)-1:0] parity_dbg;
  secded_encoder #(.DATA_W(DATA_W)) u_enc (
    .data_i(data_i),
    .codeword_o(codeword_o),
    .parity_dbg_o(parity_dbg)
  );
endmodule
