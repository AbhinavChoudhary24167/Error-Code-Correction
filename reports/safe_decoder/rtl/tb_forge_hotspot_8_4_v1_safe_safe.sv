`timescale 1ns/1ps
module tb_forge_hotspot_8_4_v1_safe_safe;
  // Campaign: all data words crossed with every modeled error.
  logic [3:0] data;
  logic [7:0] codeword, received;
  logic [3:0] data_out;
  logic correction_applied, abstain, due, fallback_selected, no_certified_mode, envelope_valid;
  logic [127:0] safety_envelope_id;
  integer d;
  forge_hotspot_8_4_v1_safe_encoder u_encoder(.data(data), .codeword(codeword));
  forge_hotspot_8_4_v1_safe_safe_decoder u_decoder(
    .word(received), .envelope_valid(envelope_valid), .fallback_select(1'b1),
    .data_out(data_out), .correction_applied(correction_applied), .abstain(abstain),
    .detected_uncorrectable(due), .fallback_selected(fallback_selected),
    .no_certified_mode(no_certified_mode), .safety_envelope_id(safety_envelope_id)
  );
  initial begin
    envelope_valid = 1'b1;
    for (d = 0; d < 16; d = d + 1) begin
      data = d[3:0]; #1;
      received = codeword ^ 8'b00000001; #1;
      if (!due) $fatal(1, "policy mismatch for sbu-0 data=%0d", d);
      received = codeword ^ 8'b00000010; #1;
      if (!due) $fatal(1, "policy mismatch for sbu-1 data=%0d", d);
      received = codeword ^ 8'b00000011; #1;
      if (due || data_out !== data) $fatal(1, "policy mismatch for adj-dbu-0-1 data=%0d", d);
      received = codeword ^ 8'b00000100; #1;
      if (!due) $fatal(1, "policy mismatch for sbu-2 data=%0d", d);
      received = codeword ^ 8'b00000110; #1;
      if (due || data_out !== data) $fatal(1, "policy mismatch for adj-dbu-1-2 data=%0d", d);
      received = codeword ^ 8'b00000111; #1;
      if (!due) $fatal(1, "policy mismatch for shift-triple-0-2 data=%0d", d);
      received = codeword ^ 8'b00001000; #1;
      if (!due) $fatal(1, "policy mismatch for sbu-3 data=%0d", d);
      received = codeword ^ 8'b00001001; #1;
      if (!due) $fatal(1, "policy mismatch for nonadj-dbu-0-3 data=%0d", d);
      received = codeword ^ 8'b00001100; #1;
      if (due || data_out !== data) $fatal(1, "policy mismatch for adj-dbu-2-3 data=%0d", d);
      received = codeword ^ 8'b00001110; #1;
      if (!due) $fatal(1, "policy mismatch for shift-triple-1-3 data=%0d", d);
      received = codeword ^ 8'b00010000; #1;
      if (due || data_out !== data) $fatal(1, "policy mismatch for sbu-4 data=%0d", d);
      received = codeword ^ 8'b00010101; #1;
      if (!due) $fatal(1, "policy mismatch for shift-mbu-0-2-4 data=%0d", d);
      received = codeword ^ 8'b00011000; #1;
      if (!due) $fatal(1, "policy mismatch for adj-dbu-3-4 data=%0d", d);
      received = codeword ^ 8'b00011100; #1;
      if (!due) $fatal(1, "policy mismatch for shift-triple-2-4 data=%0d", d);
      received = codeword ^ 8'b00100000; #1;
      if (!due) $fatal(1, "policy mismatch for sbu-5 data=%0d", d);
      received = codeword ^ 8'b00100010; #1;
      if (!due) $fatal(1, "policy mismatch for nonadj-dbu-1-5 data=%0d", d);
      received = codeword ^ 8'b00110000; #1;
      if (due || data_out !== data) $fatal(1, "policy mismatch for adj-dbu-4-5 data=%0d", d);
      received = codeword ^ 8'b00111000; #1;
      if (!due) $fatal(1, "policy mismatch for shift-triple-3-5 data=%0d", d);
      received = codeword ^ 8'b01000000; #1;
      if (!due) $fatal(1, "policy mismatch for sbu-6 data=%0d", d);
      received = codeword ^ 8'b01001010; #1;
      if (!due) $fatal(1, "policy mismatch for shift-mbu-1-3-6 data=%0d", d);
      received = codeword ^ 8'b01100000; #1;
      if (!due) $fatal(1, "policy mismatch for adj-dbu-5-6 data=%0d", d);
      received = codeword ^ 8'b01110000; #1;
      if (!due) $fatal(1, "policy mismatch for shift-triple-4-6 data=%0d", d);
      received = codeword ^ 8'b10000000; #1;
      if (due || data_out !== data) $fatal(1, "policy mismatch for sbu-7 data=%0d", d);
      received = codeword ^ 8'b10000100; #1;
      if (due || data_out !== data) $fatal(1, "policy mismatch for nonadj-dbu-2-7 data=%0d", d);
      received = codeword ^ 8'b10010001; #1;
      if (!due) $fatal(1, "policy mismatch for shift-mbu-0-4-7 data=%0d", d);
      received = codeword ^ 8'b10010010; #1;
      if (!due) $fatal(1, "policy mismatch for shift-mbu-1-4-7 data=%0d", d);
      received = codeword ^ 8'b11000000; #1;
      if (!due) $fatal(1, "policy mismatch for adj-dbu-6-7 data=%0d", d);
      received = codeword ^ 8'b11100000; #1;
      if (!due) $fatal(1, "policy mismatch for shift-triple-5-7 data=%0d", d);
    end
    received = codeword ^ 1; #1;
    envelope_valid = 1'b0; #1;
    if (!due || !fallback_selected || correction_applied) $fatal(1, "out-of-envelope fallback failed");
    $display("PASS tb_forge_hotspot_8_4_v1_safe_safe");
    $finish;
  end
endmodule
