// Generated syndrome network; no technology-specific PPA claim.
module forge_hotspot_8_4_v1_safe_syndrome(
  input  logic [7:0] word,
  output logic [3:0] syndrome
);
  assign syndrome[0] = word[0] ^ word[2] ^ word[3] ^ word[4];
  assign syndrome[1] = word[0] ^ word[1] ^ word[2] ^ word[5];
  assign syndrome[2] = word[1] ^ word[2] ^ word[3] ^ word[6];
  assign syndrome[3] = word[0] ^ word[1] ^ word[3] ^ word[7];
endmodule
