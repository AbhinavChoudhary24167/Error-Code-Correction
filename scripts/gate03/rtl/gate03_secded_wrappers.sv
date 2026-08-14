// Gate-03 clean PPA shells.
module gate03_secded_encoder_shell (
  input  logic        clk,
  input  logic        valid_i,
  input  logic [63:0] data_i,
  output logic        valid_o,
  output logic [71:0] codeword_o
);
  logic [63:0] data_q;
  logic valid_q;
  logic [71:0] codeword_d;
  secded_encoder #(.DATA_W(64)) u_encoder (
    .data_i(data_q), .codeword_o(codeword_d), .parity_dbg_o()
  );
  always_ff @(posedge clk) begin
    data_q <= data_i;
    codeword_o <= codeword_d;
    valid_q <= valid_i;
    valid_o <= valid_q;
  end
endmodule

module gate03_secded_decoder_shell (
  input  logic        clk,
  input  logic        valid_i,
  input  logic [71:0] codeword_i,
  output logic        valid_o,
  output logic [63:0] data_o,
  output logic        detected_o,
  output logic        corrected_o,
  output logic        uncorrectable_o
);
  logic [71:0] codeword_q, corrected_codeword;
  logic valid_q;
  logic [63:0] data_d;
  logic [6:0] syndrome, error_pos;
  logic overall_mismatch;
  logic [71:0] correction_mask;
  logic detected_d, corrected_d, uncorrectable_d;
  secded_decoder #(.DATA_W(64)) u_decoder (
    .codeword_i(codeword_q), .data_o(data_d),
    .corrected_codeword_o(corrected_codeword), .syndrome_o(syndrome),
    .overall_mismatch_o(overall_mismatch), .err_detected_o(detected_d),
    .err_corrected_o(corrected_d), .err_uncorrectable_o(uncorrectable_d),
    .correction_mask_o(correction_mask), .error_pos_o(error_pos)
  );
  always_ff @(posedge clk) begin
    codeword_q <= codeword_i;
    data_o <= data_d;
    detected_o <= detected_d;
    corrected_o <= corrected_d;
    uncorrectable_o <= uncorrectable_d;
    valid_q <= valid_i;
    valid_o <= valid_q;
  end
endmodule

module gate03_secded_combined_shell (
  input  logic        clk,
  input  logic        valid_i,
  input  logic [63:0] data_i,
  output logic        valid_o,
  output logic [63:0] data_o,
  output logic        detected_o,
  output logic        corrected_o,
  output logic        uncorrectable_o
);
  logic [63:0] data_q, data_d;
  logic valid_q;
  logic [71:0] codeword;
  logic [71:0] corrected_codeword, correction_mask;
  logic [6:0] syndrome, error_pos;
  logic overall_mismatch;
  logic detected_d, corrected_d, uncorrectable_d;
  secded_encoder #(.DATA_W(64)) u_encoder (
    .data_i(data_q), .codeword_o(codeword), .parity_dbg_o()
  );
  secded_decoder #(.DATA_W(64)) u_decoder (
    .codeword_i(codeword), .data_o(data_d),
    .corrected_codeword_o(corrected_codeword), .syndrome_o(syndrome),
    .overall_mismatch_o(overall_mismatch), .err_detected_o(detected_d),
    .err_corrected_o(corrected_d), .err_uncorrectable_o(uncorrectable_d),
    .correction_mask_o(correction_mask), .error_pos_o(error_pos)
  );
  always_ff @(posedge clk) begin
    data_q <= data_i;
    data_o <= data_d;
    detected_o <= detected_d;
    corrected_o <= corrected_d;
    uncorrectable_o <= uncorrectable_d;
    valid_q <= valid_i;
    valid_o <= valid_q;
  end
endmodule

module gate03_combined_wrapper_only_control (
  input  logic        clk,
  input  logic        valid_i,
  input  logic [63:0] data_i,
  output logic        valid_o,
  output logic [63:0] data_o,
  output logic        detected_o,
  output logic        corrected_o,
  output logic        uncorrectable_o
);
  logic [63:0] data_q;
  logic valid_q;
  always_ff @(posedge clk) begin
    data_q <= data_i;
    data_o <= data_q;
    valid_q <= valid_i;
    valid_o <= valid_q;
    detected_o <= 1'b0;
    corrected_o <= 1'b0;
    uncorrectable_o <= 1'b0;
  end
endmodule
