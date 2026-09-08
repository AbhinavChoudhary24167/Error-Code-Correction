module diagnostic(input rstb, input clk, output [7:0] dout);
wire mid, local_rstb;
sky130_fd_sc_hd__clkbuf_16 stage2(.A(rstb), .X(local_rstb));
sram22_256x8m8w1 memory(.rstb(local_rstb), .clk(clk), .dout(dout));
endmodule
