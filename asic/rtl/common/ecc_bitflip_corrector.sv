//------------------------------------------------------------------------------
// File: ecc_bitflip_corrector.sv
// Purpose: Generic XOR correction-mask applicator.
// Scheme: Common/shared infrastructure
// Inputs/Outputs: in_word xor correction_mask -> out_word
// Assumptions: correction_mask has same width as data.
// Synthesizability: Yes.
//------------------------------------------------------------------------------
module ecc_bitflip_corrector #(
  parameter int W = 72
) (
  input  logic [W-1:0] in_word,
  input  logic [W-1:0] correction_mask,
  output logic [W-1:0] out_word
);
  always_comb begin
    out_word = in_word ^ correction_mask;
  end
endmodule
