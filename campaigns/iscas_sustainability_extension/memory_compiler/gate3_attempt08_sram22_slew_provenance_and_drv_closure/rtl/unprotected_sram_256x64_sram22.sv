// Attempt06 U0 baseline: one unchanged 256x64 SRAM22 hard macro and only the
// minimal logical wrapper needed to expose its published interface.
module u0_sram22_top (
  input  logic        clk,
  input  logic        rstb,
  input  logic        ce,
  input  logic        we,
  input  logic [7:0]  wmask,
  input  logic [7:0]  addr,
  input  logic [63:0] data_in,
  output logic [63:0] data_out
);
  sram22_256x64m4w8 u_data (
    .clk(clk),
    .rstb(rstb),
    .ce(ce),
    .we(we),
    .wmask(wmask),
    .addr(addr),
    .din(data_in),
    .dout(data_out)
  );
endmodule
