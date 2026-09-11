`timescale 1ns/1ps
module tb_hsiao_exhaustive_masks;
  logic [63:0] data;
  logic [71:0] codeword, received;
  logic [63:0] decoded;
  logic correction, uncorrectable;
  integer i, j;

  hsiao_secded_72_64_v1_encoder enc(.data(data), .codeword(codeword));
  hsiao_secded_72_64_v1_decoder dec(
    .word(received), .data_out(decoded), .correction_applied(correction),
    .detected_uncorrectable(uncorrectable));

  task automatic validate_payload(input logic [63:0] payload);
    begin
      data = payload; #1; received = codeword; #1;
      if (decoded !== data || correction || uncorrectable)
        $fatal(1, "Hsiao no-error failure payload=%h", payload);
      for (i = 0; i < 72; i = i + 1) begin
        received = codeword ^ (72'b1 << i); #1;
        if (decoded !== data || !correction || uncorrectable)
          $fatal(1, "Hsiao single-bit failure bit=%0d payload=%h", i, payload);
      end
      for (i = 0; i < 72; i = i + 1)
        for (j = i + 1; j < 72; j = j + 1) begin
          received = codeword ^ (72'b1 << i) ^ (72'b1 << j); #1;
          if (correction || !uncorrectable)
            $fatal(1, "Hsiao double-detection failure bits=%0d,%0d", i, j);
        end
    end
  endtask

  initial begin
    validate_payload(64'h0000_0000_0000_0000);
    validate_payload(64'hffff_ffff_ffff_ffff);
    validate_payload(64'h0123_4567_89ab_cdef);
    validate_payload(64'ha5a5_5a5a_c33c_3cc3);
    $display("FUNCTIONAL_PASS arch=HSIAO_SECDED payloads=4 single_masks=288 double_masks=10224");
    $finish;
  end
endmodule
