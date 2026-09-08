module diagnostic(input rstb, input clk, output [63:0] dout);
wire mid, local_rstb;
sky130_fd_sc_hd__buf_16 stage2(.A(rstb), .X(local_rstb));
sram22_256x64m4w8 memory(.rstb(local_rstb), .clk(clk), .dout(dout));
endmodule
