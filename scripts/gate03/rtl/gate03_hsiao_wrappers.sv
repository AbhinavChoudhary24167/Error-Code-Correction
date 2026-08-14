// Gate-03 clean PPA shells.
module gate03_hsiao_encoder_shell (
  input logic clk, input logic valid_i, input logic [63:0] data_i,
  output logic valid_o, output logic [71:0] codeword_o
);
  logic [63:0] data_q;
  logic valid_q;
  logic [71:0] codeword_d;
  hsiao_secded_72_64_v1_encoder u_encoder(.data(data_q), .codeword(codeword_d));
  always_ff @(posedge clk) begin
    data_q <= data_i;
    codeword_o <= codeword_d;
    valid_q <= valid_i;
    valid_o <= valid_q;
  end
endmodule

module gate03_hsiao_decoder_shell (
  input logic clk, input logic valid_i, input logic [71:0] codeword_i,
  output logic valid_o, output logic [63:0] data_o,
  output logic detected_o, output logic corrected_o, output logic uncorrectable_o
);
  logic [71:0] codeword_q;
  logic valid_q;
  logic [63:0] data_d;
  logic corrected_d, uncorrectable_d;
  hsiao_secded_72_64_v1_decoder u_decoder(
    .word(codeword_q), .data_out(data_d), .correction_applied(corrected_d),
    .detected_uncorrectable(uncorrectable_d)
  );
  always_ff @(posedge clk) begin
    codeword_q <= codeword_i;
    data_o <= data_d;
    corrected_o <= corrected_d;
    uncorrectable_o <= uncorrectable_d;
    detected_o <= corrected_d | uncorrectable_d;
    valid_q <= valid_i;
    valid_o <= valid_q;
  end
endmodule

module gate03_hsiao_combined_shell (
  input logic clk, input logic valid_i, input logic [63:0] data_i,
  output logic valid_o, output logic [63:0] data_o,
  output logic detected_o, output logic corrected_o, output logic uncorrectable_o
);
  logic [63:0] data_q, data_d;
  logic valid_q;
  logic [71:0] codeword;
  logic corrected_d, uncorrectable_d;
  hsiao_secded_72_64_v1_encoder u_encoder(.data(data_q), .codeword(codeword));
  hsiao_secded_72_64_v1_decoder u_decoder(
    .word(codeword), .data_out(data_d), .correction_applied(corrected_d),
    .detected_uncorrectable(uncorrectable_d)
  );
  always_ff @(posedge clk) begin
    data_q <= data_i;
    data_o <= data_d;
    corrected_o <= corrected_d;
    uncorrectable_o <= uncorrectable_d;
    detected_o <= corrected_d | uncorrectable_d;
    valid_q <= valid_i;
    valid_o <= valid_q;
  end
endmodule
