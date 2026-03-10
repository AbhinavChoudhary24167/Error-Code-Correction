//------------------------------------------------------------------------------
// File: polar_codec.sv
// Purpose: Polar encoder and bounded hard-decision decoder.
// Scheme: Polar (N=64/128 supported via parameter)
// Assumptions: Non-systematic Arikan transform. Frozen-mask default keeps lower
//              index bits frozen. Decoder uses inverse transform + bounded
//              local search (<=2 info-bit flips), not full SC/SCL.
// Synthesizability: Yes (combinational), with notable area for local search.
//------------------------------------------------------------------------------
module polar_encoder #(
  parameter int N = 64,
  parameter int K = 32,
  parameter logic [127:0] FROZEN_MASK = polar_pkg::default_frozen_mask(N,K)
) (
  input  logic [K-1:0] data_i,
  output logic [N-1:0] codeword_o,
  output logic [N-1:0] u_dbg_o
);
  int i, j, stage, span, half;
  logic [N-1:0] u;
  logic [N-1:0] x;

  always_comb begin
    u = '0;
    j = 0;
    for (i = 0; i < N; i++) begin
      if (FROZEN_MASK[i]) u[i] = 1'b0;
      else begin
        u[i] = data_i[j];
        j++;
      end
    end

    x = u;
    for (stage = 0; stage < $clog2(N); stage++) begin
      span = (1 << (stage+1));
      half = span >> 1;
      for (i = 0; i < N; i += span) begin
        for (j = 0; j < half; j++) begin
          x[i+j] = x[i+j] ^ x[i+j+half];
        end
      end
    end

    u_dbg_o = u;
    codeword_o = x;
  end
endmodule

module polar_decoder #(
  parameter int N = 64,
  parameter int K = 32,
  parameter logic [127:0] FROZEN_MASK = polar_pkg::default_frozen_mask(N,K)
) (
  input  logic [N-1:0] codeword_i,
  output logic [K-1:0] data_o,
  output logic [N-1:0] corrected_codeword_o,
  output logic [N-1:0] u_hat_o,
  output logic         err_detected_o,
  output logic         err_corrected_o,
  output logic         err_uncorrectable_o
);
  int i, j, stage, span, half, info_cnt;
  logic [N-1:0] u_est;
  logic [N-1:0] x_reenc;
  logic [255:0] diff_vec;
  int unsigned best_dist;
  logic [N-1:0] best_u;

  function automatic int unsigned hdist(input logic [N-1:0] a, input logic [N-1:0] b);
    int unsigned c;
    int t;
    begin
      c = 0;
      for (t = 0; t < N; t++) c += (a[t]^b[t]);
      return c;
    end
  endfunction

  function automatic logic [N-1:0] polar_transform(input logic [N-1:0] in_u);
    logic [N-1:0] y;
    int s, p, q, sp, hf;
    begin
      y = in_u;
      for (s = 0; s < $clog2(N); s++) begin
        sp = (1 << (s+1));
        hf = sp >> 1;
        for (p = 0; p < N; p += sp)
          for (q = 0; q < hf; q++) y[p+q] = y[p+q] ^ y[p+q+hf];
      end
      return y;
    end
  endfunction

  always_comb begin
    // Approximate inverse (same matrix over GF(2)).
    u_est = polar_transform(codeword_i);
    for (i = 0; i < N; i++) if (FROZEN_MASK[i]) u_est[i] = 1'b0;

    best_u = u_est;
    x_reenc = polar_transform(u_est);
    best_dist = hdist(codeword_i, x_reenc);

    // Bounded local search in info-bit domain (<=2 flips).
    for (i = 0; i < N; i++) begin
      if (!FROZEN_MASK[i]) begin
        logic [N-1:0] c1_u, c1_x;
        int unsigned d1;
        c1_u = u_est;
        c1_u[i] = ~c1_u[i];
        c1_x = polar_transform(c1_u);
        d1 = hdist(codeword_i, c1_x);
        if (d1 < best_dist) begin
          best_dist = d1;
          best_u = c1_u;
        end
      end
    end

    for (i = 0; i < N; i++) begin
      if (!FROZEN_MASK[i]) begin
        for (j = i+1; j < N; j++) begin
          if (!FROZEN_MASK[j]) begin
            logic [N-1:0] c2_u, c2_x;
            int unsigned d2;
            c2_u = u_est;
            c2_u[i] = ~c2_u[i];
            c2_u[j] = ~c2_u[j];
            c2_x = polar_transform(c2_u);
            d2 = hdist(codeword_i, c2_x);
            if (d2 < best_dist) begin
              best_dist = d2;
              best_u = c2_u;
            end
          end
        end
      end
    end

    corrected_codeword_o = polar_transform(best_u);
    u_hat_o = best_u;

    info_cnt = 0;
    data_o = '0;
    for (i = 0; i < N; i++) begin
      if (!FROZEN_MASK[i]) begin
        data_o[info_cnt] = best_u[i];
        info_cnt++;
      end
    end

    err_detected_o = (codeword_i != corrected_codeword_o);
    err_corrected_o = err_detected_o && (best_dist <= 2);
    err_uncorrectable_o = err_detected_o && (best_dist > 2);
  end
endmodule
