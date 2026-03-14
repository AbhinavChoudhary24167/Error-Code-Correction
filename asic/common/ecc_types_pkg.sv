//------------------------------------------------------------------------------
// File: asic/common/ecc_types_pkg.sv
// Purpose: Shared ECC/SRAM type and sizing helpers for top-level SRAM wrappers.
// Notes  : Keeps wrapper interfaces and SRAM organization consistent.
//------------------------------------------------------------------------------
package ecc_types_pkg;
  typedef enum logic [2:0] {
    ECC_SECDED      = 3'd0,
    ECC_SECDAEC     = 3'd1,
    ECC_TAEC        = 3'd2,
    ECC_BCH63       = 3'd3,
    ECC_POLAR_64_32 = 3'd4,
    ECC_POLAR_64_48 = 3'd5,
    ECC_POLAR_128_96= 3'd6
  } ecc_scheme_e;

  function automatic int hamming_p_bits(input int data_w);
    int p;
    begin
      p = 0;
      while ((1 << p) < (data_w + p + 1)) p++;
      return p;
    end
  endfunction
endpackage
