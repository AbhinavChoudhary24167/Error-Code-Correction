//------------------------------------------------------------------------------
// File: ecc_pkg.sv
// Purpose: Common ECC package with status types and compile-time helper
//          functions used across ASIC-oriented ECC RTL blocks.
// Scheme: Common/shared infrastructure
// Assumptions: Pure combinational helpers, no simulator-specific extensions.
// Synthesizability: Yes (package functions are constant-time loop constructs).
//------------------------------------------------------------------------------
package ecc_pkg;

  typedef struct packed {
    logic detected;
    logic corrected;
    logic uncorrectable;
    logic adjacent_corrected;
    logic [15:0] error_pos;
  } ecc_status_t;

  function automatic bit is_pow2(input int unsigned v);
    if (v == 0) return 1'b0;
    return ((v & (v-1)) == 0);
  endfunction

  function automatic int unsigned hamming_parity_bits(input int unsigned data_w);
    int unsigned m;
    begin
      m = 1;
      while ((1 << m) < (data_w + m + 1)) m++;
      return m;
    end
  endfunction

  function automatic int unsigned hamming_codeword_wo_overall(input int unsigned data_w);
    int unsigned m;
    begin
      m = hamming_parity_bits(data_w);
      return data_w + m;
    end
  endfunction

  function automatic int unsigned popcount(input logic [255:0] v, input int unsigned w);
    int unsigned i;
    int unsigned c;
    begin
      c = 0;
      for (i = 0; i < w; i++) c += v[i];
      return c;
    end
  endfunction

endpackage
