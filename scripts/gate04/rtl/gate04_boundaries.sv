// Gate 04 experiment-only boundaries. Production RTL is instantiated without
// modification. Encoder and decoder paths are independent so synthesis cannot
// collapse an encode/decode composition into a payload wire.

module gate04_secded_comb_72_64 (
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
  logic        valid_q;
  logic [63:0] enc_data_q;
  logic [71:0] dec_codeword_q;
  logic [71:0] enc_codeword_d;
  logic [63:0] dec_data_d;
  logic [71:0] dec_corrected_codeword_unused;
  logic dec_detected_d, dec_corrected_d, dec_uncorrectable_d;

  gate03r_secded_baseline_encoder u_encoder (
    .data_i(enc_data_q), .codeword_o(enc_codeword_d)
  );
  gate03r_secded_baseline_decoder u_decoder (
    .codeword_i(dec_codeword_q), .data_o(dec_data_d),
    .corrected_codeword_o(dec_corrected_codeword_unused),
    .err_detected_o(dec_detected_d), .err_corrected_o(dec_corrected_d),
    .err_uncorrectable_o(dec_uncorrectable_d)
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
      dec_detected_o <= dec_detected_d;
      dec_corrected_o <= dec_corrected_d;
      dec_uncorrectable_o <= dec_uncorrectable_d;
    end
  end
endmodule

module gate04_secded_pipe_72_64 (
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
  logic        valid_q;
  logic [63:0] enc_data_q;
  logic [71:0] dec_codeword_q;
  logic enc_core_valid, dec_core_valid;
  logic [71:0] enc_codeword_d;
  logic [63:0] dec_data_d;
  logic [71:0] dec_corrected_codeword_unused;
  logic dec_detected_d, dec_corrected_d, dec_uncorrectable_d;

  secded_pipelined_72_64_v1_encoder u_encoder (
    .clk_i(clk_i), .valid_i(valid_q), .data_i(enc_data_q),
    .valid_o(enc_core_valid), .codeword_o(enc_codeword_d)
  );
  secded_pipelined_72_64_v1_decoder u_decoder (
    .clk_i(clk_i), .valid_i(valid_q), .codeword_i(dec_codeword_q),
    .valid_o(dec_core_valid), .data_o(dec_data_d),
    .corrected_codeword_o(dec_corrected_codeword_unused),
    .err_detected_o(dec_detected_d), .err_corrected_o(dec_corrected_d),
    .err_uncorrectable_o(dec_uncorrectable_d)
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
      enc_valid_o <= enc_core_valid;
      enc_codeword_o <= enc_codeword_d;
      dec_valid_o <= dec_core_valid;
      dec_data_o <= dec_data_d;
      dec_codeword_echo_o <= dec_codeword_q;
      dec_detected_o <= dec_detected_d;
      dec_corrected_o <= dec_corrected_d;
      dec_uncorrectable_o <= dec_uncorrectable_d;
    end
  end
endmodule

module gate04_hsiao_72_64 (
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
  logic        valid_q;
  logic [63:0] enc_data_q;
  logic [71:0] dec_codeword_q;
  logic [71:0] enc_codeword_d;
  logic [63:0] dec_data_d;
  logic dec_corrected_d, dec_uncorrectable_d;

  hsiao_secded_72_64_v1_encoder u_encoder (
    .data(enc_data_q), .codeword(enc_codeword_d)
  );
  hsiao_secded_72_64_v1_decoder u_decoder (
    .word(dec_codeword_q), .data_out(dec_data_d),
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

module gate04_bch_78_64 (
  input  logic        clk_i,
  input  logic        rst_ni,
  input  logic        valid_i,
  input  logic [63:0] enc_data_i,
  input  logic [77:0] dec_codeword_i,
  output logic        enc_valid_o,
  output logic [77:0] enc_codeword_o,
  output logic        dec_valid_o,
  output logic [63:0] dec_data_o,
  output logic [77:0] dec_codeword_echo_o,
  output logic        dec_detected_o,
  output logic        dec_corrected_o,
  output logic        dec_uncorrectable_o
);
  logic        valid_q;
  logic [63:0] enc_data_q;
  logic [77:0] dec_codeword_q;
  logic [77:0] enc_codeword_d;
  logic [63:0] dec_data_d;
  logic [77:0] corrected_codeword_unused, correction_mask_unused;
  logic [27:0] syndrome_unused;
  logic dec_detected_d, dec_corrected_d, dec_uncorrectable_d;

  bch_78_64_t2_v1_encoder u_encoder (
    .data_i(enc_data_q), .codeword_o(enc_codeword_d)
  );
  bch_78_64_t2_v1_decoder u_decoder (
    .codeword_i(dec_codeword_q), .data_o(dec_data_d),
    .corrected_codeword_o(corrected_codeword_unused),
    .syndrome_o(syndrome_unused), .correction_mask_o(correction_mask_unused),
    .err_detected_o(dec_detected_d), .err_corrected_o(dec_corrected_d),
    .err_uncorrectable_o(dec_uncorrectable_d)
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
      dec_detected_o <= dec_detected_d;
      dec_corrected_o <= dec_corrected_d;
      dec_uncorrectable_o <= dec_uncorrectable_d;
    end
  end
endmodule

module gate04_boundary_ref_72_64 (
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
  always_ff @(posedge clk_i) begin
    if (!rst_ni) begin
      valid_q <= 1'b0; enc_data_q <= '0; dec_codeword_q <= '0;
      enc_valid_o <= 1'b0; enc_codeword_o <= '0;
      dec_valid_o <= 1'b0; dec_data_o <= '0; dec_codeword_echo_o <= '0;
      dec_detected_o <= 1'b0; dec_corrected_o <= 1'b0;
      dec_uncorrectable_o <= 1'b0;
    end else begin
      valid_q <= valid_i; enc_data_q <= enc_data_i; dec_codeword_q <= dec_codeword_i;
      enc_valid_o <= valid_q; enc_codeword_o <= {enc_data_q[7:0], enc_data_q};
      dec_valid_o <= valid_q; dec_data_o <= dec_codeword_q[63:0];
      dec_codeword_echo_o <= dec_codeword_q;
      dec_detected_o <= 1'b0; dec_corrected_o <= 1'b0;
      dec_uncorrectable_o <= 1'b0;
    end
  end
endmodule

module gate04_boundary_ref_78_64 (
  input  logic        clk_i,
  input  logic        rst_ni,
  input  logic        valid_i,
  input  logic [63:0] enc_data_i,
  input  logic [77:0] dec_codeword_i,
  output logic        enc_valid_o,
  output logic [77:0] enc_codeword_o,
  output logic        dec_valid_o,
  output logic [63:0] dec_data_o,
  output logic [77:0] dec_codeword_echo_o,
  output logic        dec_detected_o,
  output logic        dec_corrected_o,
  output logic        dec_uncorrectable_o
);
  logic valid_q;
  logic [63:0] enc_data_q;
  logic [77:0] dec_codeword_q;
  always_ff @(posedge clk_i) begin
    if (!rst_ni) begin
      valid_q <= 1'b0; enc_data_q <= '0; dec_codeword_q <= '0;
      enc_valid_o <= 1'b0; enc_codeword_o <= '0;
      dec_valid_o <= 1'b0; dec_data_o <= '0; dec_codeword_echo_o <= '0;
      dec_detected_o <= 1'b0; dec_corrected_o <= 1'b0;
      dec_uncorrectable_o <= 1'b0;
    end else begin
      valid_q <= valid_i; enc_data_q <= enc_data_i; dec_codeword_q <= dec_codeword_i;
      enc_valid_o <= valid_q; enc_codeword_o <= {enc_data_q[13:0], enc_data_q};
      dec_valid_o <= valid_q; dec_data_o <= dec_codeword_q[63:0];
      dec_codeword_echo_o <= dec_codeword_q;
      dec_detected_o <= 1'b0; dec_corrected_o <= 1'b0;
      dec_uncorrectable_o <= 1'b0;
    end
  end
endmodule
