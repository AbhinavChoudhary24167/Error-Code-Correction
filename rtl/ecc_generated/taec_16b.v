// Auto-generated Verilog-2001 ECC block: taec 16b
`timescale 1ns/1ps

module taec_16b_sram(
  clk, rst, we, re, addr, wcode, rcode
);
  parameter ADDR_W = 6;
  parameter CODE_W = 22;
  input clk;
  input rst;
  input we;
  input re;
  input [ADDR_W-1:0] addr;
  input [CODE_W-1:0] wcode;
  output reg [CODE_W-1:0] rcode;

  reg [CODE_W-1:0] mem[(1<<ADDR_W)-1:0];
  integer mi;
  always @(posedge clk) begin
    if (rst) begin
      for (mi = 0; mi < (1<<ADDR_W); mi = mi + 1)
        mem[mi] <= {CODE_W{1'b0}};
      rcode <= {CODE_W{1'b0}};
    end else begin
      if (we)
        mem[addr] <= wcode;
      if (re)
        rcode <= mem[addr];
    end
  end
endmodule

module taec_16b_encoder(
  data_i, codeword_o
);
  input  [15:0] data_i;
  output reg [21:0] codeword_o;

  integer i;
  integer d_idx;
  integer c_idx;
  reg [4:0] parity;
  reg overall;
  reg [21:0] code_tmp;
  always @(*) begin
    parity = {5{1'b0}};
    code_tmp = {22{1'b0}};
    d_idx = 0;
    for (c_idx = 1; c_idx <= 21; c_idx = c_idx + 1) begin
      if ((c_idx & (c_idx - 1)) != 0) begin
        code_tmp[c_idx-1] = data_i[d_idx];
        d_idx = d_idx + 1;
      end
    end
    for (i = 0; i < 5; i = i + 1) begin
      parity[i] = 1'b0;
      for (c_idx = 1; c_idx <= 21; c_idx = c_idx + 1) begin
        if ((c_idx & (1 << i)) != 0)
          parity[i] = parity[i] ^ code_tmp[c_idx-1];
      end
      code_tmp[(1 << i)-1] = parity[i];
    end
    overall = 1'b0;
    for (c_idx = 0; c_idx < 21; c_idx = c_idx + 1)
      overall = overall ^ code_tmp[c_idx];
    code_tmp[21] = overall;
    codeword_o = code_tmp;
  end
endmodule

module taec_16b_decoder(
  codeword_i, inject_syndrome_en, injected_syndrome,
  data_o, corrected_codeword_o, syndrome_out,
  error_detected, error_corrected, uncorrectable_error, error_position
);
  input  [21:0] codeword_i;
  input  inject_syndrome_en;
  input  [4:0] injected_syndrome;
  output reg [15:0] data_o;
  output reg [21:0] corrected_codeword_o;
  output reg [4:0] syndrome_out;
  output reg error_detected;
  output reg error_corrected;
  output reg uncorrectable_error;
  output reg [4:0] error_position;

  integer i;
  integer c_idx;
  integer d_idx;
  integer pos;
  reg [4:0] syndrome_raw;
  reg overall;
  reg [21:0] cw_work;
  reg found_trip;
  reg [4:0] tri_syn;
  always @(*) begin
    cw_work = codeword_i;
    syndrome_raw = {5{1'b0}};
    for (i = 0; i < 5; i = i + 1)
      for (c_idx = 1; c_idx <= 21; c_idx = c_idx + 1)
        if ((c_idx & (1 << i)) != 0)
          syndrome_raw[i] = syndrome_raw[i] ^ cw_work[c_idx-1];

    overall = 1'b0;
    for (c_idx = 0; c_idx < 22; c_idx = c_idx + 1)
      overall = overall ^ cw_work[c_idx];

    syndrome_out = inject_syndrome_en ? (syndrome_raw ^ injected_syndrome[4:0]) : syndrome_raw;
    error_detected = (syndrome_out != {5{1'b0}}) || overall;
    error_corrected = 1'b0;
    uncorrectable_error = 1'b0;
    error_position = {5{1'b0}};

    if ((syndrome_out != {5{1'b0}}) && overall) begin
      if (syndrome_out <= 21) begin
        cw_work[syndrome_out-1] = ~cw_work[syndrome_out-1];
        error_corrected = 1'b1;
        error_position = syndrome_out[4:0];
      end
    end else if ((syndrome_out != {5{1'b0}}) && !overall) begin
      found_trip = 1'b0;
      for (pos = 1; pos < 20; pos = pos + 1) begin
        tri_syn = pos ^ (pos+1) ^ (pos+2);
        if (!found_trip && (syndrome_out == tri_syn[4:0])) begin
          cw_work[pos-1] = ~cw_work[pos-1];
          cw_work[pos]   = ~cw_work[pos];
          cw_work[pos+1] = ~cw_work[pos+1];
          error_corrected = 1'b1;
          found_trip = 1'b1;
          error_position = pos[4:0];
        end
      end
      if (!found_trip)
        uncorrectable_error = 1'b1;
    end else if ((syndrome_out == {5{1'b0}}) && overall) begin
      cw_work[21] = ~cw_work[21];
      error_corrected = 1'b1;
      error_position = 22[4:0];
    end

    corrected_codeword_o = cw_work;
    data_o = {16{1'b0}};
    d_idx = 0;
    for (c_idx = 1; c_idx <= 21; c_idx = c_idx + 1)
      if ((c_idx & (c_idx - 1)) != 0) begin
        data_o[d_idx] = cw_work[c_idx-1];
        d_idx = d_idx + 1;
      end
  end
endmodule

module taec_16b_top(
  clk, rst, write_en, read_en, addr, data_in, data_out,
  inject_error_en, inject_error_mask, inject_syndrome_en, injected_syndrome,
  syndrome_out, error_detected, error_corrected, uncorrectable_error, error_position
);
  parameter ADDR_W = 6;
  input clk;
  input rst;
  input write_en;
  input read_en;
  input [ADDR_W-1:0] addr;
  input [15:0] data_in;
  output [15:0] data_out;
  input inject_error_en;
  input [21:0] inject_error_mask;
  input inject_syndrome_en;
  input [4:0] injected_syndrome;
  output [4:0] syndrome_out;
  output error_detected;
  output error_corrected;
  output uncorrectable_error;
  output [4:0] error_position;

  wire [21:0] enc_codeword;
  wire [21:0] mem_r;
  wire [21:0] dec_in;
  wire [21:0] corr_cw;

  taec_16b_encoder u_encoder(.data_i(data_in), .codeword_o(enc_codeword));
  taec_16b_sram #(.ADDR_W(ADDR_W), .CODE_W(22)) u_sram(
    .clk(clk), .rst(rst), .we(write_en), .re(read_en), .addr(addr), .wcode(enc_codeword), .rcode(mem_r)
  );

  assign dec_in = inject_error_en ? (mem_r ^ inject_error_mask) : mem_r;

  taec_16b_decoder u_decoder(
    .codeword_i(dec_in), .inject_syndrome_en(inject_syndrome_en), .injected_syndrome(injected_syndrome),
    .data_o(data_out), .corrected_codeword_o(corr_cw), .syndrome_out(syndrome_out),
    .error_detected(error_detected), .error_corrected(error_corrected), .uncorrectable_error(uncorrectable_error),
    .error_position(error_position)
  );
endmodule
