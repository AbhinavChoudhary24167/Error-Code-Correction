module green_ecc_select_mux #(
  parameter int WIDTH = 64,
  parameter int MODES = 2,
  parameter int MODE_WIDTH = (MODES <= 1) ? 1 : $clog2(MODES),
  parameter int FALLBACK_MODE = 0
) (
  input  logic [MODES*WIDTH-1:0] data_i,
  input  logic [MODE_WIDTH-1:0]  mode_i,
  output logic [WIDTH-1:0]       data_o,
  output logic                   illegal_mode_o
);
  int selected_mode;

  always_comb begin
    illegal_mode_o = (mode_i >= MODES);
    selected_mode = illegal_mode_o ? FALLBACK_MODE : mode_i;
    data_o = data_i[selected_mode*WIDTH +: WIDTH];
  end

  initial begin
    if (WIDTH <= 0 || MODES <= 0) $fatal(1, "WIDTH and MODES must be positive");
    if (FALLBACK_MODE < 0 || FALLBACK_MODE >= MODES) $fatal(1, "Invalid FALLBACK_MODE");
  end
endmodule
