// Additive DATE 2027 breadth-remediation decoder identity.
//
// The qualified hsiao-secded-72-64-v1 syndrome and correction semantics are
// unchanged. Unlike the Revision-2 v2 decoder's 72 flat eight-bit equality
// comparisons, this implementation shares two four-bit one-hot decoders and
// forms each frozen H-column match from one high/low nibble conjunction.
module hsiao_secded_72_64_v3_hierarchical_decoder(
  input  logic [71:0] word,
  output logic [63:0] data_out,
  output logic correction_applied,
  output logic detected_uncorrectable
);
  logic [7:0] syndrome;
  logic [15:0] high_match;
  logic [15:0] low_match;
  logic [71:0] column_match;
  logic [71:0] corrected_word;
  logic correction_known;

  hsiao_secded_72_64_v1_syndrome u_syndrome(
    .word(word),
    .syndrome(syndrome)
  );

  assign high_match[0]  = syndrome[7:4] == 4'h0;
  assign high_match[1]  = syndrome[7:4] == 4'h1;
  assign high_match[2]  = syndrome[7:4] == 4'h2;
  assign high_match[3]  = syndrome[7:4] == 4'h3;
  assign high_match[4]  = syndrome[7:4] == 4'h4;
  assign high_match[5]  = syndrome[7:4] == 4'h5;
  assign high_match[6]  = syndrome[7:4] == 4'h6;
  assign high_match[7]  = syndrome[7:4] == 4'h7;
  assign high_match[8]  = syndrome[7:4] == 4'h8;
  assign high_match[9]  = syndrome[7:4] == 4'h9;
  assign high_match[10] = syndrome[7:4] == 4'ha;
  assign high_match[11] = syndrome[7:4] == 4'hb;
  assign high_match[12] = syndrome[7:4] == 4'hc;
  assign high_match[13] = syndrome[7:4] == 4'hd;
  assign high_match[14] = syndrome[7:4] == 4'he;
  assign high_match[15] = syndrome[7:4] == 4'hf;

  assign low_match[0]  = syndrome[3:0] == 4'h0;
  assign low_match[1]  = syndrome[3:0] == 4'h1;
  assign low_match[2]  = syndrome[3:0] == 4'h2;
  assign low_match[3]  = syndrome[3:0] == 4'h3;
  assign low_match[4]  = syndrome[3:0] == 4'h4;
  assign low_match[5]  = syndrome[3:0] == 4'h5;
  assign low_match[6]  = syndrome[3:0] == 4'h6;
  assign low_match[7]  = syndrome[3:0] == 4'h7;
  assign low_match[8]  = syndrome[3:0] == 4'h8;
  assign low_match[9]  = syndrome[3:0] == 4'h9;
  assign low_match[10] = syndrome[3:0] == 4'ha;
  assign low_match[11] = syndrome[3:0] == 4'hb;
  assign low_match[12] = syndrome[3:0] == 4'hc;
  assign low_match[13] = syndrome[3:0] == 4'hd;
  assign low_match[14] = syndrome[3:0] == 4'he;
  assign low_match[15] = syndrome[3:0] == 4'hf;

  // H columns 0..63 are payload coordinates; 64..71 are the I_8 parity
  // columns. The constants are expressed by their high and low nibbles.
  assign column_match[0]  = high_match[0]  & low_match[7];
  assign column_match[1]  = high_match[0]  & low_match[11];
  assign column_match[2]  = high_match[0]  & low_match[13];
  assign column_match[3]  = high_match[0]  & low_match[14];
  assign column_match[4]  = high_match[1]  & low_match[3];
  assign column_match[5]  = high_match[1]  & low_match[5];
  assign column_match[6]  = high_match[1]  & low_match[6];
  assign column_match[7]  = high_match[1]  & low_match[9];
  assign column_match[8]  = high_match[1]  & low_match[10];
  assign column_match[9]  = high_match[1]  & low_match[12];
  assign column_match[10] = high_match[2]  & low_match[3];
  assign column_match[11] = high_match[2]  & low_match[5];
  assign column_match[12] = high_match[2]  & low_match[6];
  assign column_match[13] = high_match[2]  & low_match[9];
  assign column_match[14] = high_match[2]  & low_match[10];
  assign column_match[15] = high_match[2]  & low_match[12];
  assign column_match[16] = high_match[3]  & low_match[1];
  assign column_match[17] = high_match[3]  & low_match[2];
  assign column_match[18] = high_match[3]  & low_match[4];
  assign column_match[19] = high_match[3]  & low_match[8];
  assign column_match[20] = high_match[4]  & low_match[3];
  assign column_match[21] = high_match[4]  & low_match[5];
  assign column_match[22] = high_match[4]  & low_match[6];
  assign column_match[23] = high_match[4]  & low_match[9];
  assign column_match[24] = high_match[4]  & low_match[10];
  assign column_match[25] = high_match[4]  & low_match[12];
  assign column_match[26] = high_match[5]  & low_match[1];
  assign column_match[27] = high_match[5]  & low_match[2];
  assign column_match[28] = high_match[5]  & low_match[4];
  assign column_match[29] = high_match[5]  & low_match[8];
  assign column_match[30] = high_match[6]  & low_match[1];
  assign column_match[31] = high_match[6]  & low_match[2];
  assign column_match[32] = high_match[6]  & low_match[4];
  assign column_match[33] = high_match[6]  & low_match[8];
  assign column_match[34] = high_match[7]  & low_match[0];
  assign column_match[35] = high_match[8]  & low_match[3];
  assign column_match[36] = high_match[8]  & low_match[5];
  assign column_match[37] = high_match[8]  & low_match[6];
  assign column_match[38] = high_match[8]  & low_match[9];
  assign column_match[39] = high_match[8]  & low_match[10];
  assign column_match[40] = high_match[8]  & low_match[12];
  assign column_match[41] = high_match[9]  & low_match[1];
  assign column_match[42] = high_match[9]  & low_match[2];
  assign column_match[43] = high_match[9]  & low_match[4];
  assign column_match[44] = high_match[9]  & low_match[8];
  assign column_match[45] = high_match[10] & low_match[1];
  assign column_match[46] = high_match[10] & low_match[2];
  assign column_match[47] = high_match[10] & low_match[4];
  assign column_match[48] = high_match[10] & low_match[8];
  assign column_match[49] = high_match[11] & low_match[0];
  assign column_match[50] = high_match[12] & low_match[1];
  assign column_match[51] = high_match[12] & low_match[2];
  assign column_match[52] = high_match[12] & low_match[4];
  assign column_match[53] = high_match[12] & low_match[8];
  assign column_match[54] = high_match[13] & low_match[0];
  assign column_match[55] = high_match[14] & low_match[0];
  assign column_match[56] = high_match[1]  & low_match[15];
  assign column_match[57] = high_match[2]  & low_match[15];
  assign column_match[58] = high_match[3]  & low_match[7];
  assign column_match[59] = high_match[3]  & low_match[11];
  assign column_match[60] = high_match[3]  & low_match[13];
  assign column_match[61] = high_match[3]  & low_match[14];
  assign column_match[62] = high_match[4]  & low_match[15];
  assign column_match[63] = high_match[5]  & low_match[7];
  assign column_match[64] = high_match[0]  & low_match[1];
  assign column_match[65] = high_match[0]  & low_match[2];
  assign column_match[66] = high_match[0]  & low_match[4];
  assign column_match[67] = high_match[0]  & low_match[8];
  assign column_match[68] = high_match[1]  & low_match[0];
  assign column_match[69] = high_match[2]  & low_match[0];
  assign column_match[70] = high_match[4]  & low_match[0];
  assign column_match[71] = high_match[8]  & low_match[0];

  assign correction_known = |column_match;
  assign correction_applied = (syndrome != 8'h00) && correction_known;
  assign detected_uncorrectable = (syndrome != 8'h00) && !correction_known;
  assign corrected_word = word ^ column_match;
  assign data_out = corrected_word[63:0];
endmodule
