// Generated hard-decision syndrome decoder.
module forge_hotspot_8_4_v1_decoder(
  input  logic [7:0] word,
  output logic [3:0] data_out,
  output logic correction_applied,
  output logic detected_uncorrectable
);
  logic [3:0] syndrome;
  logic [7:0] correction_mask;
  logic [7:0] corrected_word;
  logic correction_known;
  forge_hotspot_8_4_v1_syndrome u_syndrome(.word(word), .syndrome(syndrome));
  always_comb begin
    correction_known = 1'b0;
    correction_mask = '0;
    unique case (syndrome)
      4'b0001: begin correction_known = 1'b1; correction_mask = 8'b00010000; end
      4'b0010: begin correction_known = 1'b1; correction_mask = 8'b00100000; end
      4'b0011: begin correction_known = 1'b1; correction_mask = 8'b00110000; end
      4'b0100: begin correction_known = 1'b1; correction_mask = 8'b01000000; end
      4'b0101: begin correction_known = 1'b1; correction_mask = 8'b00000011; end
      4'b0111: begin correction_known = 1'b1; correction_mask = 8'b00000100; end
      4'b1000: begin correction_known = 1'b1; correction_mask = 8'b10000000; end
      4'b1001: begin correction_known = 1'b1; correction_mask = 8'b00000110; end
      4'b1010: begin correction_known = 1'b1; correction_mask = 8'b00001100; end
      4'b1011: begin correction_known = 1'b1; correction_mask = 8'b00000001; end
      4'b1101: begin correction_known = 1'b1; correction_mask = 8'b00001000; end
      4'b1110: begin correction_known = 1'b1; correction_mask = 8'b00000010; end
      4'b1111: begin correction_known = 1'b1; correction_mask = 8'b10000100; end
      default: begin end
    endcase
  end
  assign correction_applied = (syndrome != '0) && correction_known;
  assign detected_uncorrectable = (syndrome != '0) && !correction_known;
  assign corrected_word = word ^ correction_mask;
  assign data_out = corrected_word[3:0];
endmodule
