`timescale 1ns/1ps
module tb_forge_hotspot_8_4_v1;
  logic [3:0] data;
  logic [7:0] codeword, received;
  logic [3:0] data_out;
  logic correction_applied, detected_uncorrectable;
  integer d;
  forge_hotspot_8_4_v1_encoder u_encoder(.data(data), .codeword(codeword));
  forge_hotspot_8_4_v1_decoder u_decoder(
    .word(received), .data_out(data_out),
    .correction_applied(correction_applied),
    .detected_uncorrectable(detected_uncorrectable)
  );
  initial begin
    for (d = 0; d < 16; d = d + 1) begin
      data = d[3:0]; #1;
      received = codeword ^ 8'b00000001; #1;
      if (data_out !== data) $fatal(1, "pattern sbu-0 failed for data=%0d", d);
      received = codeword ^ 8'b00000010; #1;
      if (data_out !== data) $fatal(1, "pattern sbu-1 failed for data=%0d", d);
      received = codeword ^ 8'b00000100; #1;
      if (data_out !== data) $fatal(1, "pattern sbu-2 failed for data=%0d", d);
      received = codeword ^ 8'b00001000; #1;
      if (data_out !== data) $fatal(1, "pattern sbu-3 failed for data=%0d", d);
      received = codeword ^ 8'b00010000; #1;
      if (data_out !== data) $fatal(1, "pattern sbu-4 failed for data=%0d", d);
      received = codeword ^ 8'b00100000; #1;
      if (data_out !== data) $fatal(1, "pattern sbu-5 failed for data=%0d", d);
      received = codeword ^ 8'b01000000; #1;
      if (data_out !== data) $fatal(1, "pattern sbu-6 failed for data=%0d", d);
      received = codeword ^ 8'b10000000; #1;
      if (data_out !== data) $fatal(1, "pattern sbu-7 failed for data=%0d", d);
      received = codeword ^ 8'b00000011; #1;
      if (data_out !== data) $fatal(1, "pattern adj-dbu-0-1 failed for data=%0d", d);
      received = codeword ^ 8'b00000110; #1;
      if (data_out !== data) $fatal(1, "pattern adj-dbu-1-2 failed for data=%0d", d);
      received = codeword ^ 8'b00001100; #1;
      if (data_out !== data) $fatal(1, "pattern adj-dbu-2-3 failed for data=%0d", d);
      received = codeword ^ 8'b00011000; #1;
      if (!detected_uncorrectable) $fatal(1, "pattern adj-dbu-3-4 failed for data=%0d", d);
      received = codeword ^ 8'b00110000; #1;
      if (data_out !== data) $fatal(1, "pattern adj-dbu-4-5 failed for data=%0d", d);
      received = codeword ^ 8'b01100000; #1;
      if (!detected_uncorrectable) $fatal(1, "pattern adj-dbu-5-6 failed for data=%0d", d);
      received = codeword ^ 8'b11000000; #1;
      if (!detected_uncorrectable) $fatal(1, "pattern adj-dbu-6-7 failed for data=%0d", d);
      received = codeword ^ 8'b00001001; #1;
      if (!detected_uncorrectable) $fatal(1, "pattern nonadj-dbu-0-3 failed for data=%0d", d);
      received = codeword ^ 8'b00100010; #1;
      if (!detected_uncorrectable) $fatal(1, "pattern nonadj-dbu-1-5 failed for data=%0d", d);
      received = codeword ^ 8'b10000100; #1;
      if (data_out !== data) $fatal(1, "pattern nonadj-dbu-2-7 failed for data=%0d", d);
    end
    $display("PASS tb_forge_hotspot_8_4_v1");
    $finish;
  end
endmodule
