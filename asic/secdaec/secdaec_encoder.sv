// SEC-DAEC 64b fixed encoder wrapper.
// Self-contained Verilog-2001 implementation (no package dependency).
module secdaec_64_encoder #(
  parameter DATA_W = 64,
  parameter ECC_W  = 8,
  parameter CODE_W = DATA_W + ECC_W
) (
  input      [DATA_W-1:0] data_i,
  output reg [CODE_W-1:0] codeword_o
);
  integer d_idx;
  integer p;
  integer cpos;
  reg [CODE_W-2:0] code_wo_overall;
  reg overall;
  reg px;

  function is_pow2;
    input integer v;
    begin
      if (v <= 0) is_pow2 = 1'b0;
      else is_pow2 = ((v & (v - 1)) == 0);
    end
  endfunction

  always @* begin
    code_wo_overall = {CODE_W-1{1'b0}};
    d_idx = 0;

    // Fill non-parity positions (1-based indexing over CODE_W-1 field bits).
    for (cpos = 1; cpos <= CODE_W-1; cpos = cpos + 1) begin
      if (!is_pow2(cpos)) begin
        if (d_idx < DATA_W) begin
          code_wo_overall[cpos-1] = data_i[d_idx];
          d_idx = d_idx + 1;
        end
      end
    end

    // Compute Hamming parity bits.
    for (p = 0; p < ECC_W-1; p = p + 1) begin
      px = 1'b0;
      for (cpos = 1; cpos <= CODE_W-1; cpos = cpos + 1) begin
        if (cpos & (1 << p)) begin
          px = px ^ code_wo_overall[cpos-1];
        end
      end
      if ((1 << p) <= (CODE_W-1)) begin
        code_wo_overall[(1 << p)-1] = px;
      end
    end

    overall = ^code_wo_overall;
    codeword_o = {overall, code_wo_overall};
  end
endmodule
