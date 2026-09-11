`timescale 1ns/1ps
module tb;
  localparam real CLOCK_NS = 10.000000;
  reg clk = 1'b0;
  reg rstb = 1'b0;
  reg ce = 1'b0;
  reg we = 1'b0;
  reg [7:0] addr = 8'b0;
  reg [63:0] payload_in = 64'b0;
  wire [63:0] payload_out;
  wire correction_applied;
  wire detected_uncorrectable;
  reg [63:0] payloads [0:255];
  reg [71:0] codewords [0:255];
  integer i, index, address, failures;

  secded_matched_sram_top dut(
    .clk(clk), .rstb(rstb), .ce(ce), .we(we), .addr(addr),
    .payload_in(payload_in), .payload_out(payload_out),
    .correction_applied(correction_applied),
    .detected_uncorrectable(detected_uncorrectable)
  );
  always #(CLOCK_NS / 2.0) clk = ~clk;

  task apply_operation;
    input integer requested_index;
    input integer check_result;
    begin
      index = requested_index;
      address = (19 + 73 * index) % 256;
      @(negedge clk);
      addr = address[7:0];
      ce = 1'b0;
      we = 1'b0;
      payload_in = 64'b0;
      @(posedge clk); #1;
      if (check_result != 0) begin

      end
    end
  endtask

  initial begin
    failures = 0;
    $readmemh("/mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction/campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5/fresh_runs/secded_clk10p0ns_seed23/attempt01/workloads/payloads.hex", payloads);
    $readmemh("/mnt/c/Users/Abhinav/OneDrive/Desktop/ECC/Error-Code-Correction/campaigns/iscas_sustainability_extension/green_v3_3_activity_complete_e5/fresh_runs/secded_clk10p0ns_seed23/attempt01/workloads/codewords_idle.hex", codewords);
    for (i = 0; i < 256; i = i + 1) begin
      address = (19 + 73 * i) % 256;
      dut.u_data.mem[address] = codewords[i][63:0];
      dut.u_ecc0.mem[address] = codewords[i][71:64];
    end
    repeat (2) @(posedge clk);
    rstb = 1'b1;
    // Establish a known SRAM output state before every operation-class warm-up.
    // This read is outside both the 16 warm-up operations and measured window.
    @(negedge clk);
    addr = 8'd19;
    ce = 1'b1;
    we = 1'b0;
    payload_in = 64'b0;
    @(posedge clk); #1;
    for (i = 0; i < 16; i = i + 1) apply_operation(i, 0);
    $dumpfile("/var/lib/green-ecc-v33-activity-complete-e5/fresh_runs/secded_clk10p0ns_seed23/attempt01/activity/IDLE.vcd");
    $dumpvars(1, dut);
    $display("MEASUREMENT_BEGIN_NS=%.3f", $realtime);
    for (i = 0; i < 256; i = i + 1) apply_operation(i, 0);
    #1;
    $display("MEASUREMENT_END_NS=%.3f", $realtime);
    $dumpoff;
    if (failures != 0) $fatal(1, "FUNCTIONAL_FAILURE_COUNT=%0d", failures);
    $display("SIMULATION_PASS operation=IDLE warmup=16 operations=256");
    $finish;
  end
endmodule
