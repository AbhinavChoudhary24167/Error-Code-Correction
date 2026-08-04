`timescale 1ns/1ps
module tb_green_ecc_transition_controller;
  logic clk = 0;
  logic rst_n = 0;
  logic request, quiesce_done, read_done, decode_done, encode_done;
  logic write_done, verify_done, verify_ok, resume_done, abort;
  logic [1:0] requested_mode, active_mode, target_mode;
  logic [3:0] state;
  logic busy, commit, recovery;

  always #5 clk = ~clk;

  green_ecc_transition_controller #(.MODE_COUNT(3), .SAFE_FALLBACK(2'd2)) dut (
    .clk_i(clk), .rst_ni(rst_n), .request_i(request),
    .requested_mode_i(requested_mode), .quiesce_done_i(quiesce_done),
    .read_done_i(read_done), .decode_done_i(decode_done),
    .encode_done_i(encode_done), .write_done_i(write_done),
    .verify_done_i(verify_done), .verify_ok_i(verify_ok),
    .resume_done_i(resume_done), .abort_i(abort),
    .active_mode_o(active_mode), .target_mode_o(target_mode),
    .state_o(state), .busy_o(busy), .metadata_commit_o(commit),
    .recovery_o(recovery)
  );

`define PULSE(signal) begin signal = 1'b1; @(posedge clk); #1; signal = 1'b0; end

  initial begin
    request = 0; requested_mode = 0; quiesce_done = 0; read_done = 0;
    decode_done = 0; encode_done = 0; write_done = 0; verify_done = 0;
    verify_ok = 0; resume_done = 0; abort = 0;
    repeat (2) @(posedge clk); rst_n = 1; @(posedge clk); #1;
    if (active_mode !== 2 || busy) $fatal(1, "safe reset failed");

    requested_mode = 1; `PULSE(request)
    `PULSE(quiesce_done) `PULSE(read_done) `PULSE(decode_done)
    `PULSE(encode_done) `PULSE(write_done)
    verify_ok = 1; `PULSE(verify_done) @(posedge clk); #1;
    if (!commit || active_mode !== 1) $fatal(1, "verified commit failed");
    `PULSE(resume_done) #1;
    if (busy) $fatal(1, "controller did not return stable");

    requested_mode = 3; `PULSE(request) @(posedge clk); #1;
    if (!recovery || active_mode !== 2) $fatal(1, "illegal mode did not recover");
    `PULSE(resume_done)

    requested_mode = 0; `PULSE(request) `PULSE(quiesce_done) `PULSE(read_done)
    `PULSE(decode_done) `PULSE(encode_done) `PULSE(write_done)
    verify_ok = 0; `PULSE(verify_done) @(posedge clk); #1;
    if (!recovery || active_mode !== 2) $fatal(1, "verification failure did not recover");
    $display("PASS tb_green_ecc_transition_controller");
    $finish;
  end
endmodule

`undef PULSE
