`timescale 1ns/1ps
module tb_bch_t2_exhaustive_masks;
  logic [63:0] data;
  logic [77:0] codeword, received, corrected, correction_mask;
  logic [63:0] decoded;
  logic [27:0] syndrome;
  logic detected, correction, uncorrectable;
  integer i, j;

  bch_78_64_t2_v1_encoder enc(.data_i(data), .codeword_o(codeword));
  bch_78_64_t2_v1_decoder dec(
    .codeword_i(received), .data_o(decoded), .corrected_codeword_o(corrected),
    .syndrome_o(syndrome), .correction_mask_o(correction_mask),
    .err_detected_o(detected), .err_corrected_o(correction),
    .err_uncorrectable_o(uncorrectable));

  task automatic validate_payload(input logic [63:0] payload);
    begin
      data = payload; #1; received = codeword; #1;
      if (decoded !== data || detected || correction || uncorrectable)
        $fatal(1, "BCH no-error failure payload=%h", payload);
      for (i = 0; i < 78; i = i + 1) begin
        received = codeword ^ (78'b1 << i); #1;
        if (decoded !== data || !detected || !correction || uncorrectable)
          $fatal(1, "BCH single-bit failure bit=%0d payload=%h", i, payload);
      end
      for (i = 0; i < 78; i = i + 1)
        for (j = i + 1; j < 78; j = j + 1) begin
          received = codeword ^ (78'b1 << i) ^ (78'b1 << j); #1;
          if (decoded !== data || !detected || !correction || uncorrectable)
            $fatal(1, "BCH double-bit failure bits=%0d,%0d payload=%h", i, j, payload);
        end
    end
  endtask

  initial begin
    validate_payload(64'h0000_0000_0000_0000);
    validate_payload(64'hffff_ffff_ffff_ffff);
    validate_payload(64'h0123_4567_89ab_cdef);
    validate_payload(64'ha5a5_5a5a_c33c_3cc3);
    $display("FUNCTIONAL_PASS arch=BCH_T2 payloads=4 single_masks=312 double_masks=12012");
    $finish;
  end
endmodule
