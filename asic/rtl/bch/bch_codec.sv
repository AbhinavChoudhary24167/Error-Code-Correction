//------------------------------------------------------------------------------
// File: bch_codec.sv
// Purpose: Binary BCH codec (bounded t<=2 decoder via exhaustive candidate
//          search on valid codeword remainder check).
// Scheme: BCH (n=63 default)
// Assumptions: Systematic encoder using generator polynomial G_POLY.
//              Decoder is intentionally bounded to <=2 bit corrections.
// Synthesizability: Yes, but decoder area is high due to exhaustive search.
//------------------------------------------------------------------------------
module bch_encoder #(
  parameter int N = 63,
  parameter int K = 51,
  parameter int R = N-K,
  parameter logic [R:0] G_POLY = 13'b1_000111101011 // degree-12 example
) (
  input  logic [K-1:0] data_i,
  output logic [N-1:0] codeword_o
);
  int i, j;
  logic [N-1:0] work;

  always_comb begin
    work = '0;
    work[N-1 -: K] = data_i;

    for (i = N-1; i >= R; i--) begin
      if (work[i]) begin
        for (j = 0; j <= R; j++) begin
          work[i-j] ^= G_POLY[R-j];
        end
      end
    end

    codeword_o = '0;
    codeword_o[N-1 -: K] = data_i;
    codeword_o[R-1:0] = work[R-1:0];
  end
endmodule

module bch_decoder #(
  parameter int N = 63,
  parameter int K = 51,
  parameter int R = N-K,
  parameter logic [R:0] G_POLY = 13'b1_000111101011
) (
  input  logic [N-1:0] codeword_i,
  output logic [K-1:0] data_o,
  output logic [N-1:0] corrected_codeword_o,
  output logic [R-1:0] syndrome_o,
  output logic         err_detected_o,
  output logic         err_corrected_o,
  output logic         err_uncorrectable_o
);
  int i, j;
  logic [R-1:0] rem;
  logic [N-1:0] best_cw;
  logic found;

  function automatic logic [R-1:0] calc_remainder(input logic [N-1:0] v);
    logic [N-1:0] w;
    int a, b;
    begin
      w = v;
      for (a = N-1; a >= R; a--) begin
        if (w[a]) begin
          for (b = 0; b <= R; b++) w[a-b] ^= G_POLY[R-b];
        end
      end
      return w[R-1:0];
    end
  endfunction

  always_comb begin
    rem = calc_remainder(codeword_i);
    syndrome_o = rem;
    err_detected_o = (rem != '0);
    err_corrected_o = 1'b0;
    err_uncorrectable_o = 1'b0;
    found = 1'b0;
    best_cw = codeword_i;

    if (rem == '0) begin
      found = 1'b1;
      best_cw = codeword_i;
    end else begin
      // Single-bit search
      for (i = 0; i < N; i++) begin
        logic [N-1:0] c1;
        c1 = codeword_i;
        c1[i] = ~c1[i];
        if (!found && (calc_remainder(c1) == '0)) begin
          found = 1'b1;
          best_cw = c1;
          err_corrected_o = 1'b1;
        end
      end
      // Double-bit search
      for (i = 0; i < N; i++) begin
        for (j = i+1; j < N; j++) begin
          logic [N-1:0] c2;
          c2 = codeword_i;
          c2[i] = ~c2[i];
          c2[j] = ~c2[j];
          if (!found && (calc_remainder(c2) == '0)) begin
            found = 1'b1;
            best_cw = c2;
            err_corrected_o = 1'b1;
          end
        end
      end
    end

    corrected_codeword_o = best_cw;
    data_o = best_cw[N-1 -: K];
    if (err_detected_o && !found) err_uncorrectable_o = 1'b1;
  end
endmodule
