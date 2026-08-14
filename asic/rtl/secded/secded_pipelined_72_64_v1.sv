// Exact-identity, full-throughput pipelined implementation of the repository's
// conventional extended-Hamming SECDED(72,64) code. Native bit ordering is
// identical to secded_codec.sv: positional bits 1..71 followed by overall parity.
module secded_pipelined_72_64_v1_encoder (
  input  logic        clk_i,
  input  logic        valid_i,
  input  logic [63:0] data_i,
  output logic        valid_o,
  output logic [71:0] codeword_o
);
  logic [70:0] positional_d, positional_q;
  logic [6:0] parity_d;
  logic [8:0] parity_group [0:6];
  logic stage1_valid_q, stage2_valid_q;
  logic [71:0] stage2_codeword_q;
  integer data_index, position, parity_index, group_index, group_offset;

  function automatic logic is_power_of_two(input integer value);
    begin
      is_power_of_two = (value > 0) && ((value & (value - 1)) == 0);
    end
  endfunction

  // Explicit input-only sensitivity prevents event-simulator re-entry on the
  // factored-loop temporaries while retaining a purely combinational stage.
  always @(data_i) begin
    positional_d = '0;
    parity_d = '0;
    for (parity_index = 0; parity_index < 7; parity_index = parity_index + 1)
      parity_group[parity_index] = '0;

    data_index = 0;
    for (position = 1; position <= 71; position = position + 1) begin
      if (!is_power_of_two(position)) begin
        positional_d[position-1] = data_i[data_index];
        data_index = data_index + 1;
      end
    end

    // Nine bounded groups per parity equation make the first pipeline phase
    // explicit without changing the frozen parity-check construction.
    for (parity_index = 0; parity_index < 7; parity_index = parity_index + 1) begin
      for (group_index = 0; group_index < 9; group_index = group_index + 1) begin
        for (group_offset = 0; group_offset < 8; group_offset = group_offset + 1) begin
          position = group_index * 8 + group_offset + 1;
          if ((position <= 71) && ((position & (1 << parity_index)) != 0))
            parity_group[parity_index][group_index] =
              parity_group[parity_index][group_index] ^ positional_d[position-1];
        end
      end
      parity_d[parity_index] = ^parity_group[parity_index];
      positional_d[(1 << parity_index)-1] = parity_d[parity_index];
    end
  end

  always_ff @(posedge clk_i) begin
    positional_q <= positional_d;
    stage1_valid_q <= valid_i;
    stage2_codeword_q <= {^positional_q, positional_q};
    stage2_valid_q <= stage1_valid_q;
  end

  assign codeword_o = stage2_codeword_q;
  assign valid_o = stage2_valid_q;
endmodule

module secded_pipelined_72_64_v1_decoder (
  input  logic        clk_i,
  input  logic        valid_i,
  input  logic [71:0] codeword_i,
  output logic        valid_o,
  output logic [63:0] data_o,
  output logic [71:0] corrected_codeword_o,
  output logic        err_detected_o,
  output logic        err_corrected_o,
  output logic        err_uncorrectable_o
);
  logic [6:0] syndrome_d, syndrome_q;
  logic [8:0] syndrome_group [0:6];
  logic overall_mismatch_d, overall_mismatch_q;
  logic [71:0] received_q;
  logic stage1_valid_q, stage2_valid_q;
  logic [71:0] correction_mask_d, corrected_d, corrected_q;
  logic [63:0] data_d, data_q;
  logic detected_d, corrected_flag_d, uncorrectable_d;
  logic detected_q, corrected_flag_q, uncorrectable_q;
  integer position, parity_index, group_index, group_offset, data_index;
  integer unsigned error_position;

  function automatic logic is_power_of_two(input integer value);
    begin
      is_power_of_two = (value > 0) && ((value & (value - 1)) == 0);
    end
  endfunction

  always @(codeword_i) begin
    syndrome_d = '0;
    for (parity_index = 0; parity_index < 7; parity_index = parity_index + 1)
      syndrome_group[parity_index] = '0;
    for (parity_index = 0; parity_index < 7; parity_index = parity_index + 1) begin
      for (group_index = 0; group_index < 9; group_index = group_index + 1) begin
        for (group_offset = 0; group_offset < 8; group_offset = group_offset + 1) begin
          position = group_index * 8 + group_offset + 1;
          if ((position <= 71) && ((position & (1 << parity_index)) != 0))
            syndrome_group[parity_index][group_index] =
              syndrome_group[parity_index][group_index] ^ codeword_i[position-1];
        end
      end
      syndrome_d[parity_index] = ^syndrome_group[parity_index];
    end
    overall_mismatch_d = (^codeword_i[70:0]) != codeword_i[71];
  end

  always @(syndrome_q or overall_mismatch_q or received_q) begin
    correction_mask_d = '0;
    detected_d = (syndrome_q != '0) || overall_mismatch_q;
    corrected_flag_d = 1'b0;
    uncorrectable_d = 1'b0;
    error_position = syndrome_q;

    if ((syndrome_q != '0) && overall_mismatch_q) begin
      if ((error_position >= 1) && (error_position <= 71)) begin
        correction_mask_d[error_position-1] = 1'b1;
        corrected_flag_d = 1'b1;
      end
    end else if ((syndrome_q == '0) && overall_mismatch_q) begin
      correction_mask_d[71] = 1'b1;
      corrected_flag_d = 1'b1;
    end else if ((syndrome_q != '0) && !overall_mismatch_q) begin
      uncorrectable_d = 1'b1;
    end

    corrected_d = received_q ^ correction_mask_d;
    data_d = '0;
    data_index = 0;
    for (position = 1; position <= 71; position = position + 1) begin
      if (!is_power_of_two(position)) begin
        data_d[data_index] = corrected_d[position-1];
        data_index = data_index + 1;
      end
    end
  end

  always_ff @(posedge clk_i) begin
    received_q <= codeword_i;
    syndrome_q <= syndrome_d;
    overall_mismatch_q <= overall_mismatch_d;
    stage1_valid_q <= valid_i;

    corrected_q <= corrected_d;
    data_q <= data_d;
    detected_q <= detected_d;
    corrected_flag_q <= corrected_flag_d;
    uncorrectable_q <= uncorrectable_d;
    stage2_valid_q <= stage1_valid_q;
  end

  assign valid_o = stage2_valid_q;
  assign data_o = data_q;
  assign corrected_codeword_o = corrected_q;
  assign err_detected_o = detected_q;
  assign err_corrected_o = corrected_flag_q;
  assign err_uncorrectable_o = uncorrectable_q;
endmodule
