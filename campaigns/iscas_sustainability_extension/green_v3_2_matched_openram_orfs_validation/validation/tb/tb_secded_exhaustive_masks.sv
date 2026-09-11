`timescale 1ns/1ps
module tb_secded_exhaustive_masks;
  logic [63:0] data;
  logic [71:0] codeword, received, corrected;
  logic [63:0] decoded;
  logic detected, correction, uncorrectable;
  integer i, j;

  gate03r_secded_baseline_encoder enc(.data_i(data), .codeword_o(codeword));
  gate03r_secded_baseline_decoder dec(
    .codeword_i(received), .data_o(decoded), .corrected_codeword_o(corrected),
    .err_detected_o(detected), .err_corrected_o(correction),
    .err_uncorrectable_o(uncorrectable));

  task automatic validate_payload(input logic [63:0] payload);
    begin
      data = payload; #1; received = codeword; #1;
      if (decoded !== data || detected || correction || uncorrectable)
        $fatal(1, "SECDED no-error failure payload=%h", payload);
      for (i = 0; i < 72; i = i + 1) begin
        received = codeword ^ (72'b1 << i); #1;
        if (decoded !== data || !detected || !correction || uncorrectable)
          $fatal(1, "SECDED single-bit failure bit=%0d payload=%h", i, payload);
      end
      for (i = 0; i < 72; i = i + 1)
        for (j = i + 1; j < 72; j = j + 1) begin
          received = codeword ^ (72'b1 << i) ^ (72'b1 << j); #1;
          if (!detected || correction || !uncorrectable)
            $fatal(1, "SECDED double-detection failure bits=%0d,%0d", i, j);
        end
    end
  endtask

  initial begin
    validate_payload(64'h0000_0000_0000_0000);
    validate_payload(64'hffff_ffff_ffff_ffff);
    validate_payload(64'h0123_4567_89ab_cdef);
    validate_payload(64'ha5a5_5a5a_c33c_3cc3);
    $display("FUNCTIONAL_PASS arch=SECDED payloads=4 single_masks=288 double_masks=10224");
    $finish;
  end
endmodule
