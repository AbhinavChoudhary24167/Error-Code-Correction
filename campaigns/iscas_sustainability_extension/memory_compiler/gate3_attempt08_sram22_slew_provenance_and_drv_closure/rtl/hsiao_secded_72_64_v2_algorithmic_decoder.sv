// Revision-2 algorithmic decoder for the qualified hsiao-secded-72-64-v1
// code identity. The ordered syndrome constants are the columns of the
// frozen parity-check matrix. Each comparison directly drives one correction
// bit; no syndrome-to-mask ROM or technology-specific primitive is used.
module hsiao_secded_72_64_v2_algorithmic_decoder(
  input  logic [71:0] word,
  output logic [63:0] data_out,
  output logic correction_applied,
  output logic detected_uncorrectable
);
  logic [7:0] syndrome;
  logic [71:0] column_match;
  logic [71:0] corrected_word;
  logic correction_known;

  hsiao_secded_72_64_v1_syndrome u_syndrome(
    .word(word),
    .syndrome(syndrome)
  );

  // H columns 0..63: payload coordinates. Columns 64..71 are I_8.
  assign column_match[0]  = (syndrome == 8'h07);
  assign column_match[1]  = (syndrome == 8'h0b);
  assign column_match[2]  = (syndrome == 8'h0d);
  assign column_match[3]  = (syndrome == 8'h0e);
  assign column_match[4]  = (syndrome == 8'h13);
  assign column_match[5]  = (syndrome == 8'h15);
  assign column_match[6]  = (syndrome == 8'h16);
  assign column_match[7]  = (syndrome == 8'h19);
  assign column_match[8]  = (syndrome == 8'h1a);
  assign column_match[9]  = (syndrome == 8'h1c);
  assign column_match[10] = (syndrome == 8'h23);
  assign column_match[11] = (syndrome == 8'h25);
  assign column_match[12] = (syndrome == 8'h26);
  assign column_match[13] = (syndrome == 8'h29);
  assign column_match[14] = (syndrome == 8'h2a);
  assign column_match[15] = (syndrome == 8'h2c);
  assign column_match[16] = (syndrome == 8'h31);
  assign column_match[17] = (syndrome == 8'h32);
  assign column_match[18] = (syndrome == 8'h34);
  assign column_match[19] = (syndrome == 8'h38);
  assign column_match[20] = (syndrome == 8'h43);
  assign column_match[21] = (syndrome == 8'h45);
  assign column_match[22] = (syndrome == 8'h46);
  assign column_match[23] = (syndrome == 8'h49);
  assign column_match[24] = (syndrome == 8'h4a);
  assign column_match[25] = (syndrome == 8'h4c);
  assign column_match[26] = (syndrome == 8'h51);
  assign column_match[27] = (syndrome == 8'h52);
  assign column_match[28] = (syndrome == 8'h54);
  assign column_match[29] = (syndrome == 8'h58);
  assign column_match[30] = (syndrome == 8'h61);
  assign column_match[31] = (syndrome == 8'h62);
  assign column_match[32] = (syndrome == 8'h64);
  assign column_match[33] = (syndrome == 8'h68);
  assign column_match[34] = (syndrome == 8'h70);
  assign column_match[35] = (syndrome == 8'h83);
  assign column_match[36] = (syndrome == 8'h85);
  assign column_match[37] = (syndrome == 8'h86);
  assign column_match[38] = (syndrome == 8'h89);
  assign column_match[39] = (syndrome == 8'h8a);
  assign column_match[40] = (syndrome == 8'h8c);
  assign column_match[41] = (syndrome == 8'h91);
  assign column_match[42] = (syndrome == 8'h92);
  assign column_match[43] = (syndrome == 8'h94);
  assign column_match[44] = (syndrome == 8'h98);
  assign column_match[45] = (syndrome == 8'ha1);
  assign column_match[46] = (syndrome == 8'ha2);
  assign column_match[47] = (syndrome == 8'ha4);
  assign column_match[48] = (syndrome == 8'ha8);
  assign column_match[49] = (syndrome == 8'hb0);
  assign column_match[50] = (syndrome == 8'hc1);
  assign column_match[51] = (syndrome == 8'hc2);
  assign column_match[52] = (syndrome == 8'hc4);
  assign column_match[53] = (syndrome == 8'hc8);
  assign column_match[54] = (syndrome == 8'hd0);
  assign column_match[55] = (syndrome == 8'he0);
  assign column_match[56] = (syndrome == 8'h1f);
  assign column_match[57] = (syndrome == 8'h2f);
  assign column_match[58] = (syndrome == 8'h37);
  assign column_match[59] = (syndrome == 8'h3b);
  assign column_match[60] = (syndrome == 8'h3d);
  assign column_match[61] = (syndrome == 8'h3e);
  assign column_match[62] = (syndrome == 8'h4f);
  assign column_match[63] = (syndrome == 8'h57);
  assign column_match[64] = (syndrome == 8'h01);
  assign column_match[65] = (syndrome == 8'h02);
  assign column_match[66] = (syndrome == 8'h04);
  assign column_match[67] = (syndrome == 8'h08);
  assign column_match[68] = (syndrome == 8'h10);
  assign column_match[69] = (syndrome == 8'h20);
  assign column_match[70] = (syndrome == 8'h40);
  assign column_match[71] = (syndrome == 8'h80);

  assign correction_known = |column_match;
  assign correction_applied = (syndrome != 8'h00) && correction_known;
  assign detected_uncorrectable = (syndrome != 8'h00) && !correction_known;
  assign corrected_word = word ^ column_match;
  assign data_out = corrected_word[63:0];
endmodule
