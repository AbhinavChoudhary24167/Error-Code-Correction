//------------------------------------------------------------------------------
// File: ecc_entries.sv
// Purpose: Concrete top-level module names for fixed/global code_db entries.
// Scheme: SECDED / SECDAEC / TAEC / BCH / Polar
// Assumptions: These are thin wiring aliases to family modules.
// Synthesizability: Yes.
//------------------------------------------------------------------------------

module sec_ded_64 (
  input logic [63:0] data_i,
  output logic [71:0] codeword_o,
  input logic [71:0] codeword_in_i,
  output logic [63:0] data_o,
  output logic err_detected_o, err_corrected_o, err_uncorrectable_o
);
  logic [6:0] pdbg, syn;
  logic [71:0] ccw, mask;
  logic om;
  logic [$clog2(73)-1:0] ep;
  secded_encoder #(.DATA_W(64)) u_e(.data_i(data_i), .codeword_o(codeword_o), .parity_dbg_o(pdbg));
  secded_decoder #(.DATA_W(64)) u_d(.codeword_i(codeword_in_i), .data_o(data_o), .corrected_codeword_o(ccw), .syndrome_o(syn), .overall_mismatch_o(om), .err_detected_o(err_detected_o), .err_corrected_o(err_corrected_o), .err_uncorrectable_o(err_uncorrectable_o), .correction_mask_o(mask), .error_pos_o(ep));
endmodule

module sec_daec_64 (
  input logic [63:0] data_i, output logic [71:0] codeword_o, input logic [71:0] codeword_in_i, output logic [63:0] data_o,
  output logic err_detected_o, err_corrected_o, err_uncorrectable_o
);
  logic [71:0] ccw; logic [6:0] syn; logic adj;
  secdaec_encoder #(.DATA_W(64)) u_e(.data_i(data_i), .codeword_o(codeword_o));
  secdaec_decoder #(.DATA_W(64)) u_d(.codeword_i(codeword_in_i), .data_o(data_o), .corrected_codeword_o(ccw), .syndrome_o(syn), .err_detected_o(err_detected_o), .err_corrected_o(err_corrected_o), .err_uncorrectable_o(err_uncorrectable_o), .adjacent_double_corrected_o(adj));
endmodule

module taec_64 (
  input logic [63:0] data_i, output logic [71:0] codeword_o, input logic [71:0] codeword_in_i, output logic [63:0] data_o,
  output logic err_detected_o, err_corrected_o, err_uncorrectable_o
);
  logic [71:0] ccw; logic [6:0] syn; logic tri;
  taec_encoder #(.DATA_W(64)) u_e(.data_i(data_i), .codeword_o(codeword_o));
  taec_decoder #(.DATA_W(64)) u_d(.codeword_i(codeword_in_i), .data_o(data_o), .corrected_codeword_o(ccw), .syndrome_o(syn), .err_detected_o(err_detected_o), .err_corrected_o(err_corrected_o), .err_uncorrectable_o(err_uncorrectable_o), .triple_adjacent_corrected_o(tri));
endmodule

module bch_63 (
  input logic [50:0] data_i, output logic [62:0] codeword_o, input logic [62:0] codeword_in_i, output logic [50:0] data_o,
  output logic err_detected_o, err_corrected_o, err_uncorrectable_o
);
  logic [62:0] ccw; logic [11:0] syn;
  bch_encoder #(.N(63), .K(51)) u_e(.data_i(data_i), .codeword_o(codeword_o));
  bch_decoder #(.N(63), .K(51)) u_d(.codeword_i(codeword_in_i), .data_o(data_o), .corrected_codeword_o(ccw), .syndrome_o(syn), .err_detected_o(err_detected_o), .err_corrected_o(err_corrected_o), .err_uncorrectable_o(err_uncorrectable_o));
endmodule

module polar_64_32 (
  input logic [31:0] data_i, output logic [63:0] codeword_o, input logic [63:0] codeword_in_i, output logic [31:0] data_o,
  output logic err_detected_o, err_corrected_o, err_uncorrectable_o
);
  logic [63:0] udbg, cwcorr, uhat;
  polar_encoder #(.N(64), .K(32)) u_e(.data_i(data_i), .codeword_o(codeword_o), .u_dbg_o(udbg));
  polar_decoder #(.N(64), .K(32)) u_d(.codeword_i(codeword_in_i), .data_o(data_o), .corrected_codeword_o(cwcorr), .u_hat_o(uhat), .err_detected_o(err_detected_o), .err_corrected_o(err_corrected_o), .err_uncorrectable_o(err_uncorrectable_o));
endmodule

module polar_64_48 (
  input logic [47:0] data_i, output logic [63:0] codeword_o, input logic [63:0] codeword_in_i, output logic [47:0] data_o,
  output logic err_detected_o, err_corrected_o, err_uncorrectable_o
);
  logic [63:0] udbg, cwcorr, uhat;
  polar_encoder #(.N(64), .K(48)) u_e(.data_i(data_i), .codeword_o(codeword_o), .u_dbg_o(udbg));
  polar_decoder #(.N(64), .K(48)) u_d(.codeword_i(codeword_in_i), .data_o(data_o), .corrected_codeword_o(cwcorr), .u_hat_o(uhat), .err_detected_o(err_detected_o), .err_corrected_o(err_corrected_o), .err_uncorrectable_o(err_uncorrectable_o));
endmodule

module polar_128_96 (
  input logic [95:0] data_i, output logic [127:0] codeword_o, input logic [127:0] codeword_in_i, output logic [95:0] data_o,
  output logic err_detected_o, err_corrected_o, err_uncorrectable_o
);
  logic [127:0] udbg, cwcorr, uhat;
  polar_encoder #(.N(128), .K(96)) u_e(.data_i(data_i), .codeword_o(codeword_o), .u_dbg_o(udbg));
  polar_decoder #(.N(128), .K(96)) u_d(.codeword_i(codeword_in_i), .data_o(data_o), .corrected_codeword_o(cwcorr), .u_hat_o(uhat), .err_detected_o(err_detected_o), .err_corrected_o(err_corrected_o), .err_uncorrectable_o(err_uncorrectable_o));
endmodule
