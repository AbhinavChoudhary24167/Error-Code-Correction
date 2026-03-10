`timescale 1ns/1ps
module tb_taec;
  logic [63:0] d;
  logic [71:0] cw, cwi, cwc;
  logic [63:0] dout;
  logic [6:0] syn;
  logic det, cor, unc, tri;

  taec_encoder #(.DATA_W(64)) enc(.data_i(d), .codeword_o(cw));
  taec_decoder #(.DATA_W(64)) dec(.codeword_i(cwi), .data_o(dout), .corrected_codeword_o(cwc), .syndrome_o(syn), .err_detected_o(det), .err_corrected_o(cor), .err_uncorrectable_o(unc), .triple_adjacent_corrected_o(tri));

  function automatic int data_idx_to_cpos0(input int unsigned data_idx);
    int count, pos;
    begin
      count = 0;
      for (pos = 1; pos <= 71; pos++) begin
        if ((pos & (pos-1)) != 0) begin
          if (count == data_idx) return pos-1;
          count++;
        end
      end
      return 0;
    end
  endfunction

  initial begin
    d = 64'h0bad_f00d_dead_beef; #1;
    cwi = cw; #1;
    if (dout !== d) $fatal(1, "taec no-error failed");

    cwi = cw;
    cwi[data_idx_to_cpos0(20)] ^= 1'b1;
    cwi[data_idx_to_cpos0(21)] ^= 1'b1;
    cwi[data_idx_to_cpos0(22)] ^= 1'b1;
    #1;
    if (dout !== d || !tri || !cor) $fatal(1, "taec triple-adj correction failed");

    cwi = cw ^ (72'd1<<4) ^ (72'd1<<25) ^ (72'd1<<40); #1;
    if (!unc) $fatal(1, "taec non-adj triple should be uncorrectable");

    $display("TB_TAEC_PASS");
    $finish;
  end
endmodule
