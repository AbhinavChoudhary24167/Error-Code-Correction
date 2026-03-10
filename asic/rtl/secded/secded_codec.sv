//------------------------------------------------------------------------------
// File: secded_codec.sv
// Purpose: Parameterized SEC-DED encoder/decoder with explicit syndrome,
//          correction mask, and error classification outputs.
// Scheme: SEC-DED (Hamming + overall parity)
// Assumptions: Standard Hamming parity placement at codeword positions that are
//              powers of 2 (1-based), plus one overall parity bit at MSB.
// Synthesizability: Yes (combinational datapath).
//------------------------------------------------------------------------------
`include "ecc_pkg.sv"

module secded_encoder #(
  parameter int DATA_W = 64,
  parameter int P_W    = ecc_pkg::hamming_parity_bits(DATA_W),
  parameter int N_W    = DATA_W + P_W
) (
  input  logic [DATA_W-1:0] data_i,
  output logic [N_W:0]      codeword_o,
  output logic [P_W-1:0]    parity_dbg_o
);
  int d_idx;
  int p;
  int cpos;
  logic [N_W-1:0] code_wo_overall;
  logic overall;

  always_comb begin
    code_wo_overall = '0;
    d_idx = 0;

    // Fill non-parity locations with data bits.
    for (cpos = 1; cpos <= N_W; cpos++) begin
      if (!ecc_pkg::is_pow2(cpos)) begin
        code_wo_overall[cpos-1] = data_i[d_idx];
        d_idx++;
      end
    end

    // Compute each parity bit over its coverage set.
    for (p = 0; p < P_W; p++) begin
      logic px;
      px = 1'b0;
      for (cpos = 1; cpos <= N_W; cpos++) begin
        if (cpos & (1 << p)) px ^= code_wo_overall[cpos-1];
      end
      code_wo_overall[(1 << p)-1] = px;
      parity_dbg_o[p] = px;
    end

    overall = ^code_wo_overall;
    codeword_o = {overall, code_wo_overall};
  end
endmodule

module secded_decoder #(
  parameter int DATA_W = 64,
  parameter int P_W    = ecc_pkg::hamming_parity_bits(DATA_W),
  parameter int N_W    = DATA_W + P_W
) (
  input  logic [N_W:0]      codeword_i,
  output logic [DATA_W-1:0] data_o,
  output logic [N_W:0]      corrected_codeword_o,
  output logic [P_W-1:0]    syndrome_o,
  output logic              overall_mismatch_o,
  output logic              err_detected_o,
  output logic              err_corrected_o,
  output logic              err_uncorrectable_o,
  output logic [N_W:0]      correction_mask_o,
  output logic [$clog2(N_W+2)-1:0] error_pos_o
);
  int p, cpos, d_idx;
  logic [P_W-1:0] syndrome;
  logic overall_calc;
  logic overall_mismatch;
  int unsigned err_pos;

  always_comb begin
    syndrome = '0;
    for (p = 0; p < P_W; p++) begin
      logic sx;
      sx = 1'b0;
      for (cpos = 1; cpos <= N_W; cpos++) begin
        if (cpos & (1 << p)) sx ^= codeword_i[cpos-1];
      end
      syndrome[p] = sx;
    end

    overall_calc = ^codeword_i[N_W-1:0];
    overall_mismatch = (overall_calc != codeword_i[N_W]);
    err_pos = syndrome;

    correction_mask_o = '0;
    err_detected_o = (syndrome != '0) || overall_mismatch;
    err_corrected_o = 1'b0;
    err_uncorrectable_o = 1'b0;

    // SEC-DED classification
    // 1) syndrome!=0 and overall mismatch => single-bit in payload/parity field
    // 2) syndrome==0 and overall mismatch => overall parity-bit error only
    // 3) syndrome!=0 and overall match    => double-bit (uncorrectable)
    if ((syndrome != '0) && overall_mismatch) begin
      if ((err_pos >= 1) && (err_pos <= N_W)) begin
        correction_mask_o[err_pos-1] = 1'b1;
        err_corrected_o = 1'b1;
      end
    end else if ((syndrome == '0) && overall_mismatch) begin
      correction_mask_o[N_W] = 1'b1;
      err_corrected_o = 1'b1;
    end else if ((syndrome != '0) && !overall_mismatch) begin
      err_uncorrectable_o = 1'b1;
    end

    corrected_codeword_o = codeword_i ^ correction_mask_o;
    syndrome_o = syndrome;
    overall_mismatch_o = overall_mismatch;
    error_pos_o = err_pos[$clog2(N_W+2)-1:0];

    d_idx = 0;
    data_o = '0;
    for (cpos = 1; cpos <= N_W; cpos++) begin
      if (!ecc_pkg::is_pow2(cpos)) begin
        data_o[d_idx] = corrected_codeword_o[cpos-1];
        d_idx++;
      end
    end
  end
endmodule
