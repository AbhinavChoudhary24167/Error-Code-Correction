// Attempt06 hard-macro composition. The two SRAM22 instances remain separate
// hardened macros and together implement one logical 72-bit protected word.
module ecc_sram_256x72_sram22 (
  input  logic        clk,
  input  logic        rstb,
  input  logic        ce,
  input  logic        we,
  input  logic [7:0]  addr,
  input  logic [63:0] payload_in,
  input  logic [71:0] qualification_fault_mask,
  output logic [63:0] payload_out,
  output logic        correction_applied,
  output logic        detected_uncorrectable
);
  logic [71:0] encoded_word;
  logic [63:0] data_dout;
  logic [7:0]  ecc_dout;
  logic [71:0] stored_word;
  logic [71:0] decoder_word;

  hsiao_secded_72_64_v1_encoder u_encoder (
    .data(payload_in),
    .codeword(encoded_word)
  );

  sram22_256x64m4w8 u_data (
    .clk(clk),
    .rstb(rstb),
    .ce(ce),
    .we(we),
    .wmask(8'hff),
    .addr(addr),
    .din(encoded_word[63:0]),
    .dout(data_dout)
  );

  sram22_256x8m8w1 u_ecc (
    .clk(clk),
    .rstb(rstb),
    .ce(ce),
    .we(we),
    .wmask(8'hff),
    .addr(addr),
    .din(encoded_word[71:64]),
    .dout(ecc_dout)
  );

  assign stored_word = {ecc_dout, data_dout};
  assign decoder_word = stored_word ^ qualification_fault_mask;

  hsiao_secded_72_64_v2_algorithmic_decoder u_decoder (
    .word(decoder_word),
    .data_out(payload_out),
    .correction_applied(correction_applied),
    .detected_uncorrectable(detected_uncorrectable)
  );
endmodule

// Physical E0 top. Fault injection is tied off so it synthesizes away; the
// qualification port above exists only to exercise the stored-codeword path.
module e0_sram22_top (
  input  logic        clk,
  input  logic        rstb,
  input  logic        ce,
  input  logic        we,
  input  logic [7:0]  addr,
  input  logic [63:0] payload_in,
  output logic [63:0] payload_out,
  output logic        correction_applied,
  output logic        detected_uncorrectable
);
  ecc_sram_256x72_sram22 u_protected_memory (
    .clk(clk),
    .rstb(rstb),
    .ce(ce),
    .we(we),
    .addr(addr),
    .payload_in(payload_in),
    .qualification_fault_mask(72'b0),
    .payload_out(payload_out),
    .correction_applied(correction_applied),
    .detected_uncorrectable(detected_uncorrectable)
  );
endmodule
