`timescale 1ns/1ps
module tb_secdaec;
  logic [63:0] d;
  logic [71:0] cw, cwi, cwc;
  logic [63:0] dout;
  logic [6:0] syn;
  logic det, cor, unc, adj;

  secdaec_encoder #(.DATA_W(64)) enc(.data_i(d), .codeword_o(cw));
  secdaec_decoder #(.DATA_W(64)) dec(.codeword_i(cwi), .data_o(dout), .corrected_codeword_o(cwc), .syndrome_o(syn), .err_detected_o(det), .err_corrected_o(cor), .err_uncorrectable_o(unc), .adjacent_double_corrected_o(adj));

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
    d = 64'hfeed_face_cafe_beef; #1; cwi = cw; #1;
    if (dout !== d) $fatal(1, "secdaec no-error failed");

    cwi = cw;
    cwi[data_idx_to_cpos0(10)] ^= 1'b1;
    cwi[data_idx_to_cpos0(11)] ^= 1'b1;
    #1;
    if (dout !== d || !adj || !cor) $fatal(1, "secdaec adjacent double correction failed");

    cwi = cw ^ (72'd1<<2) ^ (72'd1<<18); #1;
    if (!unc) $fatal(1, "secdaec non-adj double should be uncorrectable");

    $display("TB_SECDAEC_PASS");
    $finish;
  end
endmodule
