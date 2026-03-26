// SEC-DAEC 64b fixed decoder wrapper.
// Self-contained Verilog-2001 implementation (no package dependency).
module secdaec_64_decoder #(
  parameter DATA_W = 64,
  parameter ECC_W  = 8,
  parameter CODE_W = DATA_W + ECC_W
) (
  input      [CODE_W-1:0] codeword_i,
  output reg [DATA_W-1:0] data_o,
  output reg [CODE_W-1:0] corrected_codeword_o,
  output reg              err_detected_o,
  output reg              err_corrected_o,
  output reg              err_uncorrectable_o,
  output reg              adjacent_error_o
);
  integer p;
  integer cpos;
  integer d_idx;
  integer i;
  integer p0;
  integer p1;
  integer err_pos;

  reg [ECC_W-2:0] syndrome;
  reg overall_calc;
  reg overall_mismatch;
  reg [CODE_W-1:0] secded_corr;
  reg [CODE_W-1:0] correction_mask;
  reg found_adj;
  reg [CODE_W-1:0] adj_mask;
  reg [ECC_W-2:0] pair_sig;
  reg [CODE_W-2:0] code_field;

  function is_pow2;
    input integer v;
    begin
      if (v <= 0) is_pow2 = 1'b0;
      else is_pow2 = ((v & (v - 1)) == 0);
    end
  endfunction

  function integer data_idx_to_cpos0;
    input integer data_idx;
    integer count;
    integer pos;
    begin
      count = 0;
      data_idx_to_cpos0 = 0;
      for (pos = 1; pos <= CODE_W-1; pos = pos + 1) begin
        if (!is_pow2(pos)) begin
          if (count == data_idx) begin
            data_idx_to_cpos0 = pos - 1;
          end
          count = count + 1;
        end
      end
    end
  endfunction

  always @* begin
    code_field = codeword_i[CODE_W-2:0];

    // SEC-DED base decode.
    syndrome = {ECC_W-1{1'b0}};
    for (p = 0; p < ECC_W-1; p = p + 1) begin
      reg sx;
      sx = 1'b0;
      for (cpos = 1; cpos <= CODE_W-1; cpos = cpos + 1) begin
        if (cpos & (1 << p)) begin
          sx = sx ^ codeword_i[cpos-1];
        end
      end
      syndrome[p] = sx;
    end

    overall_calc = ^codeword_i[CODE_W-2:0];
    overall_mismatch = (overall_calc != codeword_i[CODE_W-1]);
    err_pos = syndrome;

    correction_mask = {CODE_W{1'b0}};
    err_detected_o = (syndrome != {ECC_W-1{1'b0}}) || overall_mismatch;
    err_corrected_o = 1'b0;
    err_uncorrectable_o = 1'b0;
    adjacent_error_o = 1'b0;

    if ((syndrome != {ECC_W-1{1'b0}}) && overall_mismatch) begin
      if ((err_pos >= 1) && (err_pos <= CODE_W-1)) begin
        correction_mask[err_pos-1] = 1'b1;
        err_corrected_o = 1'b1;
      end
    end else if ((syndrome == {ECC_W-1{1'b0}}) && overall_mismatch) begin
      correction_mask[CODE_W-1] = 1'b1;
      err_corrected_o = 1'b1;
    end else if ((syndrome != {ECC_W-1{1'b0}}) && !overall_mismatch) begin
      err_uncorrectable_o = 1'b1;
    end

    secded_corr = codeword_i ^ correction_mask;

    // DAEC adjacent-pair rescue for (syndrome!=0 && overall_mismatch==0).
    found_adj = 1'b0;
    adj_mask = {CODE_W{1'b0}};
    if ((syndrome != {ECC_W-1{1'b0}}) && !overall_mismatch) begin
      for (i = 0; i < DATA_W-1; i = i + 1) begin
        p0 = data_idx_to_cpos0(i) + 1;
        p1 = data_idx_to_cpos0(i+1) + 1;
        pair_sig = p0[ECC_W-2:0] ^ p1[ECC_W-2:0];
        if (!found_adj && (pair_sig == syndrome)) begin
          found_adj = 1'b1;
          adj_mask[p0-1] = 1'b1;
          adj_mask[p1-1] = 1'b1;
        end
      end
    end

    if (found_adj) begin
      corrected_codeword_o = codeword_i ^ adj_mask;
      adjacent_error_o = 1'b1;
      err_corrected_o = 1'b1;
      err_uncorrectable_o = 1'b0;
    end else begin
      corrected_codeword_o = secded_corr;
    end

    d_idx = 0;
    data_o = {DATA_W{1'b0}};
    for (cpos = 1; cpos <= CODE_W-1; cpos = cpos + 1) begin
      if (!is_pow2(cpos)) begin
        if (d_idx < DATA_W) begin
          data_o[d_idx] = corrected_codeword_o[cpos-1];
          d_idx = d_idx + 1;
        end
      end
    end
  end
endmodule
