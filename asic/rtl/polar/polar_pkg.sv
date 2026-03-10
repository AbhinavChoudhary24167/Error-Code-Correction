//------------------------------------------------------------------------------
// File: polar_pkg.sv
// Purpose: Frozen-set helpers for predefined Polar configurations.
// Scheme: Polar
// Assumptions: Reliability ordering is simplified, deterministic and documented.
// Synthesizability: Yes.
//------------------------------------------------------------------------------
package polar_pkg;
  function automatic logic [127:0] default_frozen_mask(input int unsigned N, input int unsigned K);
    logic [127:0] m;
    int i;
    begin
      m = '0;
      // Simplified reliability order assumption: keep highest indices as info bits.
      for (i = 0; i < N-K; i++) m[i] = 1'b1; // 1 => frozen
      return m;
    end
  endfunction
endpackage
