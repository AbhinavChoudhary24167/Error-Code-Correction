module green_ecc_mode_controller #(
  parameter int MODES = 2,
  parameter int MODE_WIDTH = (MODES <= 1) ? 1 : $clog2(MODES),
  parameter int FALLBACK_MODE = 0
) (
  input  logic                        clk_i,
  input  logic                        rst_ni,
  input  logic                        config_valid_i,
  input  logic [MODE_WIDTH-1:0]       config_mode_i,
  input  logic                        transition_safe_i,
  output logic [MODE_WIDTH-1:0]       active_mode_o,
  output logic [3*MODE_WIDTH-1:0]     protected_metadata_o,
  output logic                        transition_pending_o,
  output logic                        transition_ack_o,
  output logic                        illegal_mode_o
);
  logic [MODE_WIDTH-1:0] pending_mode_q;

  assign protected_metadata_o = {active_mode_o, active_mode_o, active_mode_o};

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      active_mode_o        <= MODE_WIDTH'(FALLBACK_MODE);
      pending_mode_q       <= MODE_WIDTH'(FALLBACK_MODE);
      transition_pending_o <= 1'b0;
      transition_ack_o     <= 1'b0;
      illegal_mode_o       <= 1'b0;
    end else begin
      transition_ack_o <= 1'b0;
      illegal_mode_o   <= 1'b0;

      if (config_valid_i) begin
        if (config_mode_i >= MODES) begin
          active_mode_o        <= MODE_WIDTH'(FALLBACK_MODE);
          pending_mode_q       <= MODE_WIDTH'(FALLBACK_MODE);
          transition_pending_o <= 1'b0;
          transition_ack_o     <= 1'b1;
          illegal_mode_o       <= 1'b1;
        end else if (transition_safe_i) begin
          active_mode_o        <= config_mode_i;
          transition_pending_o <= 1'b0;
          transition_ack_o     <= 1'b1;
        end else begin
          pending_mode_q       <= config_mode_i;
          transition_pending_o <= 1'b1;
        end
      end else if (transition_pending_o && transition_safe_i) begin
        active_mode_o        <= pending_mode_q;
        transition_pending_o <= 1'b0;
        transition_ack_o     <= 1'b1;
      end
    end
  end

  initial begin
    if (MODES <= 0) $fatal(1, "MODES must be positive");
    if (FALLBACK_MODE < 0 || FALLBACK_MODE >= MODES) $fatal(1, "Invalid FALLBACK_MODE");
  end
endmodule
