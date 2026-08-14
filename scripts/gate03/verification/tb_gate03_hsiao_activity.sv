`timescale 1ns/1ps
// Verification/activity harness only. FAULT_WEIGHT=0 is the primary clean workload;
// weights 1 and 2 are conditional decoder workloads and are never PMF-weighted here.
module gate03_tb_hsiao_activity #(
  parameter integer FAULT_WEIGHT = 0
);
  logic clk = 1'b0;
  logic valid_i = 1'b1;
  logic [63:0] data = 64'h475245454e454343;
  logic [71:0] clean_codeword, decoder_input, testbench_mask;
  logic valid_o, detected, corrected, uncorrectable;
  logic [63:0] decoded;
  integer i, bit_a, bit_b;

  always #5 clk = ~clk;
  hsiao_secded_72_64_v1_encoder reference_encoder(.data(data), .codeword(clean_codeword));
  assign decoder_input = clean_codeword ^ testbench_mask;
  gate03_hsiao_decoder_shell dut(
    .clk(clk), .valid_i(valid_i), .codeword_i(decoder_input), .valid_o(valid_o),
    .data_o(decoded), .detected_o(detected), .corrected_o(corrected),
    .uncorrectable_o(uncorrectable)
  );

  initial begin
    $dumpfile("gate03-hsiao-activity.vcd");
    $dumpvars(0, dut);
    $dumpoff;
    testbench_mask = '0;
    for (i = -256; i < 8192; i = i + 1) begin
      @(negedge clk);
      if (i == 0) $dumpon;
      data = (data ^ (data << 13)) ^ (data >> 7) ^ (data << 17);
      testbench_mask = '0;
      bit_a = ((i + 256) * 17 + 3) % 72;
      bit_b = ((i + 256) * 29 + 11) % 72;
      if (bit_b == bit_a) bit_b = (bit_b + 1) % 72;
      if (FAULT_WEIGHT >= 1) testbench_mask[bit_a] = 1'b1;
      if (FAULT_WEIGHT >= 2) testbench_mask[bit_b] = 1'b1;
    end
    @(negedge clk);
    $dumpoff;
    $display("GATE03_ACTIVITY_PASS hsiao fault_weight=%0d measured_cycles=8192", FAULT_WEIGHT);
    $finish;
  end
endmodule
