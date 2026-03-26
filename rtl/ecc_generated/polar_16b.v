// Auto-generated Verilog-2001 ECC block: polar 16b
`timescale 1ns/1ps

module polar_16b_sram(
  clk, rst, we, re, addr, wcode, rcode
);
  parameter ADDR_W = 6;
  parameter CODE_W = 32;
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

module polar_16b_encoder(
  data_i, codeword_o
);
  input  [15:0] data_i;
  output reg [31:0] codeword_o;

  integer i;
  integer s;
  integer step;
  integer blk;
  integer off;
  reg [31:0] u;
  reg [31:0] x;
  always @(*) begin
    u = {32{1'b0}};
    for (i = 0; i < 16; i = i + 1)
      u[16+i] = data_i[i];
    x = u;
    step = 1;
    for (s = 0; s < 5; s = s + 1) begin
      for (blk = 0; blk < 32; blk = blk + (step << 1)) begin
        for (off = 0; off < step; off = off + 1)
          x[blk+off] = x[blk+off] ^ x[blk+off+step];
      end
      step = step << 1;
    end
    codeword_o = x;
  end
endmodule

module polar_16b_decoder(
  codeword_i, inject_syndrome_en, injected_syndrome,
  data_o, corrected_codeword_o, syndrome_out,
  error_detected, error_corrected, uncorrectable_error, error_position
);
  input  [31:0] codeword_i;
  input  inject_syndrome_en;
  input  [31:0] injected_syndrome;
  output reg [15:0] data_o;
  output reg [31:0] corrected_codeword_o;
  output reg [31:0] syndrome_out;
  output reg error_detected;
  output reg error_corrected;
  output reg uncorrectable_error;
  output reg [5:0] error_position;

  integer i;
  integer s;
  integer step;
  integer blk;
  integer off;
  integer b;
  reg [31:0] x;
  reg [31:0] u_hat;
  reg [31:0] recoded;
  reg found;
  always @(*) begin
    x = codeword_i;
    syndrome_out = inject_syndrome_en ? injected_syndrome : {32{1'b0}};
    if (inject_syndrome_en)
      x[31:0] = x[31:0] ^ injected_syndrome;

    u_hat = x;
    step = 16;
    for (s = 0; s < 5; s = s + 1) begin
      for (blk = 0; blk < 32; blk = blk + (step << 1)) begin
        for (off = 0; off < step; off = off + 1)
          u_hat[blk+off] = u_hat[blk+off] ^ u_hat[blk+off+step];
      end
      step = step >> 1;
      if (step == 0)
        step = 1;
    end

    data_o = u_hat[31:16];

    recoded = {32{1'b0}};
    for (i = 0; i < 16; i = i + 1)
      recoded[16+i] = data_o[i];
    step = 1;
    for (s = 0; s < 5; s = s + 1) begin
      for (blk = 0; blk < 32; blk = blk + (step << 1)) begin
        for (off = 0; off < step; off = off + 1)
          recoded[blk+off] = recoded[blk+off] ^ recoded[blk+off+step];
      end
      step = step << 1;
    end

    corrected_codeword_o = x;
    error_detected = (recoded != x);
    error_corrected = 1'b0;
    uncorrectable_error = 1'b0;
    error_position = {6{1'b0}};
    if (error_detected) begin
      found = 1'b0;
      for (b = 0; b < 32; b = b + 1) begin
        if (!found) begin
          corrected_codeword_o = x ^ ({{32{1'b0}}} | ({32{1'b0}} | (64'h1 << b)));
          found = 1'b1;
        end
      end
      uncorrectable_error = 1'b1;
    end
  end
endmodule

module polar_16b_top(
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
  input [31:0] inject_error_mask;
  input inject_syndrome_en;
  input [31:0] injected_syndrome;
  output [31:0] syndrome_out;
  output error_detected;
  output error_corrected;
  output uncorrectable_error;
  output [5:0] error_position;

  wire [31:0] enc_codeword;
  wire [31:0] mem_r;
  wire [31:0] dec_in;
  wire [31:0] corr_cw;

  polar_16b_encoder u_encoder(.data_i(data_in), .codeword_o(enc_codeword));
  polar_16b_sram #(.ADDR_W(ADDR_W), .CODE_W(32)) u_sram(
    .clk(clk), .rst(rst), .we(write_en), .re(read_en), .addr(addr), .wcode(enc_codeword), .rcode(mem_r)
  );

  assign dec_in = inject_error_en ? (mem_r ^ inject_error_mask) : mem_r;

  polar_16b_decoder u_decoder(
    .codeword_i(dec_in), .inject_syndrome_en(inject_syndrome_en), .injected_syndrome(injected_syndrome),
    .data_o(data_out), .corrected_codeword_o(corr_cw), .syndrome_out(syndrome_out),
    .error_detected(error_detected), .error_corrected(error_corrected), .uncorrectable_error(uncorrectable_error),
    .error_position(error_position)
  );
endmodule
