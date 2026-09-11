// Additive boundary with the exact Revision-2 Hsiao transaction contract.
// Only the decoder implementation identity differs from the qualified baseline.
module breadth_hsiao_hierarchical_72_64 (
  input  logic        clk_i,
  input  logic        rst_ni,
  input  logic        valid_i,
  input  logic [63:0] enc_data_i,
  input  logic [71:0] dec_codeword_i,
  output logic        enc_valid_o,
  output logic [71:0] enc_codeword_o,
  output logic        dec_valid_o,
  output logic [63:0] dec_data_o,
  output logic [71:0] dec_codeword_echo_o,
  output logic        dec_detected_o,
  output logic        dec_corrected_o,
  output logic        dec_uncorrectable_o
);
  logic valid_q;
  logic [63:0] enc_data_q;
  logic [71:0] dec_codeword_q;
  logic [71:0] enc_codeword_d;
  logic [63:0] dec_data_d;
  logic dec_corrected_d;
  logic dec_uncorrectable_d;

  hsiao_secded_72_64_v1_encoder u_encoder(
    .data(enc_data_q),
    .codeword(enc_codeword_d)
  );

  hsiao_secded_72_64_v3_hierarchical_decoder u_decoder(
    .word(dec_codeword_q),
    .data_out(dec_data_d),
    .correction_applied(dec_corrected_d),
    .detected_uncorrectable(dec_uncorrectable_d)
  );

  always_ff @(posedge clk_i) begin
    if (!rst_ni) begin
      valid_q <= 1'b0;
      enc_data_q <= '0;
      dec_codeword_q <= '0;
      enc_valid_o <= 1'b0;
      enc_codeword_o <= '0;
      dec_valid_o <= 1'b0;
      dec_data_o <= '0;
      dec_codeword_echo_o <= '0;
      dec_detected_o <= 1'b0;
      dec_corrected_o <= 1'b0;
      dec_uncorrectable_o <= 1'b0;
    end else begin
      valid_q <= valid_i;
      enc_data_q <= enc_data_i;
      dec_codeword_q <= dec_codeword_i;
      enc_valid_o <= valid_q;
      enc_codeword_o <= enc_codeword_d;
      dec_valid_o <= valid_q;
      dec_data_o <= dec_data_d;
      dec_codeword_echo_o <= dec_codeword_q;
      dec_detected_o <= dec_corrected_d | dec_uncorrectable_d;
      dec_corrected_o <= dec_corrected_d;
      dec_uncorrectable_o <= dec_uncorrectable_d;
    end
  end
endmodule
