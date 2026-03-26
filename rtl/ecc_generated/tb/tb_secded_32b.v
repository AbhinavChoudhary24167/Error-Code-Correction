`timescale 1ns/1ps
module tb_secded_32b;
  reg clk;
  reg rst;
  reg write_en;
  reg read_en;
  reg [5:0] addr;
  reg [31:0] data_in;
  wire [31:0] data_out;
  reg inject_error_en;
  reg [38:0] inject_error_mask;
  reg inject_syndrome_en;
  reg [5:0] injected_syndrome;
  wire [5:0] syndrome_out;
  wire error_detected;
  wire error_corrected;
  wire uncorrectable_error;
  wire [5:0] error_position;

  secded_32b_top dut(
    .clk(clk), .rst(rst), .write_en(write_en), .read_en(read_en), .addr(addr), .data_in(data_in), .data_out(data_out),
    .inject_error_en(inject_error_en), .inject_error_mask(inject_error_mask),
    .inject_syndrome_en(inject_syndrome_en), .injected_syndrome(injected_syndrome),
    .syndrome_out(syndrome_out), .error_detected(error_detected), .error_corrected(error_corrected),
    .uncorrectable_error(uncorrectable_error), .error_position(error_position)
  );

  always #5 clk = ~clk;

  initial begin
    clk = 0; rst = 1; write_en = 0; read_en = 0; addr = 0; data_in = 0;
    inject_error_en = 0; inject_error_mask = 0; inject_syndrome_en = 0; injected_syndrome = 0;
    #20 rst = 0;

    data_in = 32'hA5A5A5A5;
    write_en = 1; #10; write_en = 0;

    read_en = 1; #10; read_en = 0;

    inject_error_en = 1; inject_error_mask = 39'h1;
    read_en = 1; #10; read_en = 0;

    inject_syndrome_en = 1; injected_syndrome = 6'h1;
    read_en = 1; #10; read_en = 0;

    inject_error_mask = 39'h3;
    read_en = 1; #10; read_en = 0;

    #20 $finish;
  end
endmodule
