`timescale 1ns/1ps
module tb_memory_smoke;
  logic clk = 0;
  logic rstb = 0;
  logic ce = 0;
  logic we = 0;
  logic [7:0] addr = 0;
  logic [63:0] payload_in = 0;
  logic [63:0] payload_out;
  logic correction_applied, detected_uncorrectable;
  integer i;
  logic [63:0] patterns [0:3];

`ifdef TEST_U0
  u0_matched_sram_top dut(.*);
`elsif TEST_SECDED
  secded_matched_sram_top dut(.*);
`elsif TEST_HSIAO
  hsiao_matched_sram_top dut(.*);
`elsif TEST_SECDAEC
  secdaec_matched_sram_top dut(.*);
`elsif TEST_BCH
  bch_t2_matched_sram_top dut(.*);
`else
  initial $fatal(1, "No TEST_* architecture define supplied");
`endif

  always #5 clk = ~clk;

  initial begin
    patterns[0] = 64'h0000_0000_0000_0000;
    patterns[1] = 64'hffff_ffff_ffff_ffff;
    patterns[2] = 64'h0123_4567_89ab_cdef;
    patterns[3] = 64'ha5a5_5a5a_c33c_3cc3;
    // Force an initial transition before the first all-zero write. Some
    // checked-in combinational encoders intentionally use always @(data_i).
    payload_in = 64'hdeaf_beef_0123_4567;
    repeat (2) @(negedge clk);
    rstb = 1; ce = 1;
    for (i = 0; i < 4; i = i + 1) begin
      @(negedge clk); we = 1; addr = 8'h40 + i; payload_in = patterns[i];
      @(negedge clk); we = 0; addr = 8'h40 + i;
      @(negedge clk);
      if (payload_out !== patterns[i])
        $fatal(1, "memory round-trip failure index=%0d expected=%h got=%h", i, patterns[i], payload_out);
      if (correction_applied || detected_uncorrectable)
        $fatal(1, "unexpected no-error status index=%0d", i);
    end
    $display("MEMORY_INTEGRATION_PASS transactions=4");
    $finish;
  end
endmodule
