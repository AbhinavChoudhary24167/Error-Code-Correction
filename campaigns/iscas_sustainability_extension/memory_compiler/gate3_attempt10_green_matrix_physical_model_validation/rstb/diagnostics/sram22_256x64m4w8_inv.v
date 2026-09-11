module diagnostic(input rstb, input clk, output [63:0] dout);
wire mid, local_rstb;
sky130_fd_sc_hd__inv_16 stage1(.A(rstb), .Y(mid));
sky130_fd_sc_hd__inv_16 stage2(.A(mid), .Y(local_rstb));
sram22_256x64m4w8 memory(.rstb(local_rstb), .clk(clk), .dout(dout));
endmodule
