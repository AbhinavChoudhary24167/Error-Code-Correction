//------------------------------------------------------------------------------
// File: asic/common/sram_core.sv
// Purpose: Reusable synthesizable single-port SRAM-style storage core for ECC.
// Notes  : Read data is registered and returned 1 cycle after cs && !we.
//------------------------------------------------------------------------------
module sram_core #(
  parameter int ADDR_W = 8,
  parameter int CODE_W = 72,
  parameter int DEPTH  = (1 << ADDR_W)
) (
  input  logic              clk,
  input  logic              rst_n,
  input  logic              cs,
  input  logic              we,
  input  logic [ADDR_W-1:0] addr,
  input  logic [CODE_W-1:0] wcode,
  output logic [CODE_W-1:0] rcode,
  output logic              rvalid
);
  logic [CODE_W-1:0] mem [0:DEPTH-1];

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      rcode  <= '0;
      rvalid <= 1'b0;
    end else begin
      rvalid <= 1'b0;

      if (cs && we) begin
        mem[addr] <= wcode;
      end

      if (cs && !we) begin
        rcode  <= mem[addr];
        rvalid <= 1'b1;
      end
    end
  end
endmodule
