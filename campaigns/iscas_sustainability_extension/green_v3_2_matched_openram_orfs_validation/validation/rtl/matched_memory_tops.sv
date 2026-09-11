// Experiment-only SRAM wrappers. Production codec RTL and inherited SRAM22
// views are instantiated without alteration.

module u0_matched_sram_top (
  input logic clk, rstb, ce, we,
  input logic [7:0] addr,
  input logic [63:0] payload_in,
  output logic [63:0] payload_out,
  output logic correction_applied,
  output logic detected_uncorrectable
);
  sram22_256x64m4w8 u_data (
    .clk(clk), .rstb(rstb), .ce(ce), .we(we), .wmask(8'hff),
    .addr(addr), .din(payload_in), .dout(payload_out)
  );
  assign correction_applied = 1'b0;
  assign detected_uncorrectable = 1'b0;
endmodule
module secded_matched_sram_top (
  input logic clk, rstb, ce, we,
  input logic [7:0] addr,
  input logic [63:0] payload_in,
  output logic [63:0] payload_out,
  output logic correction_applied,
  output logic detected_uncorrectable
);
  logic [71:0] encoded_word, stored_word, corrected_word;
  logic [63:0] data_dout;
  logic [7:0] ecc_dout;
  logic detected_unused;
  gate03r_secded_baseline_encoder u_encoder(.data_i(payload_in), .codeword_o(encoded_word));
  sram22_256x64m4w8 u_data(
    .clk(clk), .rstb(rstb), .ce(ce), .we(we), .wmask(8'hff),
    .addr(addr), .din(encoded_word[63:0]), .dout(data_dout));
  sram22_256x8m8w1 u_ecc0(
    .clk(clk), .rstb(rstb), .ce(ce), .we(we), .wmask(8'hff),
    .addr(addr), .din(encoded_word[71:64]), .dout(ecc_dout));
  assign stored_word = {ecc_dout, data_dout};
  gate03r_secded_baseline_decoder u_decoder(
    .codeword_i(stored_word), .data_o(payload_out),
    .corrected_codeword_o(corrected_word), .err_detected_o(detected_unused),
    .err_corrected_o(correction_applied), .err_uncorrectable_o(detected_uncorrectable));
endmodule

module hsiao_matched_sram_top (
  input logic clk, rstb, ce, we,
  input logic [7:0] addr,
  input logic [63:0] payload_in,
  output logic [63:0] payload_out,
  output logic correction_applied,
  output logic detected_uncorrectable
);
  logic [71:0] encoded_word, stored_word;
  logic [63:0] data_dout;
  logic [7:0] ecc_dout;
  hsiao_secded_72_64_v1_encoder u_encoder(.data(payload_in), .codeword(encoded_word));
  sram22_256x64m4w8 u_data(
    .clk(clk), .rstb(rstb), .ce(ce), .we(we), .wmask(8'hff),
    .addr(addr), .din(encoded_word[63:0]), .dout(data_dout));
  sram22_256x8m8w1 u_ecc0(
    .clk(clk), .rstb(rstb), .ce(ce), .we(we), .wmask(8'hff),
    .addr(addr), .din(encoded_word[71:64]), .dout(ecc_dout));
  assign stored_word = {ecc_dout, data_dout};
  hsiao_secded_72_64_v1_decoder u_decoder(
    .word(stored_word), .data_out(payload_out),
    .correction_applied(correction_applied),
    .detected_uncorrectable(detected_uncorrectable));
endmodule

module secdaec_matched_sram_top (
  input logic clk, rstb, ce, we,
  input logic [7:0] addr,
  input logic [63:0] payload_in,
  output logic [63:0] payload_out,
  output logic correction_applied,
  output logic detected_uncorrectable
);
  logic [71:0] encoded_word, stored_word, corrected_word;
  logic [63:0] data_dout;
  logic [7:0] ecc_dout;
  logic [6:0] syndrome_unused;
  logic detected_unused, adjacent_unused;
  secdaec_encoder #(.DATA_W(64)) u_encoder(.data_i(payload_in), .codeword_o(encoded_word));
  sram22_256x64m4w8 u_data(
    .clk(clk), .rstb(rstb), .ce(ce), .we(we), .wmask(8'hff),
    .addr(addr), .din(encoded_word[63:0]), .dout(data_dout));
  sram22_256x8m8w1 u_ecc0(
    .clk(clk), .rstb(rstb), .ce(ce), .we(we), .wmask(8'hff),
    .addr(addr), .din(encoded_word[71:64]), .dout(ecc_dout));
  assign stored_word = {ecc_dout, data_dout};
  secdaec_decoder #(.DATA_W(64)) u_decoder(
    .codeword_i(stored_word), .data_o(payload_out),
    .corrected_codeword_o(corrected_word), .syndrome_o(syndrome_unused),
    .err_detected_o(detected_unused), .err_corrected_o(correction_applied),
    .err_uncorrectable_o(detected_uncorrectable),
    .adjacent_double_corrected_o(adjacent_unused));
endmodule

module bch_t2_matched_sram_top (
  input logic clk, rstb, ce, we,
  input logic [7:0] addr,
  input logic [63:0] payload_in,
  output logic [63:0] payload_out,
  output logic correction_applied,
  output logic detected_uncorrectable
);
  logic [77:0] encoded_word, stored_word, corrected_word, correction_mask_unused;
  logic [63:0] data_dout;
  logic [7:0] ecc0_dout, ecc1_dout;
  logic [27:0] syndrome_unused;
  logic detected_unused;
  bch_78_64_t2_v1_encoder u_encoder(.data_i(payload_in), .codeword_o(encoded_word));
  sram22_256x64m4w8 u_data(
    .clk(clk), .rstb(rstb), .ce(ce), .we(we), .wmask(8'hff),
    .addr(addr), .din(encoded_word[63:0]), .dout(data_dout));
  sram22_256x8m8w1 u_ecc0(
    .clk(clk), .rstb(rstb), .ce(ce), .we(we), .wmask(8'hff),
    .addr(addr), .din(encoded_word[71:64]), .dout(ecc0_dout));
  sram22_256x8m8w1 u_ecc1(
    .clk(clk), .rstb(rstb), .ce(ce), .we(we), .wmask(8'hff),
    .addr(addr), .din({2'b00, encoded_word[77:72]}), .dout(ecc1_dout));
  assign stored_word = {ecc1_dout[5:0], ecc0_dout, data_dout};
  bch_78_64_t2_v1_decoder u_decoder(
    .codeword_i(stored_word), .data_o(payload_out),
    .corrected_codeword_o(corrected_word), .syndrome_o(syndrome_unused),
    .correction_mask_o(correction_mask_unused), .err_detected_o(detected_unused),
    .err_corrected_o(correction_applied), .err_uncorrectable_o(detected_uncorrectable));
endmodule
