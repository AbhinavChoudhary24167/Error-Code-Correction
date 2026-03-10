`timescale 1ns/1ps
module tb_polar;
  logic [31:0] d;
  logic [63:0] cw, cwi, cwc, udbg, uhat;
  logic [31:0] dout;
  logic det, cor, unc;
  int i;

  polar_encoder #(.N(64), .K(32)) enc(.data_i(d), .codeword_o(cw), .u_dbg_o(udbg));
  polar_decoder #(.N(64), .K(32)) dec(.codeword_i(cwi), .data_o(dout), .corrected_codeword_o(cwc), .u_hat_o(uhat), .err_detected_o(det), .err_corrected_o(cor), .err_uncorrectable_o(unc));

  initial begin
    d = 32'h1234abcd; #1;
    cwi = cw; #1;
    if (dout !== d) $fatal(1, "polar no-error failed");

    cwi = cw ^ (64'd1<<7); #1;
    if (!det) $fatal(1, "polar single error detect failed");

    for (i = 0; i < 20; i++) begin
      d = $urandom;
      #1; cwi = cw ^ (64'd1 << ($urandom%64)); #1;
      if (unc) $fatal(1, "polar randomized bounded decode flagged uncorrectable unexpectedly");
    end

    $display("TB_POLAR_PASS");
    $finish;
  end
endmodule
