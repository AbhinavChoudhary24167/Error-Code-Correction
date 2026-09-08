module diagnostic(input rstb, input clk, output [7:0] dout);
wire mid, local_rstb;
sky130_fd_sc_hd__inv_16 stage1(.A(rstb), .Y(mid));
sky130_fd_sc_hd__inv_16 stage2(.A(mid), .Y(local_rstb));
sram22_256x8m8w1 memory(.rstb(local_rstb), .clk(clk), .dout(dout));
endmodule
