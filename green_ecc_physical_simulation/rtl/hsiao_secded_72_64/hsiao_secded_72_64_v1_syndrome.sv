// Generated syndrome network; no technology-specific PPA claim.
module hsiao_secded_72_64_v1_syndrome(
  input  logic [71:0] word,
  output logic [7:0] syndrome
);
  assign syndrome[0] = word[0] ^ word[1] ^ word[2] ^ word[4] ^ word[5] ^ word[7] ^ word[10] ^ word[11] ^ word[13] ^ word[16] ^ word[20] ^ word[21] ^ word[23] ^ word[26] ^ word[30] ^ word[35] ^ word[36] ^ word[38] ^ word[41] ^ word[45] ^ word[50] ^ word[56] ^ word[57] ^ word[58] ^ word[59] ^ word[60] ^ word[62] ^ word[63] ^ word[64];
  assign syndrome[1] = word[0] ^ word[1] ^ word[3] ^ word[4] ^ word[6] ^ word[8] ^ word[10] ^ word[12] ^ word[14] ^ word[17] ^ word[20] ^ word[22] ^ word[24] ^ word[27] ^ word[31] ^ word[35] ^ word[37] ^ word[39] ^ word[42] ^ word[46] ^ word[51] ^ word[56] ^ word[57] ^ word[58] ^ word[59] ^ word[61] ^ word[62] ^ word[63] ^ word[65];
  assign syndrome[2] = word[0] ^ word[2] ^ word[3] ^ word[5] ^ word[6] ^ word[9] ^ word[11] ^ word[12] ^ word[15] ^ word[18] ^ word[21] ^ word[22] ^ word[25] ^ word[28] ^ word[32] ^ word[36] ^ word[37] ^ word[40] ^ word[43] ^ word[47] ^ word[52] ^ word[56] ^ word[57] ^ word[58] ^ word[60] ^ word[61] ^ word[62] ^ word[63] ^ word[66];
  assign syndrome[3] = word[1] ^ word[2] ^ word[3] ^ word[7] ^ word[8] ^ word[9] ^ word[13] ^ word[14] ^ word[15] ^ word[19] ^ word[23] ^ word[24] ^ word[25] ^ word[29] ^ word[33] ^ word[38] ^ word[39] ^ word[40] ^ word[44] ^ word[48] ^ word[53] ^ word[56] ^ word[57] ^ word[59] ^ word[60] ^ word[61] ^ word[62] ^ word[67];
  assign syndrome[4] = word[4] ^ word[5] ^ word[6] ^ word[7] ^ word[8] ^ word[9] ^ word[16] ^ word[17] ^ word[18] ^ word[19] ^ word[26] ^ word[27] ^ word[28] ^ word[29] ^ word[34] ^ word[41] ^ word[42] ^ word[43] ^ word[44] ^ word[49] ^ word[54] ^ word[56] ^ word[58] ^ word[59] ^ word[60] ^ word[61] ^ word[63] ^ word[68];
  assign syndrome[5] = word[10] ^ word[11] ^ word[12] ^ word[13] ^ word[14] ^ word[15] ^ word[16] ^ word[17] ^ word[18] ^ word[19] ^ word[30] ^ word[31] ^ word[32] ^ word[33] ^ word[34] ^ word[45] ^ word[46] ^ word[47] ^ word[48] ^ word[49] ^ word[55] ^ word[57] ^ word[58] ^ word[59] ^ word[60] ^ word[61] ^ word[69];
  assign syndrome[6] = word[20] ^ word[21] ^ word[22] ^ word[23] ^ word[24] ^ word[25] ^ word[26] ^ word[27] ^ word[28] ^ word[29] ^ word[30] ^ word[31] ^ word[32] ^ word[33] ^ word[34] ^ word[50] ^ word[51] ^ word[52] ^ word[53] ^ word[54] ^ word[55] ^ word[62] ^ word[63] ^ word[70];
  assign syndrome[7] = word[35] ^ word[36] ^ word[37] ^ word[38] ^ word[39] ^ word[40] ^ word[41] ^ word[42] ^ word[43] ^ word[44] ^ word[45] ^ word[46] ^ word[47] ^ word[48] ^ word[49] ^ word[50] ^ word[51] ^ word[52] ^ word[53] ^ word[54] ^ word[55] ^ word[71];
endmodule
