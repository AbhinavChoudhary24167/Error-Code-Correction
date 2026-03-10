`timescale 1ns/1ps
module tb_secded;
  logic [63:0] d;
  logic [71:0] cw, cwi, cwc;
  logic [63:0] dout;
  logic [6:0] syn;
  logic om, det, cor, unc;
  logic [71:0] mask;
  logic [$clog2(73)-1:0] ep;
  int i;

  secded_encoder #(.DATA_W(64)) enc(.data_i(d), .codeword_o(cw), .parity_dbg_o());
  secded_decoder #(.DATA_W(64)) dec(.codeword_i(cwi), .data_o(dout), .corrected_codeword_o(cwc), .syndrome_o(syn), .overall_mismatch_o(om), .err_detected_o(det), .err_corrected_o(cor), .err_uncorrectable_o(unc), .correction_mask_o(mask), .error_pos_o(ep));

  initial begin
    d = 64'h0123_4567_89ab_cdef;
    #1; cwi = cw; #1;
    if (dout !== d || det) $fatal(1, "secded no-error failed");

    for (i = 0; i < 72; i++) begin
      cwi = cw ^ (72'd1 << i); #1;
      if (dout !== d || !cor) $fatal(1, "secded single-bit failed at %0d", i);
    end

    cwi = cw ^ (72'd1<<3) ^ (72'd1<<7); #1;
    if (!unc) $fatal(1, "secded double-bit detect failed");

    $display("TB_SEDDED_PASS");
    $finish;
  end
endmodule
