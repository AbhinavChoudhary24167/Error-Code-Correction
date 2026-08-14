`timescale 1ns/1ps
module gate03_tb_hsiao;
  logic [63:0] data, decoded;
  logic [71:0] codeword, received, fault_mask;
  logic corrected, uncorrectable;
  integer i, bit_a, bit_b;

  hsiao_secded_72_64_v1_encoder u_encoder(.data(data), .codeword(codeword));
  // Verification-only injection. This top is never supplied to synthesis/ORFS.
  assign received = codeword ^ fault_mask;
  hsiao_secded_72_64_v1_decoder u_decoder(
    .word(received), .data_out(decoded), .correction_applied(corrected),
    .detected_uncorrectable(uncorrectable)
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
      if ((i < 0 || (i % 10) != 9) && decoded !== data) $fatal(1, "Hsiao mismatch at %0d", i);
    end
    $display("GATE03_VERIFICATION_PASS hsiao stress=80/10/10 power_eligible=0");
    $finish;
  end
endmodule
