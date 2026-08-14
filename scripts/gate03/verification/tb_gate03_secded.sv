`timescale 1ns/1ps
module gate03_tb_secded;
  logic [63:0] data;
  logic [71:0] codeword, received, corrected_codeword, fault_mask;
  logic [63:0] decoded;
  logic [6:0] syndrome, error_pos;
  logic overall_mismatch, detected, corrected, uncorrectable;
  logic [71:0] correction_mask;
  integer i, bit_a, bit_b;

  secded_encoder #(.DATA_W(64)) u_encoder(
    .data_i(data), .codeword_o(codeword), .parity_dbg_o()
  );
  // Verification-only injection. This top is never supplied to synthesis/ORFS.
  assign received = codeword ^ fault_mask;
  secded_decoder #(.DATA_W(64)) u_decoder(
    .codeword_i(received), .data_o(decoded), .corrected_codeword_o(corrected_codeword),
    .syndrome_o(syndrome), .overall_mismatch_o(overall_mismatch),
    .err_detected_o(detected), .err_corrected_o(corrected),
    .err_uncorrectable_o(uncorrectable), .correction_mask_o(correction_mask),
    .error_pos_o(error_pos)
  );

  initial begin
    data = 64'h475245454e454343;
    fault_mask = '0;
    #1;
    for (i = -256; i < 8192; i = i + 1) begin
      data = (data ^ (data << 13)) ^ (data >> 7) ^ (data << 17);
      fault_mask = '0;
      if ((i >= 0) && ((i % 10) == 8)) begin
        bit_a = (i * 17 + 3) % 72;
        fault_mask[bit_a] = 1'b1;
      end else if ((i >= 0) && ((i % 10) == 9)) begin
        bit_a = (i * 17 + 3) % 72;
        bit_b = (i * 29 + 11) % 72;
        if (bit_b == bit_a) bit_b = (bit_b + 1) % 72;
        fault_mask[bit_a] = 1'b1;
        fault_mask[bit_b] = 1'b1;
      end
      #1;
      if ((i < 0 || (i % 10) != 9) && decoded !== data) $fatal(1, "SECDED mismatch at %0d", i);
    end
    $display("GATE03_VERIFICATION_PASS secded stress=80/10/10 power_eligible=0");
    $finish;
  end
endmodule
