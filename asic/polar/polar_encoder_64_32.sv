// Polar (64,32) fixed encoder wrapper.
module polar_encoder_64_32 #(
  parameter int DATA_W = 32,
  parameter int CODE_W = 64,
  parameter int ECC_W  = CODE_W - DATA_W
) (
  input  logic [DATA_W-1:0] data_i,
  output logic [CODE_W-1:0] codeword_o
);
  logic [CODE_W-1:0] u_dbg;
  polar_encoder #(.N(CODE_W), .K(DATA_W)) u_enc (
    .data_i(data_i), .codeword_o(codeword_o), .u_dbg_o(u_dbg)
  );
endmodule
