// Gate 03R characterization-only shells.  The baseline logic is a literal
// package-free statement of asic/rtl/secded/secded_codec.sv for older Yosys.
module gate03r_secded_baseline_encoder(
  input logic [63:0] data_i,
  output logic [71:0] codeword_o
);
  logic [70:0] positional;
  logic parity;
  integer data_index, position, parity_index;
  function automatic logic is_power_of_two(input integer value);
    begin is_power_of_two = value > 0 && ((value & (value - 1)) == 0); end
  endfunction
  always @(data_i) begin
    positional = '0; data_index = 0;
    for (position = 1; position <= 71; position = position + 1)
      if (!is_power_of_two(position)) begin
        positional[position-1] = data_i[data_index]; data_index = data_index + 1;
      end
    for (parity_index = 0; parity_index < 7; parity_index = parity_index + 1) begin
      parity = 0;
      for (position = 1; position <= 71; position = position + 1)
        if ((position & (1 << parity_index)) != 0) parity = parity ^ positional[position-1];
      positional[(1 << parity_index)-1] = parity;
    end
    codeword_o = {^positional, positional};
  end
endmodule

module gate03r_secded_baseline_decoder(
  input logic [71:0] codeword_i,
  output logic [63:0] data_o,
  output logic [71:0] corrected_codeword_o,
  output logic err_detected_o,
  output logic err_corrected_o,
  output logic err_uncorrectable_o
);
  logic [6:0] syndrome;
  logic overall_mismatch;
  logic [71:0] mask;
  integer position, parity_index, data_index;
  integer unsigned error_position;
  function automatic logic is_power_of_two(input integer value);
    begin is_power_of_two = value > 0 && ((value & (value - 1)) == 0); end
  endfunction
  always @(codeword_i) begin
    syndrome = '0;
    for (parity_index = 0; parity_index < 7; parity_index = parity_index + 1)
      for (position = 1; position <= 71; position = position + 1)
        if ((position & (1 << parity_index)) != 0)
          syndrome[parity_index] = syndrome[parity_index] ^ codeword_i[position-1];
    overall_mismatch = (^codeword_i[70:0]) != codeword_i[71];
    error_position = syndrome; mask = '0;
    err_detected_o = syndrome != 0 || overall_mismatch;
    err_corrected_o = 0; err_uncorrectable_o = 0;
    if (syndrome != 0 && overall_mismatch && error_position >= 1 && error_position <= 71) begin
      mask[error_position-1] = 1; err_corrected_o = 1;
    end else if (syndrome == 0 && overall_mismatch) begin
      mask[71] = 1; err_corrected_o = 1;
    end else if (syndrome != 0 && !overall_mismatch) begin
      err_uncorrectable_o = 1;
    end
    corrected_codeword_o = codeword_i ^ mask;
    data_o = '0; data_index = 0;
    for (position = 1; position <= 71; position = position + 1)
      if (!is_power_of_two(position)) begin
        data_o[data_index] = corrected_codeword_o[position-1]; data_index = data_index + 1;
      end
  end
endmodule

module gate03r_secded_baseline_combined(
  input logic [63:0] data_i,
  output logic [63:0] data_o,
  output logic [71:0] codeword_o,
  output logic detected_o, corrected_o, uncorrectable_o
);
  logic [71:0] corrected_codeword;
  gate03r_secded_baseline_encoder encoder(.data_i(data_i), .codeword_o(codeword_o));
  gate03r_secded_baseline_decoder decoder(
    .codeword_i(codeword_o), .data_o(data_o), .corrected_codeword_o(corrected_codeword),
    .err_detected_o(detected_o), .err_corrected_o(corrected_o),
    .err_uncorrectable_o(uncorrectable_o)
  );
endmodule

module gate03r_secded_pipelined_combined(
  input logic clk_i, input logic valid_i, input logic [63:0] data_i,
  output logic valid_o, output logic [63:0] data_o,
  output logic [71:0] codeword_o, output logic detected_o,
  output logic corrected_o, output logic uncorrectable_o
);
  logic encoder_valid;
  logic [71:0] corrected_codeword;
  secded_pipelined_72_64_v1_encoder encoder(
    .clk_i(clk_i), .valid_i(valid_i), .data_i(data_i),
    .valid_o(encoder_valid), .codeword_o(codeword_o)
  );
  secded_pipelined_72_64_v1_decoder decoder(
    .clk_i(clk_i), .valid_i(encoder_valid), .codeword_i(codeword_o),
    .valid_o(valid_o), .data_o(data_o), .corrected_codeword_o(corrected_codeword),
    .err_detected_o(detected_o), .err_corrected_o(corrected_o),
    .err_uncorrectable_o(uncorrectable_o)
  );
endmodule

module gate03r_bch_combined(
  input logic [63:0] data_i,
  output logic [63:0] data_o,
  output logic [77:0] codeword_o,
  output logic detected_o, corrected_o, uncorrectable_o
);
  logic [77:0] corrected_codeword, correction_mask;
  logic [27:0] syndrome;
  bch_78_64_t2_v1_encoder encoder(.data_i(data_i), .codeword_o(codeword_o));
  bch_78_64_t2_v1_decoder decoder(
    .codeword_i(codeword_o), .data_o(data_o), .corrected_codeword_o(corrected_codeword),
    .syndrome_o(syndrome), .correction_mask_o(correction_mask),
    .err_detected_o(detected_o), .err_corrected_o(corrected_o),
    .err_uncorrectable_o(uncorrectable_o)
  );
endmodule
