// Clean Gate 03R characterization shells. Fault injection is prohibited here.

module gate03r_bch_encoder_shell (
  input logic clk, input logic valid_i, input logic [63:0] data_i,
  output logic valid_o, output logic [77:0] codeword_o
);
  logic [63:0] data_q;
  logic valid_q;
  logic [77:0] codeword_d;
  bch_78_64_t2_v1_encoder u_encoder(.data_i(data_q), .codeword_o(codeword_d));
  always_ff @(posedge clk) begin
    data_q <= data_i;
    codeword_o <= codeword_d;
    valid_q <= valid_i;
    valid_o <= valid_q;
  end
endmodule

module gate03r_bch_decoder_shell (
  input logic clk, input logic valid_i, input logic [77:0] codeword_i,
  output logic valid_o, output logic [63:0] data_o,
  output logic [77:0] corrected_codeword_o,
  output logic detected_o, output logic corrected_o, output logic uncorrectable_o
);
  logic [77:0] codeword_q, corrected_d, correction_mask;
  logic [63:0] data_d;
  logic [27:0] syndrome;
  logic detected_d, corrected_flag_d, uncorrectable_d, valid_q;
  bch_78_64_t2_v1_decoder u_decoder(
    .codeword_i(codeword_q), .data_o(data_d), .corrected_codeword_o(corrected_d),
    .syndrome_o(syndrome), .correction_mask_o(correction_mask),
    .err_detected_o(detected_d), .err_corrected_o(corrected_flag_d),
    .err_uncorrectable_o(uncorrectable_d));
  always_ff @(posedge clk) begin
    codeword_q <= codeword_i;
    data_o <= data_d;
    corrected_codeword_o <= corrected_d;
    detected_o <= detected_d;
    corrected_o <= corrected_flag_d;
    uncorrectable_o <= uncorrectable_d;
    valid_q <= valid_i;
    valid_o <= valid_q;
  end
endmodule

