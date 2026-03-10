//------------------------------------------------------------------------------
// File: secdaec_codec.sv
// Purpose: SEC-DAEC codec built on Hamming structure with explicit adjacent
//          double-error correction search over data-bit adjacency.
// Scheme: SEC-DAEC
// Assumptions: Adjacent means neighboring indices in extracted data payload.
//              Non-adjacent double-bit errors remain uncorrectable.
// Synthesizability: Yes (combinational bounded search).
//------------------------------------------------------------------------------
module secdaec_encoder #(
  parameter int DATA_W = 64
) (
  input  logic [DATA_W-1:0] data_i,
  output logic [DATA_W+ecc_pkg::hamming_parity_bits(DATA_W):0] codeword_o
);
  localparam int P_W = ecc_pkg::hamming_parity_bits(DATA_W);
  logic [P_W-1:0] parity_dbg;
  secded_encoder #(.DATA_W(DATA_W)) u_enc (
    .data_i(data_i), .codeword_o(codeword_o), .parity_dbg_o(parity_dbg)
  );
endmodule

module secdaec_decoder #(
  parameter int DATA_W = 64,
  parameter int P_W    = ecc_pkg::hamming_parity_bits(DATA_W),
  parameter int N_W    = DATA_W + P_W
) (
  input  logic [N_W:0]      codeword_i,
  output logic [DATA_W-1:0] data_o,
  output logic [N_W:0]      corrected_codeword_o,
  output logic [P_W-1:0]    syndrome_o,
  output logic              err_detected_o,
  output logic              err_corrected_o,
  output logic              err_uncorrectable_o,
  output logic              adjacent_double_corrected_o
);
  int i, cpos, d_idx;
  logic [DATA_W-1:0] pre_data;
  logic [N_W:0] secded_cw;
  logic [P_W-1:0] syndrome;
  logic overall_mm, det, cor, unc;
  logic [N_W:0] mask;
  logic [$clog2(N_W+2)-1:0] ep;
  logic found_adj;
  logic [N_W:0] adj_mask;

  // Helper: data index -> codeword index (0-based in codeword without overall)
  function automatic int data_idx_to_cpos0(input int unsigned data_idx);
    int unsigned count;
    int pos;
    begin
      count = 0;
      for (pos = 1; pos <= N_W; pos++) begin
        if (!ecc_pkg::is_pow2(pos)) begin
          if (count == data_idx) return pos-1;
          count++;
        end
      end
      return 0;
    end
  endfunction

  secded_decoder #(.DATA_W(DATA_W)) u_dec (
    .codeword_i(codeword_i),
    .data_o(pre_data),
    .corrected_codeword_o(secded_cw),
    .syndrome_o(syndrome),
    .overall_mismatch_o(overall_mm),
    .err_detected_o(det),
    .err_corrected_o(cor),
    .err_uncorrectable_o(unc),
    .correction_mask_o(mask),
    .error_pos_o(ep)
  );

  always_comb begin
    found_adj = 1'b0;
    adj_mask = '0;

    // Only attempt DAEC rescue for standard SEC-DED double-bit signature.
    if ((syndrome != '0) && !overall_mm) begin
      for (i = 0; i < DATA_W-1; i++) begin
        int p0, p1;
        logic [P_W-1:0] pair_sig;
        p0 = data_idx_to_cpos0(i) + 1;
        p1 = data_idx_to_cpos0(i+1) + 1;
        pair_sig = p0[P_W-1:0] ^ p1[P_W-1:0];
        if (!found_adj && (pair_sig == syndrome)) begin
          found_adj = 1'b1;
          adj_mask[p0-1] = 1'b1;
          adj_mask[p1-1] = 1'b1;
        end
      end
    end

    if (found_adj) corrected_codeword_o = codeword_i ^ adj_mask;
    else corrected_codeword_o = secded_cw;

    d_idx = 0;
    data_o = '0;
    for (cpos = 1; cpos <= N_W; cpos++) begin
      if (!ecc_pkg::is_pow2(cpos)) begin
        data_o[d_idx] = corrected_codeword_o[cpos-1];
        d_idx++;
      end
    end

    syndrome_o = syndrome;
    err_detected_o = det;
    adjacent_double_corrected_o = found_adj;
    err_corrected_o = cor | found_adj;
    err_uncorrectable_o = unc & ~found_adj;
  end
endmodule
