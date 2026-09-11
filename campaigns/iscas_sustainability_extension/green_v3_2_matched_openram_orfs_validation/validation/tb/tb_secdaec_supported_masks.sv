`timescale 1ns/1ps
module tb_secdaec_supported_masks;
  logic [63:0] data;
  logic [71:0] codeword, received, corrected;
  logic [63:0] decoded;
  logic [6:0] syndrome;
  logic detected, correction, uncorrectable, adjacent;
  integer i;

  secdaec_encoder #(.DATA_W(64)) enc(.data_i(data), .codeword_o(codeword));
  secdaec_decoder #(.DATA_W(64)) dec(
    .codeword_i(received), .data_o(decoded), .corrected_codeword_o(corrected),
    .syndrome_o(syndrome), .err_detected_o(detected),
    .err_corrected_o(correction), .err_uncorrectable_o(uncorrectable),
    .adjacent_double_corrected_o(adjacent));

  function automatic integer data_idx_to_cpos0(input integer data_idx);
    integer count, pos;
    begin
      count = 0;
      data_idx_to_cpos0 = 0;
      for (pos = 1; pos <= 71; pos = pos + 1)
        if ((pos & (pos - 1)) != 0) begin
          if (count == data_idx) data_idx_to_cpos0 = pos - 1;
          count = count + 1;
        end
    end
  endfunction

  task automatic validate_payload(input logic [63:0] payload);
    integer p0, p1;
    begin
      data = payload; #1; received = codeword; #1;
      if (decoded !== data || detected || correction || uncorrectable || adjacent)
        $fatal(1, "SEC-DAEC no-error failure payload=%h", payload);
      for (i = 0; i < 72; i = i + 1) begin
        received = codeword ^ (72'b1 << i); #1;
        if (decoded !== data || !detected || !correction || uncorrectable)
          $fatal(1, "SEC-DAEC single-bit failure bit=%0d payload=%h", i, payload);
      end
      for (i = 0; i < 63; i = i + 1) begin
        p0 = data_idx_to_cpos0(i);
        p1 = data_idx_to_cpos0(i + 1);
        received = codeword ^ (72'b1 << p0) ^ (72'b1 << p1); #1;
        if (decoded !== data || !detected || !correction || !adjacent || uncorrectable)
          $fatal(1, "SEC-DAEC adjacent-pair failure data_bits=%0d,%0d", i, i + 1);
      end
    end
  endtask

  initial begin
    validate_payload(64'h0000_0000_0000_0000);
    validate_payload(64'hffff_ffff_ffff_ffff);
    validate_payload(64'hfeed_face_cafe_beef);
    validate_payload(64'h0f0f_f0f0_55aa_aa55);
    $display("FUNCTIONAL_PASS arch=SEC_DAEC payloads=4 single_masks=288 adjacent_double_masks=252");
    $finish;
  end
endmodule
