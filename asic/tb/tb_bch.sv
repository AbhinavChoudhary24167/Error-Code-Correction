`timescale 1ns/1ps
module tb_bch;
  logic [50:0] d;
  logic [62:0] cw, cwi, cwc;
  logic [50:0] dout;
  logic [11:0] syn;
  logic det, cor, unc;

  bch_encoder #(.N(63), .K(51)) enc(.data_i(d), .codeword_o(cw));
  bch_decoder #(.N(63), .K(51)) dec(.codeword_i(cwi), .data_o(dout), .corrected_codeword_o(cwc), .syndrome_o(syn), .err_detected_o(det), .err_corrected_o(cor), .err_uncorrectable_o(unc));

  initial begin
    d = 51'h5a55_1234_0001; #1;
    cwi = cw; #1;
    if (dout !== d || det) $fatal(1, "bch no-error failed");

    cwi = cw ^ (63'd1<<9); #1;
    if (dout !== d || !cor) $fatal(1, "bch single-bit correction failed");

    cwi = cw ^ (63'd1<<9) ^ (63'd1<<22); #1;
    if (dout !== d || !cor) $fatal(1, "bch double-bit correction failed");

    cwi = cw ^ (63'd1<<1) ^ (63'd1<<5) ^ (63'd1<<29); #1;
    if (!unc) $fatal(1, "bch >2-bit should be uncorrectable");

    $display("TB_BCH_PASS");
    $finish;
  end
endmodule
