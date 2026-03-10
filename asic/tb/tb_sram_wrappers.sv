`timescale 1ns/1ps
module tb_sram_wrappers;
  logic [7:0] d8, q8; logic [12:0] m8, r8; logic de8, co8, un8;
  logic [15:0] d16, q16; logic [31:0] m16p, r16p; logic dep, cop, unp;
  logic [31:0] d32, q32; logic [44:0] m32b, r32b; logic deb, cob, unb;

  sram_secded_8 u0(.wr_data_i(d8), .mem_word_o(m8), .rd_word_i(r8), .rd_data_o(q8), .err_detected_o(de8), .err_corrected_o(co8), .err_uncorrectable_o(un8));
  sram_polar_16 u1(.wr_data_i(d16), .mem_word_o(m16p), .rd_word_i(r16p), .rd_data_o(q16), .err_detected_o(dep), .err_corrected_o(cop), .err_uncorrectable_o(unp));
  sram_bch_32 u2(.wr_data_i(d32), .mem_word_o(m32b), .rd_word_i(r32b), .rd_data_o(q32), .err_detected_o(deb), .err_corrected_o(cob), .err_uncorrectable_o(unb));

  initial begin
    d8 = 8'hA5; #1; r8 = m8; #1; if (q8 !== d8) $fatal(1, "sram secded-8 no-error");
    r8 = m8 ^ (13'd1<<4); #1; if (q8 !== d8 || !co8) $fatal(1, "sram secded-8 single error");

    d16 = 16'hBEEF; #1; r16p = m16p; #1; if (q16 !== d16) $fatal(1, "sram polar-16 no-error");

    d32 = 32'hdeadbeef; #1; r32b = m32b ^ (45'd1<<3) ^ (45'd1<<11); #1; if (q32 !== d32 || !cob) $fatal(1, "sram bch-32 2-bit correction");

    $display("TB_SRAM_WRAPPERS_PASS");
    $finish;
  end
endmodule
