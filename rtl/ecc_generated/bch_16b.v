// Auto-generated Verilog-2001 ECC block: bch 16b
`timescale 1ns/1ps

module bch_16b_sram(
  clk, rst, we, re, addr, wcode, rcode
);
  parameter ADDR_W = 6;
  parameter CODE_W = 24;
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

module bch_16b_encoder(
  data_i, codeword_o
);
  input  [15:0] data_i;
  output reg [23:0] codeword_o;

  integer i;
  integer j;
  reg [7:0] ecc;
  always @(*) begin
    ecc = {8{1'b0}};
    for (j = 0; j < 8; j = j + 1) begin
      for (i = 0; i < 16; i = i + 1) begin
        if (((i+1) & (j+1)) != 0)
          ecc[j] = ecc[j] ^ data_i[i];
      end
      ecc[j] = ecc[j] ^ data_i[j % 16];
    end
    codeword_o = {ecc, data_i};
  end
endmodule

module bch_16b_decoder(
  codeword_i, inject_syndrome_en, injected_syndrome,
  data_o, corrected_codeword_o, syndrome_out,
  error_detected, error_corrected, uncorrectable_error, error_position
);
  input  [23:0] codeword_i;
  input  inject_syndrome_en;
  input  [7:0] injected_syndrome;
  output reg [15:0] data_o;
  output reg [23:0] corrected_codeword_o;
  output reg [7:0] syndrome_out;
  output reg error_detected;
  output reg error_corrected;
  output reg uncorrectable_error;
  output reg [4:0] error_position;

  integer i;
  integer j;
  integer b;
  reg [7:0] syndrome_raw;
  reg [7:0] bit_sig;
  reg [23:0] cw_work;
  reg found;
  always @(*) begin
    cw_work = codeword_i;
    syndrome_raw = {8{1'b0}};
    for (j = 0; j < 8; j = j + 1) begin
      for (i = 0; i < 24; i = i + 1)
        if (((i+1) & (j+1)) != 0)
          syndrome_raw[j] = syndrome_raw[j] ^ cw_work[i];
    end
    syndrome_out = inject_syndrome_en ? (syndrome_raw ^ injected_syndrome[7:0]) : syndrome_raw;
    error_detected = (syndrome_out != {8{1'b0}});
    error_corrected = 1'b0;
    uncorrectable_error = 1'b0;
    error_position = {5{1'b0}};

    if (syndrome_out != {8{1'b0}}) begin
      found = 1'b0;
      for (b = 0; b < 24; b = b + 1) begin
        bit_sig = {8{1'b0}};
        for (j = 0; j < 8; j = j + 1)
          if (((b+1) & (j+1)) != 0)
            bit_sig[j] = 1'b1;
        if (!found && (bit_sig == syndrome_out)) begin
          cw_work[b] = ~cw_work[b];
          error_corrected = 1'b1;
          found = 1'b1;
          error_position = (b+1)[4:0];
        end
      end
      if (!found)
        uncorrectable_error = 1'b1;
    end

    corrected_codeword_o = cw_work;
    data_o = cw_work[15:0];
  end
endmodule

module bch_16b_top(
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
  input [23:0] inject_error_mask;
  input inject_syndrome_en;
  input [7:0] injected_syndrome;
  output [7:0] syndrome_out;
  output error_detected;
  output error_corrected;
  output uncorrectable_error;
  output [4:0] error_position;

  wire [23:0] enc_codeword;
  wire [23:0] mem_r;
  wire [23:0] dec_in;
  wire [23:0] corr_cw;

  bch_16b_encoder u_encoder(.data_i(data_in), .codeword_o(enc_codeword));
  bch_16b_sram #(.ADDR_W(ADDR_W), .CODE_W(24)) u_sram(
    .clk(clk), .rst(rst), .we(write_en), .re(read_en), .addr(addr), .wcode(enc_codeword), .rcode(mem_r)
  );

  assign dec_in = inject_error_en ? (mem_r ^ inject_error_mask) : mem_r;

  bch_16b_decoder u_decoder(
    .codeword_i(dec_in), .inject_syndrome_en(inject_syndrome_en), .injected_syndrome(injected_syndrome),
    .data_o(data_out), .corrected_codeword_o(corr_cw), .syndrome_out(syndrome_out),
    .error_detected(error_detected), .error_corrected(error_corrected), .uncorrectable_error(uncorrectable_error),
    .error_position(error_position)
  );
endmodule
