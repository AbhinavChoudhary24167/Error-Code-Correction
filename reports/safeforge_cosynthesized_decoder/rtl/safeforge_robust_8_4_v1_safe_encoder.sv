// Generated structural encoder; no technology-specific PPA claim.
module safeforge_robust_8_4_v1_safe_encoder(
  input  logic [3:0] data,
  output logic [7:0] codeword
);
  assign codeword[0] = data[0];
  assign codeword[1] = data[1];
  assign codeword[2] = data[2];
  assign codeword[3] = data[3];
  assign codeword[4] = data[1] ^ data[3];
  assign codeword[5] = data[0] ^ data[3];
  assign codeword[6] = data[1] ^ data[2] ^ data[3];
  assign codeword[7] = data[0] ^ data[2];
endmodule
