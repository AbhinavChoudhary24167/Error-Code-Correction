`timescale 1ns/1ps

module tb_green_ecc_selection;
  localparam int WIDTH = 7;
  localparam int MODES = 5;
  localparam int MODE_WIDTH = $clog2(MODES);

  logic clk = 1'b0;
  logic rst_n = 1'b0;
  logic config_valid;
  logic [MODE_WIDTH-1:0] config_mode;
  logic transition_safe;
  logic [MODE_WIDTH-1:0] active_mode;
  logic [3*MODE_WIDTH-1:0] metadata;
  logic pending;
  logic ack;
  logic illegal_controller;
  logic [MODES*WIDTH-1:0] mux_inputs;
  logic [WIDTH-1:0] mux_output;
  logic illegal_mux;

  always #5 clk = ~clk;

  green_ecc_mode_controller #(
    .MODES(MODES), .FALLBACK_MODE(0)
  ) controller (
    .clk_i(clk), .rst_ni(rst_n), .config_valid_i(config_valid),
    .config_mode_i(config_mode), .transition_safe_i(transition_safe),
    .active_mode_o(active_mode), .protected_metadata_o(metadata),
    .transition_pending_o(pending), .transition_ack_o(ack),
    .illegal_mode_o(illegal_controller)
  );

  green_ecc_select_mux #(
    .WIDTH(WIDTH), .MODES(MODES), .FALLBACK_MODE(0)
  ) mux (
    .data_i(mux_inputs), .mode_i(active_mode), .data_o(mux_output),
    .illegal_mode_o(illegal_mux)
  );

  task automatic request_mode(input int mode, input logic safe);
    begin
      @(negedge clk);
      config_valid = 1'b1;
      config_mode = MODE_WIDTH'(mode);
      transition_safe = safe;
      @(negedge clk);
      config_valid = 1'b0;
    end
  endtask

  initial begin
    config_valid = 1'b0;
    config_mode = '0;
    transition_safe = 1'b0;
    mux_inputs = '0;
    for (int i = 0; i < MODES; i++) mux_inputs[i*WIDTH +: WIDTH] = WIDTH'(i + 10);

    repeat (2) @(negedge clk);
    rst_n = 1'b1;
    @(negedge clk);
    if (active_mode !== 0 || mux_output !== WIDTH'(10)) $fatal(1, "Fallback reset failed");
    if (metadata !== {3{active_mode}}) $fatal(1, "Protected metadata mismatch");

    request_mode(3, 1'b1);
    if (active_mode !== 3 || mux_output !== WIDTH'(13) || !ack) $fatal(1, "Legal mode selection failed");

    request_mode(4, 1'b0);
    if (!pending || active_mode !== 3) $fatal(1, "Unsafe transition was not deferred");
    transition_safe = 1'b1;
    @(negedge clk);
    if (pending || active_mode !== 4 || !ack) $fatal(1, "Deferred transition did not commit");

    request_mode(7, 1'b1);
    if (!illegal_controller || active_mode !== 0 || mux_output !== WIDTH'(10)) $fatal(1, "Illegal mode fallback failed");

    $display("GREEN-ECC selection fabric tests passed");
    $finish;
  end
endmodule
