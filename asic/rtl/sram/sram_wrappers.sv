//------------------------------------------------------------------------------
// File: sram_wrappers.sv
// Purpose: Thin SRAM-facing wrappers for ECC schemes at word widths 8/16/32.
// Scheme: SRAM wrappers over SECDED/TAEC/BCH/Polar
// Assumptions: Write path encodes payload; read path decodes full stored word.
// Synthesizability: Yes.
//------------------------------------------------------------------------------

module sram_secded_wrapper #(
  parameter int DATA_W = 8
) (
  input  logic [DATA_W-1:0] wr_data_i,
  output logic [DATA_W+ecc_pkg::hamming_parity_bits(DATA_W):0] mem_word_o,
  input  logic [DATA_W+ecc_pkg::hamming_parity_bits(DATA_W):0] rd_word_i,
  output logic [DATA_W-1:0] rd_data_o,
  output logic err_detected_o,
  output logic err_corrected_o,
  output logic err_uncorrectable_o
);
  logic [ecc_pkg::hamming_parity_bits(DATA_W)-1:0] p;
  logic [DATA_W+ecc_pkg::hamming_parity_bits(DATA_W):0] cw_corr;
  logic [ecc_pkg::hamming_parity_bits(DATA_W)-1:0] s;
  logic om;
  logic [DATA_W+ecc_pkg::hamming_parity_bits(DATA_W):0] mask;
  logic [$clog2(DATA_W+ecc_pkg::hamming_parity_bits(DATA_W)+2)-1:0] ep;
  secded_encoder #(.DATA_W(DATA_W)) u_we(.data_i(wr_data_i), .codeword_o(mem_word_o), .parity_dbg_o(p));
  secded_decoder #(.DATA_W(DATA_W)) u_re(
    .codeword_i(rd_word_i), .data_o(rd_data_o), .corrected_codeword_o(cw_corr),
    .syndrome_o(s), .overall_mismatch_o(om), .err_detected_o(err_detected_o),
    .err_corrected_o(err_corrected_o), .err_uncorrectable_o(err_uncorrectable_o),
    .correction_mask_o(mask), .error_pos_o(ep));
endmodule

module sram_taec_wrapper #(
  parameter int DATA_W = 8
) (
  input  logic [DATA_W-1:0] wr_data_i,
  output logic [DATA_W+ecc_pkg::hamming_parity_bits(DATA_W):0] mem_word_o,
  input  logic [DATA_W+ecc_pkg::hamming_parity_bits(DATA_W):0] rd_word_i,
  output logic [DATA_W-1:0] rd_data_o,
  output logic err_detected_o,
  output logic err_corrected_o,
  output logic err_uncorrectable_o
);
  logic [DATA_W+ecc_pkg::hamming_parity_bits(DATA_W):0] cw_corr;
  logic [ecc_pkg::hamming_parity_bits(DATA_W)-1:0] syn;
  logic tri;
  taec_encoder #(.DATA_W(DATA_W)) u_we(.data_i(wr_data_i), .codeword_o(mem_word_o));
  taec_decoder #(.DATA_W(DATA_W)) u_re(.codeword_i(rd_word_i), .data_o(rd_data_o), .corrected_codeword_o(cw_corr),
    .syndrome_o(syn), .err_detected_o(err_detected_o), .err_corrected_o(err_corrected_o),
    .err_uncorrectable_o(err_uncorrectable_o), .triple_adjacent_corrected_o(tri));
endmodule

module sram_bch_wrapper #(
  parameter int DATA_W = 8,
  parameter int N = DATA_W + 6
) (
  input  logic [DATA_W-1:0] wr_data_i,
  output logic [N-1:0]      mem_word_o,
  input  logic [N-1:0]      rd_word_i,
  output logic [DATA_W-1:0] rd_data_o,
  output logic err_detected_o,
  output logic err_corrected_o,
  output logic err_uncorrectable_o
);
  logic [N-1:0] cw_corr;
  logic [N-DATA_W-1:0] syn;
  bch_encoder #(.N(N), .K(DATA_W)) u_we(.data_i(wr_data_i), .codeword_o(mem_word_o));
  bch_decoder #(.N(N), .K(DATA_W)) u_re(.codeword_i(rd_word_i), .data_o(rd_data_o), .corrected_codeword_o(cw_corr),
    .syndrome_o(syn), .err_detected_o(err_detected_o), .err_corrected_o(err_corrected_o), .err_uncorrectable_o(err_uncorrectable_o));
endmodule

module sram_polar_wrapper #(
  parameter int DATA_W = 8,
  parameter int N = (DATA_W <= 8) ? 16 : ((DATA_W <= 16) ? 32 : 64)
) (
  input  logic [DATA_W-1:0] wr_data_i,
  output logic [N-1:0]      mem_word_o,
  input  logic [N-1:0]      rd_word_i,
  output logic [DATA_W-1:0] rd_data_o,
  output logic err_detected_o,
  output logic err_corrected_o,
  output logic err_uncorrectable_o
);
  logic [N-1:0] udbg, uh;
  logic [N-1:0] cw_corr;
  polar_encoder #(.N(N), .K(DATA_W)) u_we(.data_i(wr_data_i), .codeword_o(mem_word_o), .u_dbg_o(udbg));
  polar_decoder #(.N(N), .K(DATA_W)) u_re(.codeword_i(rd_word_i), .data_o(rd_data_o), .corrected_codeword_o(cw_corr),
    .u_hat_o(uh), .err_detected_o(err_detected_o), .err_corrected_o(err_corrected_o), .err_uncorrectable_o(err_uncorrectable_o));
endmodule

// Concrete entry-point module names for code_db SRAM entries.
module sram_secded_8  (input logic [7:0]  wr_data_i, output logic [12:0] mem_word_o, input logic [12:0] rd_word_i, output logic [7:0]  rd_data_o, output logic err_detected_o, err_corrected_o, err_uncorrectable_o);  sram_secded_wrapper #(.DATA_W(8))  u (.*); endmodule
module sram_secded_16 (input logic [15:0] wr_data_i, output logic [21:0] mem_word_o, input logic [21:0] rd_word_i, output logic [15:0] rd_data_o, output logic err_detected_o, err_corrected_o, err_uncorrectable_o); sram_secded_wrapper #(.DATA_W(16)) u (.*); endmodule
module sram_secded_32 (input logic [31:0] wr_data_i, output logic [38:0] mem_word_o, input logic [38:0] rd_word_i, output logic [31:0] rd_data_o, output logic err_detected_o, err_corrected_o, err_uncorrectable_o); sram_secded_wrapper #(.DATA_W(32)) u (.*); endmodule
module sram_taec_8    (input logic [7:0]  wr_data_i, output logic [12:0] mem_word_o, input logic [12:0] rd_word_i, output logic [7:0]  rd_data_o, output logic err_detected_o, err_corrected_o, err_uncorrectable_o);  sram_taec_wrapper #(.DATA_W(8))    u (.*); endmodule
module sram_taec_16   (input logic [15:0] wr_data_i, output logic [21:0] mem_word_o, input logic [21:0] rd_word_i, output logic [15:0] rd_data_o, output logic err_detected_o, err_corrected_o, err_uncorrectable_o); sram_taec_wrapper #(.DATA_W(16))   u (.*); endmodule
module sram_taec_32   (input logic [31:0] wr_data_i, output logic [38:0] mem_word_o, input logic [38:0] rd_word_i, output logic [31:0] rd_data_o, output logic err_detected_o, err_corrected_o, err_uncorrectable_o); sram_taec_wrapper #(.DATA_W(32))   u (.*); endmodule
module sram_bch_8     (input logic [7:0]  wr_data_i, output logic [13:0] mem_word_o, input logic [13:0] rd_word_i, output logic [7:0]  rd_data_o, output logic err_detected_o, err_corrected_o, err_uncorrectable_o);  sram_bch_wrapper #(.DATA_W(8), .N(14))  u (.*); endmodule
module sram_bch_16    (input logic [15:0] wr_data_i, output logic [23:0] mem_word_o, input logic [23:0] rd_word_i, output logic [15:0] rd_data_o, output logic err_detected_o, err_corrected_o, err_uncorrectable_o); sram_bch_wrapper #(.DATA_W(16), .N(24)) u (.*); endmodule
module sram_bch_32    (input logic [31:0] wr_data_i, output logic [44:0] mem_word_o, input logic [44:0] rd_word_i, output logic [31:0] rd_data_o, output logic err_detected_o, err_corrected_o, err_uncorrectable_o); sram_bch_wrapper #(.DATA_W(32), .N(45)) u (.*); endmodule
module sram_polar_8   (input logic [7:0]  wr_data_i, output logic [15:0] mem_word_o, input logic [15:0] rd_word_i, output logic [7:0]  rd_data_o, output logic err_detected_o, err_corrected_o, err_uncorrectable_o);  sram_polar_wrapper #(.DATA_W(8), .N(16))  u (.*); endmodule
module sram_polar_16  (input logic [15:0] wr_data_i, output logic [31:0] mem_word_o, input logic [31:0] rd_word_i, output logic [15:0] rd_data_o, output logic err_detected_o, err_corrected_o, err_uncorrectable_o); sram_polar_wrapper #(.DATA_W(16), .N(32)) u (.*); endmodule
module sram_polar_32  (input logic [31:0] wr_data_i, output logic [63:0] mem_word_o, input logic [63:0] rd_word_i, output logic [31:0] rd_data_o, output logic err_detected_o, err_corrected_o, err_uncorrectable_o); sram_polar_wrapper #(.DATA_W(32), .N(64)) u (.*); endmodule
